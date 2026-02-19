#!/usr/bin/env python3
"""
Fix countries table data quality issues.

Issues fixed:
  1. '1980)' — parsing error → re-link to 'N Germany', delete bad entry
  2. 'Czech Repubic' → merge into 'Czech Republic'
  3. 'Brasil' → merge into 'Brazil'
  4. 'N. Ireland' → merge into 'N Ireland'
  5. 'NWGreenland' → merge into 'NW Greenland'
  6. 'E. Kazakhstan' → merge into 'E Kazakhstan' (no genus_locations, just delete)
  7. 'arctic Russia' → merge into 'Arctic Russia'
  8. '" Spain' → merge into 'Spain'
  9. '" SE Morocco' → merge into 'SE Morocco'
  10. 'central Afghanistan' → rename to 'Central Afghanistan'
  11. 'central Kazakhstan' → rename to 'Central Kazakhstan'
  12. 'central Morocco' → rename to 'Central Morocco'
  13. 'eastern Iran' → rename to 'Eastern Iran'
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')


def merge_country(cursor, bad_name, good_name):
    """Merge bad country into good country: re-link genus_locations, update taxa_count, delete bad."""
    cursor.execute("SELECT id, taxa_count FROM countries WHERE name = ?", (bad_name,))
    bad = cursor.fetchone()
    if not bad:
        print(f"  SKIP: '{bad_name}' not found")
        return

    cursor.execute("SELECT id, taxa_count FROM countries WHERE name = ?", (good_name,))
    good = cursor.fetchone()
    if not good:
        print(f"  ERROR: target '{good_name}' not found!")
        return

    bad_id, bad_count = bad
    good_id, good_count = good

    # Re-link genus_locations (skip duplicates)
    cursor.execute("""
        UPDATE OR IGNORE genus_locations SET country_id = ? WHERE country_id = ?
    """, (good_id, bad_id))
    moved = cursor.rowcount

    # Delete any remaining (duplicates that couldn't be moved due to UNIQUE constraint)
    cursor.execute("DELETE FROM genus_locations WHERE country_id = ?", (bad_id,))
    skipped = cursor.rowcount

    # Update taxa_count on good entry
    cursor.execute("""
        UPDATE countries SET taxa_count = (
            SELECT COUNT(*) FROM genus_locations WHERE country_id = ?
        ) WHERE id = ?
    """, (good_id, good_id))

    # Delete bad entry
    cursor.execute("DELETE FROM countries WHERE id = ?", (bad_id,))

    print(f"  MERGE: '{bad_name}' (id={bad_id}) → '{good_name}' (id={good_id}): {moved} moved, {skipped} dup-deleted")


def rename_country(cursor, old_name, new_name):
    """Rename a country entry."""
    cursor.execute("SELECT id FROM countries WHERE name = ?", (old_name,))
    row = cursor.fetchone()
    if not row:
        print(f"  SKIP: '{old_name}' not found")
        return

    cursor.execute("UPDATE countries SET name = ? WHERE name = ?", (new_name, old_name))
    print(f"  RENAME: '{old_name}' → '{new_name}' (id={row[0]})")


def fix_parsing_error(cursor):
    """Fix '1980)' parsing error: re-link Metagnostus to 'N Germany', delete bad country."""
    # Check current state
    cursor.execute("SELECT id FROM countries WHERE name = '1980)'")
    bad = cursor.fetchone()
    if not bad:
        print("  SKIP: '1980)' not found")
        return

    bad_id = bad[0]

    cursor.execute("SELECT id FROM countries WHERE name = 'N Germany'")
    good = cursor.fetchone()
    if not good:
        print("  ERROR: 'N Germany' not found!")
        return

    good_id = good[0]

    # Update genus_locations: change country_id and fix region
    cursor.execute("""
        UPDATE genus_locations
        SET country_id = ?, region = NULL
        WHERE country_id = ?
    """, (good_id, bad_id))
    moved = cursor.rowcount

    # Update taxa_count
    cursor.execute("""
        UPDATE countries SET taxa_count = (
            SELECT COUNT(*) FROM genus_locations WHERE country_id = ?
        ) WHERE id = ?
    """, (good_id, good_id))

    # Delete bad country
    cursor.execute("DELETE FROM countries WHERE id = ?", (bad_id,))

    print(f"  FIX: '1980)' (id={bad_id}) → 'N Germany' (id={good_id}): {moved} re-linked")


def main():
    db_path = os.path.abspath(DB_PATH)
    if not os.path.exists(db_path):
        print(f"Error: DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count before
    cursor.execute("SELECT COUNT(*) FROM countries")
    count_before = cursor.fetchone()[0]

    print(f"Countries before: {count_before}")
    print()

    # 1. Fix parsing error
    print("[1] Fix parsing error: '1980)'")
    fix_parsing_error(cursor)

    # 2-9. Merge duplicates
    merges = [
        ('Czech Repubic', 'Czech Republic'),
        ('Brasil', 'Brazil'),
        ('N. Ireland', 'N Ireland'),
        ('NWGreenland', 'NW Greenland'),
        ('E. Kazakhstan', 'E Kazakhstan'),
        ('arctic Russia', 'Arctic Russia'),
        ('" Spain', 'Spain'),
        ('" SE Morocco', 'SE Morocco'),
    ]

    print("\n[2-9] Merge duplicates:")
    for bad, good in merges:
        merge_country(cursor, bad, good)

    # 10-13. Rename lowercase prefixes
    renames = [
        ('central Afghanistan', 'Central Afghanistan'),
        ('central Kazakhstan', 'Central Kazakhstan'),
        ('central Morocco', 'Central Morocco'),
        ('eastern Iran', 'Eastern Iran'),
    ]

    print("\n[10-13] Rename lowercase prefixes:")
    for old, new in renames:
        rename_country(cursor, old, new)

    conn.commit()

    # Count after
    cursor.execute("SELECT COUNT(*) FROM countries")
    count_after = cursor.fetchone()[0]

    print(f"\nCountries after: {count_after} (removed {count_before - count_after})")

    # Verify no orphaned genus_locations
    cursor.execute("""
        SELECT COUNT(*) FROM genus_locations gl
        WHERE NOT EXISTS (SELECT 1 FROM countries c WHERE c.id = gl.country_id)
    """)
    orphans = cursor.fetchone()[0]
    print(f"Orphaned genus_locations: {orphans}")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
