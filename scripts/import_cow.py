#!/usr/bin/env python3
"""
Phase 26: Import COW (Correlates of War) State System Membership v2024.

Creates two tables:
  1. cow_states — COW sovereign state master (from statelist2024.csv)
  2. country_cow_mapping — Trilobase countries ↔ COW ccode mapping

Usage:
  python scripts/import_cow.py              # full import
  python scripts/import_cow.py --dry-run    # preview without DB changes
  python scripts/import_cow.py --report     # mapping report only (DB must exist)
"""

import csv
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..',
                        'vendor', 'cow', 'v2024', 'States2024', 'statelist2024.csv')

# ── Manual mapping: Trilobase country name → COW ccode ──
# For sub-national regions, directional prefixes, and non-obvious matches.
# Key = countries.name (exact), Value = (cow_ccode, parent_name explanation)
MANUAL_MAPPING = {
    # UK constituents
    'England':       (200, 'England → United Kingdom'),
    'Scotland':      (200, 'Scotland → United Kingdom'),
    'Wales':         (200, 'Wales → United Kingdom'),
    'N Ireland':     (200, 'N Ireland → United Kingdom'),
    'N Wales':       (200, 'N Wales → United Kingdom'),
    'S Wales':       (200, 'S Wales → United Kingdom'),
    'SW Wales':      (200, 'SW Wales → United Kingdom'),
    'NW Scotland':   (200, 'NW Scotland → United Kingdom'),
    'Devon':         (200, 'Devon → United Kingdom'),

    # USA states
    'Alaska':        (2, 'Alaska → United States of America'),
    'E Alaska':      (2, 'E Alaska → United States of America'),
    'Iowa':          (2, 'Iowa → United States of America'),
    'Massachusetts': (2, 'Massachusetts → United States of America'),
    'Missouri':      (2, 'Missouri → United States of America'),
    'Pennsylvania':  (2, 'Pennsylvania → United States of America'),
    'Tennessee':     (2, 'Tennessee → United States of America'),
    'Texas':         (2, 'Texas → United States of America'),

    # Australia states
    'South Australia':                (900, 'South Australia → Australia'),
    'Western Australia':              (900, 'Western Australia → Australia'),
    'Australian Capital Territory':   (900, 'Australian Capital Territory → Australia'),

    # Canada provinces
    'New Brunswick':  (20, 'New Brunswick → Canada'),
    'Ontario':        (20, 'Ontario → Canada'),
    'NW Canada':      (20, 'NW Canada → Canada'),

    # China provinces
    'Sichuan':   (710, 'Sichuan → China'),
    'Guangxi':   (710, 'Guangxi → China'),
    'Henan':     (710, 'Henan → China'),

    # Russia regions
    'Yakutia':              (365, 'Yakutia → Russia'),
    'E Yakutia':            (365, 'E Yakutia → Russia'),
    'NE Yakutia':           (365, 'NE Yakutia → Russia'),
    'Gorny Altay':          (365, 'Gorny Altay → Russia'),
    'Novaya Zemlya':        (365, 'Novaya Zemlya → Russia'),
    'Arctic Russia':        (365, 'Arctic Russia → Russia'),
    'NW Russian Platform':  (365, 'NW Russian Platform → Russia'),
    'N Russia':             (365, 'N Russia → Russia'),
    'NE Russia':            (365, 'NE Russia → Russia'),
    'E Urals':              (365, 'E Urals → Russia'),

    # Germany regions
    'Bavaria':       (255, 'Bavaria → Germany'),
    'Eifel Germany': (255, 'Eifel Germany → Germany'),

    # France regions
    'Montagne Noire': (220, 'Montagne Noire → France'),

    # Sweden
    'Gotland': (380, 'Gotland → Sweden'),

    # Norway
    'Spitsbergen': (385, 'Spitsbergen → Norway'),

    # Indonesia
    'Sumatra': (850, 'Sumatra → Indonesia'),
    'Timor':   (850, 'Timor → Indonesia'),

    # Malaysia
    'W Malaysia':  (820, 'W Malaysia → Malaysia'),
    'NW Malaya':   (820, 'NW Malaya → Malaysia'),

    # Name mismatches (Trilobase name ≠ COW name)
    'USA':           (2, 'USA → United States of America'),
    'Burma':         (775, 'Burma → Myanmar'),
    'North Vietnam': (816, 'North Vietnam → Vietnam (DRV)'),
    'Luxemburg':     (212, 'Luxemburg → Luxembourg'),
    'Tadzikhistan':  (702, 'Tadzikhistan → Tajikistan'),

    # Danish territory
    'Greenland':     (390, 'Greenland → Denmark'),
    'E Greenland':   (390, 'E Greenland → Denmark'),
    'N Greenland':   (390, 'N Greenland → Denmark'),
    'NW Greenland':  (390, 'NW Greenland → Denmark'),

    # Unmappable (cow_ccode = NULL)
    'Central Asia':  (None, 'Historical region, no single COW state'),
    'Turkestan':     (None, 'Historical region, no single COW state'),
    'Tien-Shan':     (None, 'Mountain range spanning multiple states'),
    'Kashmir':       (None, 'Disputed territory (India/Pakistan)'),
    'Antarctica':    (None, 'No sovereign state'),
}

# ── Directional prefixes to strip for auto-matching ──
DIRECTION_PREFIXES = [
    'NW ', 'NE ', 'SW ', 'SE ',
    'N ', 'S ', 'E ', 'W ',
    'Central ', 'Eastern ', 'Western ', 'Northern ', 'Southern ',
]


def read_cow_csv(csv_path):
    """Read statelist2024.csv and return list of dicts."""
    records = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ccode = int(row['ccode'])
            # Normalize dates: month/day 0 → 01
            st_month = max(int(row['stmonth']), 1)
            st_day = max(int(row['stday']), 1)
            end_month = max(int(row['endmonth']), 1)
            end_day = max(int(row['endday']), 1)
            start_date = f"{int(row['styear']):04d}-{st_month:02d}-{st_day:02d}"
            end_date = f"{int(row['endyear']):04d}-{end_month:02d}-{end_day:02d}"
            records.append({
                'cow_ccode': ccode,
                'abbrev': row['stateabb'],
                'name': row['statenme'],
                'start_date': start_date,
                'end_date': end_date,
                'version': int(row['version']),
            })
    return records


def create_cow_states(cursor, records):
    """Create and populate cow_states table."""
    cursor.execute("DROP TABLE IF EXISTS cow_states")
    cursor.execute("""
        CREATE TABLE cow_states (
            cow_ccode    INTEGER NOT NULL,
            abbrev       TEXT    NOT NULL,
            name         TEXT    NOT NULL,
            start_date   TEXT    NOT NULL,
            end_date     TEXT    NOT NULL,
            version      INTEGER NOT NULL DEFAULT 2024,
            PRIMARY KEY (cow_ccode, start_date)
        )
    """)
    cursor.executemany("""
        INSERT INTO cow_states (cow_ccode, abbrev, name, start_date, end_date, version)
        VALUES (:cow_ccode, :abbrev, :name, :start_date, :end_date, :version)
    """, records)
    print(f"  cow_states: {len(records)} records inserted")


def build_cow_name_index(records):
    """Build name→ccode lookup from COW records (latest tenure per ccode)."""
    # For matching, use the latest tenure's name for each ccode
    index = {}  # name_lower → ccode
    by_ccode = {}  # ccode → latest name
    for r in records:
        ccode = r['cow_ccode']
        if ccode not in by_ccode or r['end_date'] > by_ccode[ccode]['end_date']:
            by_ccode[ccode] = r
    for ccode, r in by_ccode.items():
        index[r['name'].lower()] = ccode
    return index


def strip_direction_prefix(name):
    """Strip directional prefix from country name. Returns (base_name, prefix) or (None, None)."""
    for prefix in DIRECTION_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):], prefix.strip()
    return None, None


def create_country_cow_mapping(cursor, cow_name_index):
    """Create and populate country_cow_mapping table."""
    cursor.execute("DROP TABLE IF EXISTS country_cow_mapping")
    cursor.execute("""
        CREATE TABLE country_cow_mapping (
            country_id   INTEGER NOT NULL,
            cow_ccode    INTEGER,
            parent_name  TEXT,
            notes        TEXT,
            FOREIGN KEY (country_id) REFERENCES countries(id),
            PRIMARY KEY (country_id)
        )
    """)

    cursor.execute("SELECT id, name FROM countries ORDER BY id")
    countries = cursor.fetchall()

    stats = {'exact': 0, 'prefix': 0, 'manual': 0, 'unmapped': 0}
    results = []

    for country_id, country_name in countries:
        ccode = None
        parent_name = None
        notes = None

        # 1. Check manual mapping first
        if country_name in MANUAL_MAPPING:
            ccode, parent_name = MANUAL_MAPPING[country_name]
            if ccode is not None:
                notes = 'manual'
                stats['manual'] += 1
            else:
                notes = 'unmappable'
                stats['unmapped'] += 1
        else:
            # 2. Exact match (case-insensitive)
            cow_match = cow_name_index.get(country_name.lower())
            if cow_match:
                ccode = cow_match
                notes = 'exact'
                stats['exact'] += 1
            else:
                # 3. Directional prefix extraction
                base_name, prefix = strip_direction_prefix(country_name)
                if base_name:
                    cow_match = cow_name_index.get(base_name.lower())
                    if cow_match:
                        ccode = cow_match
                        parent_name = f"{country_name} → {base_name}"
                        notes = 'prefix'
                        stats['prefix'] += 1
                    else:
                        # Base name not in COW — check manual for base
                        if base_name in MANUAL_MAPPING:
                            ccode, parent_name = MANUAL_MAPPING[base_name]
                            if parent_name:
                                parent_name = f"{country_name} → {parent_name}"
                            notes = 'prefix+manual'
                            stats['manual'] += 1
                        else:
                            notes = 'unmapped'
                            stats['unmapped'] += 1
                else:
                    notes = 'unmapped'
                    stats['unmapped'] += 1

        results.append({
            'country_id': country_id,
            'cow_ccode': ccode,
            'parent_name': parent_name,
            'notes': notes,
        })

    cursor.executemany("""
        INSERT INTO country_cow_mapping (country_id, cow_ccode, parent_name, notes)
        VALUES (:country_id, :cow_ccode, :parent_name, :notes)
    """, results)

    print(f"  country_cow_mapping: {len(results)} records inserted")
    print(f"    Exact match:  {stats['exact']}")
    print(f"    Prefix match: {stats['prefix']}")
    print(f"    Manual match: {stats['manual']}")
    print(f"    Unmapped:     {stats['unmapped']}")

    return results, stats


def add_provenance(cursor):
    """Add COW data source to provenance table."""
    cursor.execute("""
        SELECT id FROM provenance
        WHERE citation LIKE '%Correlates of War%'
    """)
    if cursor.fetchone():
        print("  provenance: COW entry already exists, skipping")
        return

    cursor.execute("""
        INSERT INTO provenance (source_type, citation, description, year, url)
        VALUES ('reference',
                'Correlates of War Project. State System Membership (v2024)',
                'Sovereign state codes for country name normalization',
                2024,
                'https://correlatesofwar.org/data-sets/state-system-membership/')
    """)
    print("  provenance: COW entry added")


def print_report(cursor):
    """Print detailed mapping report."""
    print("\n" + "=" * 70)
    print("MAPPING REPORT")
    print("=" * 70)

    # Summary
    cursor.execute("SELECT COUNT(*) FROM country_cow_mapping")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM country_cow_mapping WHERE cow_ccode IS NOT NULL")
    mapped = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM country_cow_mapping WHERE cow_ccode IS NULL")
    unmapped = cursor.fetchone()[0]

    print(f"\nTotal countries:  {total}")
    print(f"Mapped:           {mapped} ({mapped*100/total:.1f}%)")
    print(f"Unmapped:         {unmapped} ({unmapped*100/total:.1f}%)")

    # By method
    cursor.execute("""
        SELECT notes, COUNT(*) FROM country_cow_mapping
        GROUP BY notes ORDER BY COUNT(*) DESC
    """)
    print("\nBy method:")
    for method, count in cursor.fetchall():
        print(f"  {method:20s} {count:4d}")

    # Unmapped entries
    cursor.execute("""
        SELECT c.name, m.parent_name, m.notes
        FROM country_cow_mapping m
        JOIN countries c ON c.id = m.country_id
        WHERE m.cow_ccode IS NULL
        ORDER BY c.name
    """)
    rows = cursor.fetchall()
    if rows:
        print(f"\nUnmapped entries ({len(rows)}):")
        for name, parent, notes in rows:
            extra = f" — {parent}" if parent else ""
            print(f"  {name}{extra}")

    # Mapped entries with COW state names
    cursor.execute("""
        SELECT c.name, cs.name as cow_name, m.cow_ccode, m.notes, m.parent_name
        FROM country_cow_mapping m
        JOIN countries c ON c.id = m.country_id
        LEFT JOIN cow_states cs ON m.cow_ccode = cs.cow_ccode
        WHERE m.cow_ccode IS NOT NULL
        GROUP BY m.country_id
        ORDER BY m.notes, c.name
    """)
    rows = cursor.fetchall()
    print(f"\nMapped entries ({len(rows)}):")
    current_method = None
    for name, cow_name, ccode, method, parent in rows:
        if method != current_method:
            current_method = method
            print(f"\n  [{method}]")
        arrow = f" ({parent})" if parent else ""
        print(f"    {name:30s} → {cow_name} [{ccode}]{arrow}")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Import COW State System Membership v2024 into Trilobase')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without modifying DB')
    parser.add_argument('--report', action='store_true',
                        help='Print mapping report only (tables must exist)')
    args = parser.parse_args()

    db_path = os.path.abspath(DB_PATH)
    csv_path = os.path.abspath(CSV_PATH)

    if not os.path.exists(db_path):
        print(f"Error: DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if args.report:
        conn = sqlite3.connect(db_path)
        print_report(conn.cursor())
        conn.close()
        return

    if not os.path.exists(csv_path):
        print(f"Error: COW CSV not found: {csv_path}", file=sys.stderr)
        print("Download from: https://correlatesofwar.org/data-sets/state-system-membership/")
        sys.exit(1)

    # Read CSV
    print(f"Reading: {csv_path}")
    records = read_cow_csv(csv_path)
    print(f"  {len(records)} COW state records read")

    # Validate
    for r in records:
        assert r['cow_ccode'] > 0, f"Invalid ccode: {r}"
        assert r['start_date'] <= r['end_date'], f"Invalid dates: {r}"
        assert r['version'] == 2024, f"Unexpected version: {r}"

    if args.dry_run:
        print("\n=== DRY RUN (no DB changes) ===")
        print(f"\nWould create cow_states with {len(records)} records")
        # Build index for preview
        cow_name_index = build_cow_name_index(records)
        print(f"Unique COW states: {len(cow_name_index)}")

        # Preview mapping
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM countries ORDER BY name")
        countries = cursor.fetchall()
        print(f"\nTrilobase countries: {len(countries)}")

        mapped = 0
        for cid, cname in countries:
            if cname in MANUAL_MAPPING:
                if MANUAL_MAPPING[cname][0] is not None:
                    mapped += 1
            elif cow_name_index.get(cname.lower()):
                mapped += 1
            else:
                base, _ = strip_direction_prefix(cname)
                if base and (cow_name_index.get(base.lower()) or base in MANUAL_MAPPING):
                    mapped += 1

        print(f"Estimated mappable: {mapped}/{len(countries)} ({mapped*100/len(countries):.1f}%)")
        conn.close()
        return

    # Full import
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n[1] Creating cow_states table...")
    create_cow_states(cursor, records)

    print("\n[2] Creating country_cow_mapping table...")
    cow_name_index = build_cow_name_index(records)
    create_country_cow_mapping(cursor, cow_name_index)

    print("\n[3] Adding provenance record...")
    add_provenance(cursor)

    conn.commit()

    # Report
    print_report(cursor)

    conn.close()
    print("Done.")


if __name__ == '__main__':
    main()
