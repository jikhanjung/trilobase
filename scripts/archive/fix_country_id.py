#!/usr/bin/env python3
"""
T-5 Phase A: Fix country_id mapping errors in genus_locations.

Root cause: normalize_database.py used `LIKE '%country_name'` to assign
country_id, but later countries (e.g. 'England' matching 'New England')
overwrote earlier correct assignments (e.g. 'China').

Fix: Re-derive the correct country from taxonomic_ranks.location text
(last comma-separated segment) and update genus_locations.country_id.

Usage:
    python scripts/fix_country_id.py --dry-run    # Report only
    python scripts/fix_country_id.py --report     # Summary stats
    python scripts/fix_country_id.py              # Apply fix
"""
import argparse
import os
import sqlite3
import sys
from collections import Counter

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
DB_PATH = os.path.join(BASE_DIR, 'db', 'trilobase.db')
PC_DB_PATH = os.path.join(BASE_DIR, 'db', 'paleocore.db')

# Country name normalization map (source text → canonical pc.countries name)
COUNTRY_NORMALIZE = {
    'Czech Repubic': 'Czech Republic',
    'N. Ireland': 'N Ireland',
    'NWGreenland': 'NW Greenland',
    'arctic Russia': 'Arctic Russia',
    'eastern Iran': 'Eastern Iran',
    'central Kazakhstan': 'Central Kazakhstan',
    'central Morocco': 'Central Morocco',
    'central Afghanistan': 'Central Afghanistan',
    'southern Kazakhstan': 'S Kazakhstan',
    '" SE Morocco': 'SE Morocco',
    '" Spain': 'Spain',
    'Brasil': 'Brazil',
    'E. Kazakhstan': 'E Kazakhstan',
}

# Special location overrides: genus_name → (correct_country_name, reason)
# For locations that can't be parsed by last-comma logic
LOCATION_OVERRIDES = {
    'Metagnostus': ('N Germany', 'location contains fide parenthetical: "1980)"'),
    'Iberocoryphe': ('Spain', 'location contains embedded quote: \'"Fuencaliente VIII," Spain\''),
}


def get_country_map(cursor):
    """Build name → id map from pc.countries."""
    cursor.execute("SELECT id, name FROM pc.countries")
    return {row[0]: row[1] for row in cursor.fetchall()}, {row[1]: row[0] for row in cursor.execute("SELECT id, name FROM pc.countries")}


def extract_country_from_location(location, genus_name=None):
    """Extract the country name from location text (last comma-separated part).

    Handles special cases via LOCATION_OVERRIDES and COUNTRY_NORMALIZE.
    """
    if not location:
        return None

    # Check genus-specific overrides first
    if genus_name and genus_name in LOCATION_OVERRIDES:
        return LOCATION_OVERRIDES[genus_name][0]

    # Strip leading/trailing quotes (ASCII and Unicode curly quotes)
    loc = location.strip().strip('""\u201c\u201d').strip()

    parts = [p.strip() for p in loc.split(',')]
    country = parts[-1].strip()
    if not country:
        return None

    # Check for parenthetical content (fide references etc.) — likely parse error
    if ')' in country and '(' not in country:
        return None

    # Apply normalization
    country = COUNTRY_NORMALIZE.get(country, country)
    return country


def run_report(cursor):
    """Print current country_id mapping statistics."""
    print("=== Current country_id Mapping Report ===\n")

    # Total genus_locations
    cursor.execute("SELECT COUNT(*) FROM genus_locations")
    total = cursor.fetchone()[0]
    print(f"Total genus_locations: {total}")

    # Check how many are correctly mapped
    cursor.execute("""
        SELECT gl.id, tr.location, c.name as current_country
        FROM genus_locations gl
        JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
        JOIN pc.countries c ON gl.country_id = c.id
        WHERE tr.location IS NOT NULL
    """)
    rows = cursor.fetchall()

    correct = 0
    wrong = 0
    mismatch_details = Counter()

    for gl_id, location, current_country in rows:
        expected = extract_country_from_location(location)
        if expected and expected == current_country:
            correct += 1
        elif expected:
            wrong += 1
            mismatch_details[(expected, current_country)] += 1

    print(f"Correct: {correct} ({correct * 100.0 / len(rows):.1f}%)")
    print(f"Wrong: {wrong} ({wrong * 100.0 / len(rows):.1f}%)")

    print(f"\nTop 20 mismatches (expected → current):")
    for (expected, current), cnt in mismatch_details.most_common(20):
        print(f"  {expected} → {current}: {cnt}")


def run_fix(cursor, dry_run=False):
    """Fix country_id by re-deriving from location text."""
    # Build country name → id map
    cursor.execute("SELECT id, name FROM pc.countries")
    name_to_id = {}
    for row in cursor.fetchall():
        name_to_id[row[1]] = row[0]

    # Get all genus_locations with location text
    cursor.execute("""
        SELECT gl.id, gl.genus_id, gl.country_id, tr.location, tr.name as genus_name
        FROM genus_locations gl
        JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
        WHERE tr.location IS NOT NULL
    """)
    rows = cursor.fetchall()

    updates = []
    errors = []
    already_correct = 0
    no_match = []

    for gl_id, genus_id, current_country_id, location, genus_name in rows:
        expected_country = extract_country_from_location(location, genus_name)

        if not expected_country:
            errors.append((gl_id, genus_name, location, "Could not parse country"))
            continue

        expected_id = name_to_id.get(expected_country)
        if not expected_id:
            no_match.append((gl_id, genus_name, location, expected_country))
            continue

        if expected_id == current_country_id:
            already_correct += 1
        else:
            updates.append((expected_id, gl_id, genus_name, location, expected_country))

    # Also handle NULL-location cases (formation=country, Phase B will address)
    cursor.execute("""
        SELECT gl.id, gl.genus_id, gl.country_id, tr.name as genus_name
        FROM genus_locations gl
        JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
        WHERE tr.location IS NULL
    """)
    null_location_rows = cursor.fetchall()

    print(f"=== Phase A: country_id Fix {'(DRY RUN)' if dry_run else ''} ===\n")
    print(f"Total genus_locations: {len(rows) + len(null_location_rows)}")
    print(f"  With location text: {len(rows)}")
    print(f"  NULL location: {len(null_location_rows)}")
    print(f"  Already correct: {already_correct}")
    print(f"  To update: {len(updates)}")
    print(f"  Parse errors: {len(errors)}")
    print(f"  Country not found in pc.countries: {len(no_match)}")

    if errors:
        print(f"\n--- Parse Errors ---")
        for gl_id, genus_name, location, reason in errors:
            print(f"  [{gl_id}] {genus_name}: location='{location}' — {reason}")

    if no_match:
        print(f"\n--- Country Not Found ---")
        for gl_id, genus_name, location, country in no_match:
            print(f"  [{gl_id}] {genus_name}: location='{location}' → '{country}'")

    if not dry_run and updates:
        print(f"\nApplying {len(updates)} updates...")
        for expected_id, gl_id, genus_name, location, expected_country in updates:
            cursor.execute(
                "UPDATE genus_locations SET country_id = ? WHERE id = ?",
                (expected_id, gl_id)
            )
        print(f"Done. {len(updates)} rows updated.")

    # Post-fix verification
    if not dry_run and updates:
        print("\n--- Post-fix Verification ---")
        cursor.execute("""
            SELECT c.name, COUNT(*) as cnt
            FROM genus_locations gl
            JOIN pc.countries c ON gl.country_id = c.id
            GROUP BY c.name
            ORDER BY cnt DESC
            LIMIT 15
        """)
        print("Top 15 countries by genus_locations count:")
        for name, cnt in cursor.fetchall():
            print(f"  {name}: {cnt}")

    return len(updates), len(errors), len(no_match)


def main():
    parser = argparse.ArgumentParser(description='Fix country_id in genus_locations')
    parser.add_argument('--dry-run', action='store_true', help='Report changes without applying')
    parser.add_argument('--report', action='store_true', help='Print mapping statistics only')
    args = parser.parse_args()

    db_path = os.path.abspath(DB_PATH)
    pc_path = os.path.abspath(PC_DB_PATH)

    if not os.path.exists(db_path):
        print(f"Error: DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(pc_path):
        print(f"Error: PaleoCore DB not found: {pc_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute(f"ATTACH DATABASE '{pc_path}' AS pc")
    cursor = conn.cursor()

    if args.report:
        run_report(cursor)
    else:
        updates, errors, no_match = run_fix(cursor, dry_run=args.dry_run)
        if not args.dry_run and updates > 0:
            conn.commit()
            print("\nChanges committed.")

    conn.close()


if __name__ == '__main__':
    main()
