#!/usr/bin/env python3
"""
UID Population Phase B — Quality fixes and same_as_uid linkage.

Phase A populated all UIDs but had issues:
1. countries: wrong primary selection (shortest name != actual country)
2. geographic_regions: 4 country-level UIDs inconsistent with countries table
3. No same_as_uid linkage between country-level regions and countries
4. Alborz Mtns/Mts duplicate not linked

This script fixes all of the above.

Usage:
  python scripts/populate_uids_phase_b.py              # apply
  python scripts/populate_uids_phase_b.py --dry-run    # preview
  python scripts/populate_uids_phase_b.py --report     # statistics
"""

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import unicodedata


PALEOCORE_DB = os.path.join(os.path.dirname(__file__), '..', 'paleocore.db')

# ── Countries where the "actual country" name is NOT the shortest ──────────
# Phase A used shortest-name-per-ISO as primary. These are the corrections.
# Format: ISO_code → correct primary country name

COUNTRY_PRIMARY_OVERRIDES = {
    'ID': 'Indonesia',   # was: Sumatra (sub-region)
    'KP': 'North Korea', # was: NW Korea (sub-region)
}

# ── Geographic regions country-level ISO fixes ──────────────────────────────
# Phase A's _resolve_gr_country_iso missed these because pycountry
# couldn't resolve them and they weren't in GR_MANUAL_ISO.

GR_COUNTRY_ISO_FIXES = {
    'Turkey': 'TR',      # pycountry fails (official name: Türkiye)
    'Indonesia': 'ID',
    'North Korea': 'KP',
    'South Korea': 'KR',
}


def normalize_for_fp(text):
    """Normalize text for fingerprint hashing."""
    text = unicodedata.normalize('NFKC', text)
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def fp_sha256(canonical_string):
    """Generate SHA-256 fingerprint."""
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()


def fix_countries_primary(conn, dry_run=False):
    """Fix countries table: swap primary for ISO codes with wrong primary.

    For each override, the correct country name gets iso3166-1 UID,
    and the previous primary gets fp_v1 UID.
    Uses a temp UID to avoid UNIQUE constraint violation during swap.
    """
    changes = []

    for iso_code, correct_primary_name in COUNTRY_PRIMARY_OVERRIDES.items():
        rows = conn.execute(
            "SELECT id, name, uid, uid_method FROM countries WHERE code = ? ORDER BY id",
            (iso_code,)
        ).fetchall()

        # Find current primary (iso3166-1) and correct primary
        old_primary = None
        new_primary = None
        for row_id, name, uid, method in rows:
            if method == 'iso3166-1':
                old_primary = (row_id, name, uid)
            if name == correct_primary_name and method != 'iso3166-1':
                new_primary = (row_id, name, uid)

        if not old_primary or not new_primary:
            continue

        # Build new UIDs
        iso_uid = f"scoda:geo:country:iso3166-1:{iso_code}"
        canonical = f"name={normalize_for_fp(old_primary[1])}"
        fp_uid = f"scoda:geo:country:fp_v1:sha256:{fp_sha256(canonical)}"

        changes.append((old_primary[0], old_primary[1], old_primary[2], fp_uid,
                         'fp_v1', 'medium', f"demoted from primary for {iso_code}"))
        changes.append((new_primary[0], new_primary[1], new_primary[2], iso_uid,
                         'iso3166-1', 'high', f"promoted to primary for {iso_code}"))

        if not dry_run:
            # Swap: old_primary → temp → new_primary gets iso → old_primary gets fp
            temp_uid = f"__temp_swap_{iso_code}__"
            conn.execute("UPDATE countries SET uid=? WHERE id=?",
                         (temp_uid, old_primary[0]))
            conn.execute("UPDATE countries SET uid=?, uid_method=?, uid_confidence=? WHERE id=?",
                         (iso_uid, 'iso3166-1', 'high', new_primary[0]))
            conn.execute("UPDATE countries SET uid=?, uid_method=?, uid_confidence=? WHERE id=?",
                         (fp_uid, 'fp_v1', 'medium', old_primary[0]))

    if not dry_run:
        conn.commit()

    return changes


def fix_gr_country_uids(conn, dry_run=False):
    """Fix geographic_regions country-level UIDs to match countries table.

    For country-level entries, the UID should match the countries table UID.
    """
    changes = []

    # Get all country-level geographic_regions with their countries counterpart
    rows = conn.execute("""
        SELECT gr.id, gr.name, gr.uid as gr_uid,
               c.uid as c_uid, c.uid_method as c_method, c.uid_confidence as c_conf
        FROM geographic_regions gr
        JOIN countries c ON gr.name = c.name
        WHERE gr.level = 'country'
    """).fetchall()

    for gr_id, name, gr_uid, c_uid, c_method, c_conf in rows:
        if gr_uid != c_uid:
            # Check if we have ISO fix for this name
            if name in GR_COUNTRY_ISO_FIXES:
                iso = GR_COUNTRY_ISO_FIXES[name]
                # Use the countries table UID (which may have just been fixed)
                new_c_uid = conn.execute(
                    "SELECT uid FROM countries WHERE name = ?", (name,)
                ).fetchone()[0]
                changes.append((gr_id, name, gr_uid, new_c_uid,
                                f"synced with countries table"))
                if not dry_run:
                    conn.execute(
                        "UPDATE geographic_regions SET uid=?, uid_method=?, uid_confidence=? WHERE id=?",
                        (new_c_uid, c_method, c_conf, gr_id))
            else:
                # Sync to current countries UID
                changes.append((gr_id, name, gr_uid, c_uid,
                                f"synced with countries table"))
                if not dry_run:
                    conn.execute(
                        "UPDATE geographic_regions SET uid=?, uid_method=?, uid_confidence=? WHERE id=?",
                        (c_uid, c_method, c_conf, gr_id))

    if not dry_run:
        conn.commit()

    return changes


def fix_gr_south_korea_collision(conn, dry_run=False):
    """Fix South Korea geographic_regions UID collision suffix.

    Phase A gave South Korea gr uid = scoda:geo:country:iso3166-1:KR-2
    (collision with Korea). After countries fix, South Korea should get
    fp_v1 in countries, but in geographic_regions it should match.
    """
    row = conn.execute(
        "SELECT id, uid FROM geographic_regions WHERE name = 'South Korea' AND level = 'country'"
    ).fetchone()
    if row and '-2' in row[1]:
        c_uid = conn.execute(
            "SELECT uid FROM countries WHERE name = 'South Korea'"
        ).fetchone()[0]
        if not dry_run:
            conn.execute(
                "UPDATE geographic_regions SET uid=?, uid_method=?, uid_confidence=? WHERE id=?",
                (c_uid, 'fp_v1', 'medium', row[0]))
            conn.commit()
        return [(row[0], 'South Korea', row[1], c_uid, "removed collision suffix, synced with countries")]
    return []


def set_same_as_uid_country_level(conn, dry_run=False):
    """Set same_as_uid for country-level geographic_regions → countries.uid.

    After fixing UIDs, country-level gr entries have the same UID as their
    countries counterpart. We don't set same_as_uid in that case (same entity,
    same UID). But for entries where UIDs differ (shouldn't happen after fixes),
    we link them.

    Actually, country-level regions and countries ARE the same entity.
    The UID being identical is the correct representation.
    We skip same_as_uid since it's for "less authoritative → more authoritative" links.
    """
    # No action needed — same UID in both tables means same entity.
    # same_as_uid is for synonym/duplicate relationships, not identical entities.
    return []


def link_alborz_duplicate(conn, dry_run=False):
    """Link Alborz Mts → Alborz Mtns via same_as_uid.

    Both are under Turkestan and refer to the same mountain range.
    Alborz Mtns (id=482) is primary, Alborz Mts (id=483) gets same_as_uid.
    """
    primary = conn.execute(
        "SELECT id, uid FROM geographic_regions WHERE name = 'Alborz Mtns'"
    ).fetchone()
    secondary = conn.execute(
        "SELECT id, uid, same_as_uid FROM geographic_regions WHERE name = 'Alborz Mts'"
    ).fetchone()

    if not primary or not secondary:
        return []

    if secondary[2] is not None:
        # Already linked
        return []

    changes = [(secondary[0], 'Alborz Mts', secondary[1], primary[1],
                "linked to Alborz Mtns")]

    if not dry_run:
        conn.execute(
            "UPDATE geographic_regions SET same_as_uid = ? WHERE id = ?",
            (primary[1], secondary[0]))
        conn.commit()

    return changes


def verify(conn):
    """Verify all UIDs after fixes."""
    print("\n=== Verification ===")

    # countries: all have uid, no dupes
    for table in ['countries', 'geographic_regions']:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        with_uid = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE uid IS NOT NULL").fetchone()[0]
        distinct = conn.execute(
            f"SELECT COUNT(DISTINCT uid) FROM {table} WHERE uid IS NOT NULL").fetchone()[0]
        dupes = with_uid - distinct
        print(f"  {table}: {with_uid}/{total} UIDs (dupes={dupes})")

    # country-level gr matches countries
    mismatches = conn.execute("""
        SELECT COUNT(*) FROM geographic_regions gr
        JOIN countries c ON gr.name = c.name
        WHERE gr.level = 'country' AND gr.uid != c.uid
    """).fetchone()[0]
    print(f"  country-level gr ↔ countries mismatches: {mismatches}")

    # Alborz same_as_uid
    alborz = conn.execute(
        "SELECT name, same_as_uid FROM geographic_regions WHERE name LIKE 'Alborz%'"
    ).fetchall()
    for name, same_as in alborz:
        print(f"  {name}: same_as_uid={'SET' if same_as else 'NULL'}")

    # Method distribution
    print("\n  countries methods:")
    for method, count in conn.execute(
        "SELECT uid_method, COUNT(*) FROM countries GROUP BY uid_method ORDER BY uid_method"
    ):
        print(f"    {method}: {count}")

    print("  geographic_regions methods:")
    for method, count in conn.execute(
        "SELECT uid_method, COUNT(*) FROM geographic_regions GROUP BY uid_method ORDER BY uid_method"
    ):
        print(f"    {method}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description='UID Population Phase B — Quality fixes and same_as_uid linkage')
    parser.add_argument('--db', default=PALEOCORE_DB, help='Path to paleocore.db')
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--report', action='store_true', help='Show report after fixes')
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if args.dry_run:
        print("=== DRY RUN ===\n")

    # Step 1: Fix countries primary selection
    print("Step 1: Fix countries primary selection")
    changes = fix_countries_primary(conn, args.dry_run)
    for row_id, name, old_uid, new_uid, method, conf, reason in changes:
        print(f"  [{reason}] {name}: {method} ({conf})")
        if args.dry_run:
            print(f"    old: {old_uid}")
            print(f"    new: {new_uid}")
    if not changes:
        print("  (no changes needed)")

    # Step 2: Fix geographic_regions country-level UIDs
    print("\nStep 2: Fix geographic_regions country-level UIDs")
    changes = fix_gr_country_uids(conn, args.dry_run)
    for gr_id, name, old_uid, new_uid, reason in changes:
        print(f"  [{reason}] {name}")
        if args.dry_run:
            print(f"    old: {old_uid}")
            print(f"    new: {new_uid}")
    if not changes:
        print("  (no changes needed)")

    # Step 2b: Fix South Korea collision suffix
    changes = fix_gr_south_korea_collision(conn, args.dry_run)
    for gr_id, name, old_uid, new_uid, reason in changes:
        print(f"  [{reason}] {name}")
        if args.dry_run:
            print(f"    old: {old_uid}")
            print(f"    new: {new_uid}")

    # Step 3: Link Alborz duplicate
    print("\nStep 3: Link Alborz Mts → Alborz Mtns")
    changes = link_alborz_duplicate(conn, args.dry_run)
    for sec_id, name, sec_uid, primary_uid, reason in changes:
        print(f"  [{reason}] {name}.same_as_uid = {primary_uid}")
    if not changes:
        print("  (no changes needed)")

    # Verify
    if not args.dry_run:
        verify(conn)

    if args.report:
        verify(conn)

    conn.close()


if __name__ == '__main__':
    main()
