#!/usr/bin/env python3
"""
Trilobase Family Normalization Script
Phase 6: Parse and normalize family data
"""

import sqlite3
import re
from pathlib import Path
from collections import defaultdict

# Soft hyphen and related characters to remove
SOFT_HYPHEN = '\u00ad'
SPECIAL_CHARS = [
    SOFT_HYPHEN,
    '\u200b', '\u200c', '\u200d',  # Zero-width chars
    '\x02', '\x03',  # STX, ETX control chars (from PDF extraction)
    '\x00', '\x01', '\x04', '\x05', '\x06', '\x07',  # Other control chars
]


def clean_text(text):
    """Remove soft hyphens and other invisible characters."""
    for char in SPECIAL_CHARS:
        text = text.replace(char, '')
    # Fix split words with hyphen at end of "line" (from PDF extraction)
    # e.g., "Hall-andclarkeops" -> "Hallandclarkeops" (but keep real hyphens)
    return text


def split_families_in_text(text):
    """
    Split text that may contain multiple families.
    Families start with pattern: FamilyName AUTHOR, YEAR
    """
    # Pattern to find family starts
    # Family name: Capital letter followed by lowercase, ending in -idae or -inae
    # Followed by author (may include lowercase like McCOY, or "in AUTHOR") and year
    # Author pattern: starts with capital, may have mixed case, &, spaces, dots, 'in AUTHOR'
    # Year can be 3-4 digits (some have typos like "184" instead of "1847")
    pattern = r'([A-Z][a-z]+(?:idae|inae))\s+([A-Z][A-Za-z&\s\.\']+(?:\s+in\s+[A-Z]+)?),\s*(\d{3,4}[a-z]?)'

    # Find all matches with their positions
    matches = list(re.finditer(pattern, text))

    if not matches:
        return []

    results = []
    for i, match in enumerate(matches):
        family_name = match.group(1)
        author = match.group(2).strip()
        year = match.group(3)

        # Get genera text: from end of this match to start of next family (or end of text)
        start_pos = match.end()
        if i + 1 < len(matches):
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)

        genera_text = text[start_pos:end_pos].strip()
        # Remove trailing period and any trailing uppercase-only words (next family name fragment)
        genera_text = re.sub(r'\s+[A-Z]+$', '', genera_text)
        genera_text = genera_text.rstrip('. ')

        results.append((family_name, author, year, genera_text))

    return results


def parse_family_line(line):
    """
    Parse a complete family line.
    Format: FamilyName AUTHOR, YEAR genera_list.
    Returns: list of (family_name, author, year, genera_list) or empty list
    """
    line = clean_text(line.strip())

    # Skip empty lines or lines that are just family names (all caps, no space)
    if not line or re.match(r'^[A-Z]+$', line):
        return []

    # Use the new split function to handle multiple families per line
    results = split_families_in_text(line)

    if results:
        return results

    # Fallback: Try alternate pattern with parenthetical author
    match = re.match(
        r'^([A-Z][a-z]+(?:idae|inae))\s+\(([^)]+)\)\s*(.*)',
        line
    )
    if match:
        family_name = match.group(1)
        author_info = match.group(2)
        genera_text = match.group(3)
        # Try to extract year from author_info
        year_match = re.search(r'(\d{4}[a-z]?)', author_info)
        year = year_match.group(1) if year_match else None
        author = re.sub(r',?\s*\d{4}[a-z]?', '', author_info).strip()
        return [(family_name, author, year, genera_text)]

    return []


def parse_genera(genera_text):
    """
    Parse genera list from text.
    Handles synonyms in parentheses: Genus (=Synonym1; =Synonym2)
    Returns: list of (genus_name, [synonyms])
    """
    genera = []
    if not genera_text:
        return genera

    # Clean up text
    genera_text = clean_text(genera_text)

    # Remove trailing period
    genera_text = genera_text.rstrip('.')

    # Split by comma, but be careful with parentheses
    parts = []
    current = ''
    paren_depth = 0

    for char in genera_text:
        if char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            if current.strip():
                parts.append(current.strip())
            current = ''
        else:
            current += char

    if current.strip():
        parts.append(current.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check for synonyms in parentheses
        syn_match = re.match(r'^([^(]+)\s*\(([^)]+)\)$', part)
        if syn_match:
            genus = syn_match.group(1).strip()
            syn_text = syn_match.group(2)
            # Parse synonyms: =Syn1; =Syn2 or /Syn1; /Syn2
            synonyms = re.findall(r'[=/]([A-Z][a-z]+)', syn_text)
            genera.append((genus, synonyms))
        else:
            # Handle hyphenated names (PDF line breaks)
            # e.g., "Hall-andclarkeops" should be checked
            genus = part.strip()
            # Remove leading ? or other markers
            genus = re.sub(r'^[?\s]+', '', genus)
            if genus and re.match(r'^[A-Z][a-z]+', genus):
                genera.append((genus, []))

    return genera


def normalize_families(db_path, family_file_path):
    """Main function to normalize family data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=== Phase 6: Family Normalization ===\n")

    # Read and parse family file
    print("1. Reading and parsing family file...")
    families = []
    genera_to_family = {}

    with open(family_file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            results = parse_family_line(line)
            for family_name, author, year, genera_text in results:
                genera_list = parse_genera(genera_text)

                families.append({
                    'name': family_name,
                    'author': author,
                    'year': year,
                    'genera_count': len(genera_list),
                    'genera': genera_list
                })

                # Map genera to family
                for genus, synonyms in genera_list:
                    genera_to_family[genus.upper()] = family_name.upper()
                    for syn in synonyms:
                        genera_to_family[syn.upper()] = family_name.upper()

    print(f"   - Parsed {len(families)} families")
    print(f"   - Found {len(genera_to_family)} genus-to-family mappings")

    # Add missing families that couldn't be parsed
    missing_families = [
        # These are families that exist in taxa but weren't parsed from the file
        {'name': 'Linguaproetidae', 'author': None, 'year': None, 'genera_count': 0, 'genera': []},
        {'name': 'Scutelluidae', 'author': None, 'year': None, 'genera_count': 0, 'genera': []},
    ]

    existing_names = {f['name'].upper() for f in families}
    for mf in missing_families:
        if mf['name'].upper() not in existing_names:
            families.append(mf)
            print(f"   - Added missing family: {mf['name']}")

    # Create families table
    print("\n2. Creating families table...")
    cursor.executescript("""
        DROP TABLE IF EXISTS families;
        CREATE TABLE families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            name_normalized TEXT,
            author TEXT,
            year TEXT,
            genera_count INTEGER DEFAULT 0,
            taxa_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_families_name ON families(name);
        CREATE INDEX idx_families_normalized ON families(name_normalized);
    """)
    conn.commit()

    # Insert families
    print("\n3. Inserting family data...")
    for fam in families:
        cursor.execute("""
            INSERT OR IGNORE INTO families (name, name_normalized, author, year, genera_count)
            VALUES (?, ?, ?, ?, ?)
        """, (
            fam['name'],
            fam['name'].upper(),
            fam['author'],
            fam['year'],
            fam['genera_count']
        ))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM families")
    inserted = cursor.fetchone()[0]
    print(f"   - Inserted {inserted} families")

    # Add family_id column to taxa if not exists
    print("\n4. Adding family_id to taxa table...")
    try:
        cursor.execute("ALTER TABLE taxa ADD COLUMN family_id INTEGER")
        conn.commit()
        print("   - Column added")
    except sqlite3.OperationalError:
        print("   - Column already exists")

    # Fix typos in taxa.family before linking
    print("\n5. Fixing typos in taxa.family...")
    family_typos = {
        'DORYPGIDAE': 'DORYPYGIDAE',
        'CHENGKOUASPIDIDAE': 'CHENGKOUASPIDAE',
    }
    for wrong, correct in family_typos.items():
        cursor.execute("UPDATE taxa SET family = ? WHERE UPPER(family) = ?", (correct, wrong))
        if cursor.rowcount > 0:
            print(f"   - Fixed {cursor.rowcount} records: {wrong} -> {correct}")
    conn.commit()

    # Link taxa to families
    print("\n6. Linking taxa to families...")
    cursor.execute("""
        UPDATE taxa
        SET family_id = (
            SELECT f.id FROM families f
            WHERE UPPER(f.name) = UPPER(taxa.family)
            LIMIT 1
        )
        WHERE family IS NOT NULL AND family != ''
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM taxa WHERE family_id IS NOT NULL")
    linked = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM taxa WHERE family IS NOT NULL AND family != ''")
    total_with_family = cursor.fetchone()[0]
    print(f"   - Linked: {linked}/{total_with_family}")

    # Find unlinked families
    cursor.execute("""
        SELECT DISTINCT family FROM taxa
        WHERE family IS NOT NULL AND family != '' AND family_id IS NULL
        ORDER BY family
    """)
    unlinked = cursor.fetchall()
    if unlinked:
        print(f"\n   Unlinked families in taxa ({len(unlinked)}):")
        for row in unlinked[:20]:
            print(f"      - {row[0]}")
        if len(unlinked) > 20:
            print(f"      ... and {len(unlinked) - 20} more")

    # Update taxa_count in families
    print("\n7. Updating taxa counts...")
    cursor.execute("""
        UPDATE families
        SET taxa_count = (
            SELECT COUNT(*) FROM taxa t WHERE t.family_id = families.id
        )
    """)
    conn.commit()

    # Summary
    print("\n=== Summary ===")
    cursor.execute("SELECT COUNT(*) FROM families")
    print(f"Total families: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM taxa WHERE family_id IS NOT NULL")
    print(f"Taxa linked to families: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(DISTINCT family) FROM taxa WHERE family_id IS NULL AND family IS NOT NULL AND family != ''")
    print(f"Unlinked family names: {cursor.fetchone()[0]}")

    conn.close()
    return families, genera_to_family


if __name__ == '__main__':
    import sys

    base_path = Path(__file__).parent.parent
    db_path = base_path / 'trilobase.db'
    family_file = base_path / 'trilobite_family_list.txt'

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    if not family_file.exists():
        print(f"Error: Family file not found at {family_file}")
        sys.exit(1)

    normalize_families(db_path, family_file)
