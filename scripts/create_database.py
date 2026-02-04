#!/usr/bin/env python3
"""
Trilobase Database Creation Script
Phase 4: Parse genus list and import into SQLite database
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime

# Database schema
SCHEMA = """
-- Temporal ranges lookup table
CREATE TABLE IF NOT EXISTS temporal_ranges (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT,
    period TEXT,
    epoch TEXT,
    start_mya REAL,
    end_mya REAL
);

-- Taxa table (genera)
CREATE TABLE IF NOT EXISTS taxa (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    rank TEXT DEFAULT 'genus',
    author TEXT,
    year INTEGER,
    year_suffix TEXT,
    type_species TEXT,
    type_species_author TEXT,
    formation TEXT,
    location TEXT,
    family TEXT,
    temporal_code TEXT,
    is_valid INTEGER DEFAULT 1,
    notes TEXT,
    raw_entry TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (temporal_code) REFERENCES temporal_ranges(code)
);

-- Synonyms table
CREATE TABLE IF NOT EXISTS synonyms (
    id INTEGER PRIMARY KEY,
    junior_taxon_id INTEGER,
    senior_taxon_name TEXT,
    synonym_type TEXT,  -- j.s.s., j.o.s., preocc., replacement, suppressed
    fide_author TEXT,
    fide_year TEXT,
    notes TEXT,
    FOREIGN KEY (junior_taxon_id) REFERENCES taxa(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_taxa_name ON taxa(name);
CREATE INDEX IF NOT EXISTS idx_taxa_family ON taxa(family);
CREATE INDEX IF NOT EXISTS idx_taxa_temporal ON taxa(temporal_code);
CREATE INDEX IF NOT EXISTS idx_synonyms_junior ON synonyms(junior_taxon_id);
"""

# Temporal range data
TEMPORAL_RANGES = [
    ('LCAM', 'Lower Cambrian', 'Cambrian', 'Lower', 538.8, 509.0),
    ('MCAM', 'Middle Cambrian', 'Cambrian', 'Middle', 509.0, 497.0),
    ('UCAM', 'Upper Cambrian', 'Cambrian', 'Upper', 497.0, 485.4),
    ('MUCAM', 'Middle-Upper Cambrian', 'Cambrian', 'Middle-Upper', 509.0, 485.4),
    ('LMCAM', 'Lower-Middle Cambrian', 'Cambrian', 'Lower-Middle', 538.8, 497.0),
    ('CAM', 'Cambrian', 'Cambrian', None, 538.8, 485.4),
    ('LORD', 'Lower Ordovician', 'Ordovician', 'Lower', 485.4, 470.0),
    ('MORD', 'Middle Ordovician', 'Ordovician', 'Middle', 470.0, 458.4),
    ('UORD', 'Upper Ordovician', 'Ordovician', 'Upper', 458.4, 443.8),
    ('LMORD', 'Lower-Middle Ordovician', 'Ordovician', 'Lower-Middle', 485.4, 458.4),
    ('MUORD', 'Middle-Upper Ordovician', 'Ordovician', 'Middle-Upper', 470.0, 443.8),
    ('ORD', 'Ordovician', 'Ordovician', None, 485.4, 443.8),
    ('LSIL', 'Lower Silurian', 'Silurian', 'Lower', 443.8, 433.4),
    ('USIL', 'Upper Silurian', 'Silurian', 'Upper', 433.4, 419.2),
    ('LUSIL', 'Lower-Upper Silurian', 'Silurian', 'Lower-Upper', 443.8, 419.2),
    ('SIL', 'Silurian', 'Silurian', None, 443.8, 419.2),
    ('LDEV', 'Lower Devonian', 'Devonian', 'Lower', 419.2, 393.3),
    ('MDEV', 'Middle Devonian', 'Devonian', 'Middle', 393.3, 382.7),
    ('UDEV', 'Upper Devonian', 'Devonian', 'Upper', 382.7, 358.9),
    ('LMDEV', 'Lower-Middle Devonian', 'Devonian', 'Lower-Middle', 419.2, 382.7),
    ('MUDEV', 'Middle-Upper Devonian', 'Devonian', 'Middle-Upper', 393.3, 358.9),
    ('EDEV', 'Early Devonian', 'Devonian', 'Early', 419.2, 393.3),
    ('MISS', 'Mississippian', 'Carboniferous', 'Mississippian', 358.9, 323.2),
    ('PENN', 'Pennsylvanian', 'Carboniferous', 'Pennsylvanian', 323.2, 298.9),
    ('LPERM', 'Lower Permian', 'Permian', 'Lower', 298.9, 272.95),
    ('PERM', 'Permian', 'Permian', None, 298.9, 251.9),
    ('UPERM', 'Upper Permian', 'Permian', 'Upper', 259.51, 251.9),
    ('INDET', 'Indeterminate', None, None, None, None),
]


def parse_entry(line):
    """Parse a single genus entry line."""
    result = {
        'name': None,
        'author': None,
        'year': None,
        'year_suffix': None,
        'type_species': None,
        'type_species_author': None,
        'formation': None,
        'location': None,
        'family': None,
        'temporal_code': None,
        'is_valid': 1,
        'notes': None,
        'synonym_info': [],
        'raw_entry': line.strip()
    }

    line = line.strip()
    if not line:
        return None

    # Extract genus name (first word)
    match = re.match(r'^([A-ZÀ-Ža-zà-ž]+)', line)
    if match:
        result['name'] = match.group(1)
    else:
        return None

    # Extract author and year
    # Patterns: "AUTHOR, YEAR", "AUTHOR & AUTHOR, YEAR", "AUTHOR in AUTHOR et al., YEAR"
    author_pattern = r'^[A-ZÀ-Ža-zà-ž]+\s+(.+?),\s*(\d{4})([a-z])?'
    match = re.match(author_pattern, line)
    if match:
        result['author'] = match.group(1).strip()
        result['year'] = int(match.group(2))
        result['year_suffix'] = match.group(3)

    # Extract type species (first [...])
    type_match = re.search(r'\[([^\]]+)\]', line)
    if type_match:
        type_content = type_match.group(1)
        # Check if it's a suppression note or actual type species
        if not type_content.startswith(('j.s.s.', 'j.o.s.', 'preocc.', 'replacement', 'suppressed')):
            # Try to separate species name from author
            sp_match = re.match(r'^([A-Z][a-z]+ [a-z]+)\s+([A-Z].+)$', type_content)
            if sp_match:
                result['type_species'] = sp_match.group(1)
                result['type_species_author'] = sp_match.group(2)
            else:
                result['type_species'] = type_content

    # Extract family and temporal code (last two semicolon-separated fields before final period or bracket)
    # Pattern: ; FAMILY; TEMPORAL.
    family_temporal = re.search(r';\s*([A-Z]+(?:IDAE|INAE)?)\s*;\s*([A-Z]+)\.?(?:\s*\[|$)', line)
    if family_temporal:
        result['family'] = family_temporal.group(1)
        result['temporal_code'] = family_temporal.group(2)

    # Extract formation and location (between ] and ; FAMILY)
    loc_match = re.search(r'\]\s*([^;]+?);\s*[A-Z]+(?:IDAE|INAE)?;', line)
    if loc_match:
        loc_str = loc_match.group(1).strip()
        # Try to split into formation and location
        # Common pattern: "Formation Fm, Location, Country"
        if ',' in loc_str:
            parts = loc_str.split(',', 1)
            result['formation'] = parts[0].strip()
            result['location'] = parts[1].strip() if len(parts) > 1 else None
        else:
            result['formation'] = loc_str

    # Extract synonym information
    # Patterns: [j.s.s. of X, fide AUTHOR, YEAR], [j.o.s. of X], [preocc., replaced by X]
    synonym_patterns = [
        (r'\[j\.s\.s\.?\s*of\s+([^,\]]+)(?:,\s*fide\s+([^,\]]+))?(?:,\s*(\d{4}))?\]', 'j.s.s.'),
        (r'\[j\.o\.s\.?\s*of\s+([^\]]+)\]', 'j.o.s.'),
        (r'\[preocc\.,\s*replaced\s+by\s+([^\]]+)\]', 'preocc.'),
        (r'\[replacement\s+name\s+for\s+([^\]]+)\]', 'replacement'),
        (r'\[suppressed[^\]]*\]', 'suppressed'),
    ]

    for pattern, syn_type in synonym_patterns:
        matches = re.finditer(pattern, line, re.IGNORECASE)
        for m in matches:
            syn_info = {
                'type': syn_type,
                'senior_name': m.group(1) if m.lastindex and m.lastindex >= 1 else None,
                'fide_author': None,
                'fide_year': None,
            }
            if syn_type == 'j.s.s.' and m.lastindex and m.lastindex >= 2:
                syn_info['fide_author'] = m.group(2)
                if m.lastindex >= 3:
                    syn_info['fide_year'] = m.group(3)
            result['synonym_info'].append(syn_info)

    # Check validity
    if any(s['type'] in ['j.s.s.', 'j.o.s.', 'suppressed'] for s in result['synonym_info']):
        result['is_valid'] = 0

    return result


def create_database(db_path, genus_file):
    """Create and populate the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create schema
    cursor.executescript(SCHEMA)

    # Insert temporal ranges
    cursor.executemany(
        "INSERT OR IGNORE INTO temporal_ranges (code, name, period, epoch, start_mya, end_mya) VALUES (?, ?, ?, ?, ?, ?)",
        TEMPORAL_RANGES
    )

    # Parse and insert genus data
    with open(genus_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    success_count = 0
    error_count = 0

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        try:
            entry = parse_entry(line)
            if entry and entry['name']:
                cursor.execute("""
                    INSERT INTO taxa (name, author, year, year_suffix, type_species,
                                     type_species_author, formation, location, family,
                                     temporal_code, is_valid, notes, raw_entry)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry['name'],
                    entry['author'],
                    entry['year'],
                    entry['year_suffix'],
                    entry['type_species'],
                    entry['type_species_author'],
                    entry['formation'],
                    entry['location'],
                    entry['family'],
                    entry['temporal_code'],
                    entry['is_valid'],
                    entry['notes'],
                    entry['raw_entry']
                ))

                taxon_id = cursor.lastrowid

                # Insert synonyms
                for syn in entry['synonym_info']:
                    cursor.execute("""
                        INSERT INTO synonyms (junior_taxon_id, senior_taxon_name,
                                            synonym_type, fide_author, fide_year)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        taxon_id,
                        syn['senior_name'],
                        syn['type'],
                        syn['fide_author'],
                        syn['fide_year']
                    ))

                success_count += 1
            else:
                error_count += 1
                print(f"Line {i}: Could not parse - {line[:50]}...")
        except Exception as e:
            error_count += 1
            print(f"Line {i}: Error - {e} - {line[:50]}...")

    conn.commit()

    # Print statistics
    print(f"\n=== Database Creation Complete ===")
    print(f"Successfully imported: {success_count}")
    print(f"Errors: {error_count}")

    # Get counts
    cursor.execute("SELECT COUNT(*) FROM taxa")
    print(f"Total taxa: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM taxa WHERE is_valid = 1")
    print(f"Valid taxa: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM synonyms")
    print(f"Synonym records: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(DISTINCT family) FROM taxa WHERE family IS NOT NULL")
    print(f"Unique families: {cursor.fetchone()[0]}")

    conn.close()
    return success_count, error_count


if __name__ == '__main__':
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / 'trilobase.db'
    genus_file = base_dir / 'trilobite_genus_list.txt'

    print(f"Creating database: {db_path}")
    print(f"Source file: {genus_file}")

    create_database(db_path, genus_file)
