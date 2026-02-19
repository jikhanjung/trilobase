#!/usr/bin/env python3
"""
Fix synonym parsing - handle complex cases with semicolons and hyphens
"""

import sqlite3
import re
from pathlib import Path


def clean_senior_name(name):
    """Clean up senior taxon name."""
    if not name:
        return name

    # Remove hyphens
    name = name.replace('-', '')

    # Handle (=X) pattern - extract X
    match = re.search(r'\(=([^)]+)\)', name)
    if match:
        name = match.group(1).strip()

    # Handle "X (=Y)" pattern - take X
    name = re.sub(r'\s*\(=[^)]+\)', '', name)

    # Remove "either " prefix
    name = re.sub(r'^either\s+', '', name, flags=re.IGNORECASE)

    # Remove author info (all caps after name, or initials like "Q.Z.")
    name = re.sub(r'\s+[A-Z][A-Z]+.*$', '', name)
    name = re.sub(r',?\s+[A-Z]\.[A-Z]\..*$', '', name)
    name = re.sub(r',\s+[A-ZŠ][A-ZŠŇÁ]+$', '', name)  # ", ŠNAJDR" pattern

    # Remove "and by X", "then X" patterns
    name = re.sub(r'\s+and\s+by\s+.*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r',?\s+then\s+.*$', '', name, flags=re.IGNORECASE)

    # Remove "or X" pattern
    name = re.sub(r'\s+or\s+.*$', '', name, flags=re.IGNORECASE)

    # Capitalize first letter (for proper genus format)
    if name and name[0].isupper() == False:
        name = name[0].upper() + name[1:] if len(name) > 1 else name.upper()

    # Fix all-caps names
    if name.isupper():
        name = name.capitalize()

    # Clean up whitespace
    name = name.strip()

    return name


def parse_synonym_bracket(bracket_content):
    """Parse a single bracket content for synonym information."""
    synonyms = []

    # Split by semicolon to handle multiple synonym info in one bracket
    parts = [p.strip() for p in bracket_content.split(';')]

    for part in parts:
        part = part.strip()
        if not part:
            continue

        syn_info = None

        # Pattern 1: j.s.s. of X, fide AUTHOR, YEAR
        match = re.match(r'j\.s\.s\.?\s*of\s+([^,]+?)(?:,\s*fide\s+(.+?)(?:,\s*(\d{4}))?)?$', part, re.IGNORECASE)
        if match:
            senior_name = clean_senior_name(match.group(1))
            syn_info = {
                'type': 'j.s.s.',
                'senior_name': senior_name,
                'fide_author': match.group(2).strip() if match.group(2) else None,
                'fide_year': match.group(3) if match.lastindex >= 3 and match.group(3) else None
            }

        # Pattern 2: j.o.s. of X
        if not syn_info:
            match = re.match(r'j\.o\.s\.?\s*of\s+(.+?)$', part, re.IGNORECASE)
            if match:
                senior_name = clean_senior_name(match.group(1))
                syn_info = {
                    'type': 'j.o.s.',
                    'senior_name': senior_name,
                    'fide_author': None,
                    'fide_year': None
                }

        # Pattern 3: replacement name for X
        if not syn_info:
            match = re.match(r'replacement\s+name\s+for\s+(.+?)$', part, re.IGNORECASE)
            if match:
                senior_name = clean_senior_name(match.group(1))
                syn_info = {
                    'type': 'replacement',
                    'senior_name': senior_name,
                    'fide_author': None,
                    'fide_year': None
                }

        # Pattern 4: preocc., replaced by X
        if not syn_info:
            match = re.match(r'preocc\.?,?\s*replaced\s+by\s+(.+?)$', part, re.IGNORECASE)
            if match:
                senior_name = clean_senior_name(match.group(1))
                syn_info = {
                    'type': 'preocc.',
                    'senior_name': senior_name,
                    'fide_author': None,
                    'fide_year': None
                }

        # Pattern 5: preocc., not replaced
        if not syn_info:
            match = re.match(r'preocc\.?,?\s*not\s+replaced', part, re.IGNORECASE)
            if match:
                syn_info = {
                    'type': 'preocc.',
                    'senior_name': None,
                    'fide_author': None,
                    'fide_year': None
                }

        # Pattern 6: suppressed
        if not syn_info:
            match = re.match(r'suppressed', part, re.IGNORECASE)
            if match:
                syn_info = {
                    'type': 'suppressed',
                    'senior_name': None,
                    'fide_author': None,
                    'fide_year': None
                }

        # Pattern 7: possibly j.s.s. of X (treat as j.s.s.)
        if not syn_info:
            match = re.match(r'possibly\s+j\.s\.s\.?\s*of\s+([^,]+?)(?:,\s*fide\s+(.+?))?$', part, re.IGNORECASE)
            if match:
                senior_name = clean_senior_name(match.group(1))
                syn_info = {
                    'type': 'j.s.s.',
                    'senior_name': senior_name,
                    'fide_author': match.group(2).strip() if match.group(2) else None,
                    'fide_year': None
                }

        # Pattern 8: "and thus j.s.s. of X" (complex pattern)
        if not syn_info:
            match = re.search(r'and\s+thus\s+j\.s\.s\.?\s*of\s+([^,]+?)(?:,\s*fide\s+(.+?))?$', part, re.IGNORECASE)
            if match:
                senior_name = clean_senior_name(match.group(1))
                syn_info = {
                    'type': 'j.s.s.',
                    'senior_name': senior_name,
                    'fide_author': match.group(2).strip() if match.group(2) else None,
                    'fide_year': None
                }

        if syn_info:
            synonyms.append(syn_info)

    return synonyms


def extract_all_synonyms(raw_entry):
    """Extract all synonym information from a raw entry."""
    all_synonyms = []

    # Find all bracket contents after the type species bracket
    # Skip the first bracket (type species)
    brackets = re.findall(r'\[([^\]]+)\]', raw_entry)

    for i, bracket in enumerate(brackets):
        # Skip if it looks like type species (first bracket usually)
        if i == 0 and not any(kw in bracket.lower() for kw in ['j.s.s.', 'j.o.s.', 'preocc.', 'replacement', 'suppressed']):
            continue

        # Parse this bracket for synonym info
        synonyms = parse_synonym_bracket(bracket)
        all_synonyms.extend(synonyms)

    return all_synonyms


def fix_synonyms(db_path):
    """Re-parse and fix all synonyms."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=== Fixing Synonym Parsing ===\n")

    # Clear existing synonyms
    cursor.execute("DELETE FROM synonyms")
    conn.commit()
    print("1. Cleared existing synonyms")

    # Get all taxa with raw entries
    cursor.execute("SELECT id, name, raw_entry FROM taxa")
    taxa = cursor.fetchall()

    total_synonyms = 0
    taxa_with_synonyms = 0

    for taxon_id, taxon_name, raw_entry in taxa:
        if not raw_entry:
            continue

        synonyms = extract_all_synonyms(raw_entry)

        if synonyms:
            taxa_with_synonyms += 1

        for syn in synonyms:
            cursor.execute("""
                INSERT INTO synonyms (junior_taxon_id, senior_taxon_name, synonym_type, fide_author, fide_year)
                VALUES (?, ?, ?, ?, ?)
            """, (taxon_id, syn['senior_name'], syn['type'], syn['fide_author'], syn['fide_year']))
            total_synonyms += 1

    conn.commit()
    print(f"2. Inserted {total_synonyms} synonyms from {taxa_with_synonyms} taxa")

    # Link to senior taxa (case-insensitive)
    print("\n3. Linking to senior taxa...")
    cursor.execute("""
        UPDATE synonyms
        SET senior_taxon_id = (
            SELECT t.id FROM taxa t
            WHERE LOWER(t.name) = LOWER(synonyms.senior_taxon_name)
            LIMIT 1
        )
        WHERE senior_taxon_name IS NOT NULL AND senior_taxon_name != ''
    """)
    conn.commit()

    # Statistics
    cursor.execute("SELECT COUNT(*) FROM synonyms")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM synonyms WHERE senior_taxon_id IS NOT NULL")
    linked = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM synonyms WHERE senior_taxon_name IS NOT NULL AND senior_taxon_name != '' AND senior_taxon_id IS NULL")
    unlinked = cursor.fetchone()[0]

    print(f"\n=== Results ===")
    print(f"Total synonyms: {total}")
    print(f"Linked to senior taxa: {linked} ({100*linked/total:.1f}%)")
    print(f"Unlinked (with name): {unlinked}")

    # Show synonym type distribution
    print(f"\nSynonym types:")
    cursor.execute("SELECT synonym_type, COUNT(*) as cnt FROM synonyms GROUP BY synonym_type ORDER BY cnt DESC")
    for syn_type, cnt in cursor.fetchall():
        print(f"  - {syn_type}: {cnt}")

    # Show unlinked cases
    print(f"\nUnlinked cases (first 10):")
    cursor.execute("""
        SELECT t.name, s.senior_taxon_name, s.synonym_type
        FROM synonyms s
        JOIN taxa t ON s.junior_taxon_id = t.id
        WHERE s.senior_taxon_id IS NULL AND s.senior_taxon_name IS NOT NULL AND s.senior_taxon_name != ''
        LIMIT 10
    """)
    for junior, senior, syn_type in cursor.fetchall():
        print(f"  {junior} -> {senior} ({syn_type})")

    conn.close()


if __name__ == '__main__':
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / 'db' / 'trilobase.db'

    fix_synonyms(db_path)
