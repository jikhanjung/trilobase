#!/usr/bin/env python3
"""
UID Population Phase A — Deterministic UID Generation

Adds uid columns to 5 tables and generates UIDs from existing DB data only.
No external lookups required.

Tables affected:
  paleocore.db:  countries, geographic_regions, ics_chronostrat, temporal_ranges
  trilobase.db:  taxonomic_ranks

Usage:
  python scripts/populate_uids_phase_a.py                    # apply
  python scripts/populate_uids_phase_a.py --dry-run          # preview
  python scripts/populate_uids_phase_a.py --report           # statistics
  python scripts/populate_uids_phase_a.py --paleocore-only   # only paleocore.db
  python scripts/populate_uids_phase_a.py --trilobase-only   # only trilobase.db
"""

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import unicodedata


PALEOCORE_DB = os.path.join(os.path.dirname(__file__), '..', 'db', 'paleocore.db')
TRILOBASE_DB = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')

UID_COLUMNS = [
    ('uid', 'TEXT'),
    ('uid_method', 'TEXT'),
    ('uid_confidence', 'TEXT'),
    ('same_as_uid', 'TEXT'),
]


# ── Utilities ──────────────────────────────────────────────────────────────

def normalize_for_fp(text):
    """Normalize text for fingerprint hashing (NFKC, lowercase, collapse spaces)."""
    text = unicodedata.normalize('NFKC', text)
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def fp_sha256(canonical_string):
    """Generate SHA-256 fingerprint from a canonical string."""
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()


def normalize_region_name(name):
    """Normalize region name: lowercase, NFKC, replace spaces with hyphens, remove punctuation."""
    name = unicodedata.normalize('NFKC', name)
    name = name.strip().lower()
    # Remove punctuation except hyphens
    name = re.sub(r"[^\w\s-]", '', name)
    # Replace spaces with hyphens
    name = re.sub(r'\s+', '-', name)
    return name


# ── Column Management ─────────────────────────────────────────────────────

def has_uid_columns(conn, table):
    """Check if table already has uid columns."""
    cols = [row[1] for row in conn.execute(
        f"PRAGMA table_info({table})").fetchall()]
    return 'uid' in cols


def add_uid_columns(conn, table):
    """Add uid columns to a table if they don't exist."""
    if has_uid_columns(conn, table):
        return False
    for col_name, col_type in UID_COLUMNS:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
    conn.commit()
    return True


def create_uid_index(conn, table):
    """Create unique index on uid column."""
    idx_name = f"idx_{table}_uid"
    conn.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {table}(uid)")
    conn.commit()


# ── UID Generators ────────────────────────────────────────────────────────

def generate_ics_chronostrat_uids(conn, dry_run=False):
    """Generate UIDs for ics_chronostrat using ics_uri.

    Pattern: scoda:strat:ics:uri:<ics_uri>
    Coverage: 100% (178 records)
    """
    rows = conn.execute(
        "SELECT id, ics_uri FROM ics_chronostrat ORDER BY id"
    ).fetchall()

    results = []
    for row_id, ics_uri in rows:
        uid = f"scoda:strat:ics:uri:{ics_uri}"
        results.append((row_id, uid, 'ics_uri', 'high', None))

    if not dry_run:
        for row_id, uid, method, confidence, same_as in results:
            conn.execute(
                "UPDATE ics_chronostrat SET uid=?, uid_method=?, "
                "uid_confidence=?, same_as_uid=? WHERE id=?",
                (uid, method, confidence, same_as, row_id))
        conn.commit()

    return results


def generate_temporal_ranges_uids(conn, dry_run=False):
    """Generate UIDs for temporal_ranges using code.

    Pattern: scoda:strat:temporal:code:<code>
    Coverage: 100% (28 records)
    """
    rows = conn.execute(
        "SELECT id, code FROM temporal_ranges ORDER BY id"
    ).fetchall()

    results = []
    for row_id, code in rows:
        uid = f"scoda:strat:temporal:code:{code}"
        results.append((row_id, uid, 'code', 'high', None))

    if not dry_run:
        for row_id, uid, method, confidence, same_as in results:
            conn.execute(
                "UPDATE temporal_ranges SET uid=?, uid_method=?, "
                "uid_confidence=?, same_as_uid=? WHERE id=?",
                (uid, method, confidence, same_as, row_id))
        conn.commit()

    return results


def generate_countries_uids(conn, dry_run=False):
    """Generate UIDs for countries using ISO 3166-1 alpha-2 or fingerprint.

    Since the countries table has sub-national entries sharing the same ISO code,
    only ONE entry per ISO code gets the iso3166-1 UID (the "primary" country).
    Others get fingerprint UIDs. The primary is selected as the shortest name
    among entries sharing the same ISO code.

    Pattern: scoda:geo:country:iso3166-1:<code> (primary per ISO code)
             scoda:geo:country:fp_v1:sha256:<hash> (sub-national / unmappable)
    """
    rows = conn.execute(
        "SELECT id, name, code FROM countries ORDER BY id"
    ).fetchall()

    # Group by ISO code to find primary entry per code
    by_code = {}
    for row_id, name, code in rows:
        if code:
            by_code.setdefault(code, []).append((row_id, name))

    # Primary = shortest name (e.g., "Russia" beats "NE Russia")
    primary_ids = set()
    for code, entries in by_code.items():
        primary = min(entries, key=lambda e: len(e[1]))
        primary_ids.add(primary[0])

    results = []
    for row_id, name, code in rows:
        if code and row_id in primary_ids:
            uid = f"scoda:geo:country:iso3166-1:{code}"
            method = 'iso3166-1'
            confidence = 'high'
        else:
            # Sub-national region or unmappable → fingerprint
            canonical = f"name={normalize_for_fp(name)}"
            uid = f"scoda:geo:country:fp_v1:sha256:{fp_sha256(canonical)}"
            method = 'fp_v1'
            confidence = 'medium' if code else 'low'
        results.append((row_id, uid, method, confidence, None))

    if not dry_run:
        for row_id, uid, method, confidence, same_as in results:
            conn.execute(
                "UPDATE countries SET uid=?, uid_method=?, "
                "uid_confidence=?, same_as_uid=? WHERE id=?",
                (uid, method, confidence, same_as, row_id))
        conn.commit()

    return results


def _resolve_gr_country_iso(name):
    """Resolve ISO code for a geographic_regions country-level entry.

    Uses pycountry + manual overrides for names that differ from the
    countries table naming (e.g., 'United Kingdom', 'Myanmar').
    """
    import pycountry

    GR_MANUAL_ISO = {
        'Korea': 'KR',
        'North Korea': 'KP',
        'South Korea': 'KR',
        'Myanmar': 'MM',
        'Czech Republic': 'CZ',
        'United Kingdom': 'GB',
        'United States of America': 'US',
        'Tajikistan': 'TJ',
        # Non-state entities → None
        'Antarctica': None,
        'Central Asia': None,
        'Kashmir': None,
        'Tien-Shan': None,
        'Turkestan': None,
    }

    if name in GR_MANUAL_ISO:
        return GR_MANUAL_ISO[name]

    try:
        c = pycountry.countries.lookup(name)
        return c.alpha_2
    except LookupError:
        pass

    try:
        results = pycountry.countries.search_fuzzy(name)
        if len(results) == 1:
            return results[0].alpha_2
    except LookupError:
        pass

    return None


def generate_geographic_regions_uids(conn, dry_run=False):
    """Generate UIDs for geographic_regions.

    Country-level: scoda:geo:country:iso3166-1:<code>
                   or scoda:geo:country:fp_v1:sha256:<hash>
    Region-level:  scoda:geo:region:name:<iso>:<normalized_name>
                   or scoda:geo:region:fp_v1:sha256:<hash>
    Collision handling: appends -2, -3 etc. for normalized name collisions.
    """
    gr_data = conn.execute(
        "SELECT id, name, level, parent_id, cow_ccode "
        "FROM geographic_regions ORDER BY id"
    ).fetchall()

    # First pass: resolve ISO for country-level entries
    country_gr_iso = {}  # gr_id → iso_code
    results = []

    for row_id, name, level, parent_id, cow_ccode in gr_data:
        if level == 'country':
            iso = _resolve_gr_country_iso(name)

            if iso:
                uid = f"scoda:geo:country:iso3166-1:{iso}"
                method = 'iso3166-1'
                confidence = 'high'
                country_gr_iso[row_id] = iso
            else:
                canonical = f"name={normalize_for_fp(name)}"
                uid = f"scoda:geo:country:fp_v1:sha256:{fp_sha256(canonical)}"
                method = 'fp_v1'
                confidence = 'medium'
                country_gr_iso[row_id] = None

            results.append((row_id, uid, method, confidence, None))

    # Build parent name lookup for fp fallback
    parent_names = {r[0]: r[1] for r in gr_data if r[2] == 'country'}

    # Second pass: generate UIDs for region-level entries
    for row_id, name, level, parent_id, cow_ccode in gr_data:
        if level == 'region':
            parent_iso = country_gr_iso.get(parent_id)

            if parent_iso:
                normalized = normalize_region_name(name)
                uid = f"scoda:geo:region:name:{parent_iso}:{normalized}"
                method = 'name'
                confidence = 'high'
            else:
                parent_name = parent_names.get(parent_id, '')
                canonical = (
                    f"country={normalize_for_fp(parent_name)}|"
                    f"name={normalize_for_fp(name)}"
                )
                uid = f"scoda:geo:region:fp_v1:sha256:{fp_sha256(canonical)}"
                method = 'fp_v1'
                confidence = 'medium'

            results.append((row_id, uid, method, confidence, None))

    # Collision handling: if any UIDs are duplicated, append suffix
    uid_seen = {}
    final_results = []
    for row_id, uid, method, confidence, same_as in results:
        if uid in uid_seen:
            count = uid_seen[uid] + 1
            uid_seen[uid] = count
            uid = f"{uid}-{count}"
            confidence = 'medium'
        else:
            uid_seen[uid] = 1
        final_results.append((row_id, uid, method, confidence, same_as))

    if not dry_run:
        for row_id, uid, method, confidence, same_as in final_results:
            conn.execute(
                "UPDATE geographic_regions SET uid=?, uid_method=?, "
                "uid_confidence=?, same_as_uid=? WHERE id=?",
                (uid, method, confidence, same_as, row_id))
        conn.commit()

    return final_results


def generate_taxonomic_ranks_uids(conn, dry_run=False):
    """Generate UIDs for taxonomic_ranks.

    Pattern: scoda:taxon:<rank_lower>:<name>
    For homonym duplicates: second entry gets scoda:taxon:<rank_lower>:<name>:hom2
    Coverage: 100% (5,340 records)
    """
    rows = conn.execute(
        "SELECT id, name, rank, is_valid, author, year "
        "FROM taxonomic_ranks ORDER BY id"
    ).fetchall()

    # Detect duplicates: (rank, name) pairs that appear more than once
    name_count = {}
    for row_id, name, rank, is_valid, author, year in rows:
        key = (rank.lower(), name)
        name_count.setdefault(key, []).append(
            (row_id, is_valid, author, year))

    # For duplicates, decide which gets the primary UID
    # Rule: valid one (is_valid=1) gets primary; if both same, lower ID wins
    primary_ids = set()
    secondary_entries = {}  # id → suffix

    for key, entries in name_count.items():
        if len(entries) > 1:
            # Sort: valid first, then by lower id
            sorted_entries = sorted(
                entries, key=lambda e: (-e[1], e[0]))
            primary_ids.add(sorted_entries[0][0])
            for i, entry in enumerate(sorted_entries[1:], 2):
                secondary_entries[entry[0]] = i

    results = []
    for row_id, name, rank, is_valid, author, year in rows:
        rank_lower = rank.lower()

        if row_id in secondary_entries:
            # Homonym duplicate — add disambiguation suffix
            suffix_num = secondary_entries[row_id]
            uid = f"scoda:taxon:{rank_lower}:{name}:hom{suffix_num}"
            method = 'name+disambiguation'
            confidence = 'medium'
        else:
            uid = f"scoda:taxon:{rank_lower}:{name}"
            method = 'name'
            confidence = 'high'

        results.append((row_id, uid, method, confidence, None))

    if not dry_run:
        for row_id, uid, method, confidence, same_as in results:
            conn.execute(
                "UPDATE taxonomic_ranks SET uid=?, uid_method=?, "
                "uid_confidence=?, same_as_uid=? WHERE id=?",
                (uid, method, confidence, same_as, row_id))
        conn.commit()

    return results


# ── Main Logic ────────────────────────────────────────────────────────────

def process_paleocore(db_path, dry_run=False):
    """Process all PaleoCore tables."""
    conn = sqlite3.connect(db_path)
    results = {}

    tables = ['countries', 'geographic_regions',
              'ics_chronostrat', 'temporal_ranges']

    # Add uid columns
    for table in tables:
        added = add_uid_columns(conn, table)
        if added and not dry_run:
            print(f"  Added uid columns to {table}")
        elif not added:
            print(f"  {table}: uid columns already exist")

    # Generate UIDs
    print("\nGenerating UIDs...")

    r = generate_ics_chronostrat_uids(conn, dry_run)
    results['ics_chronostrat'] = r
    print(f"  ics_chronostrat: {len(r)} UIDs")

    r = generate_temporal_ranges_uids(conn, dry_run)
    results['temporal_ranges'] = r
    print(f"  temporal_ranges: {len(r)} UIDs")

    r = generate_countries_uids(conn, dry_run)
    results['countries'] = r
    iso_count = sum(1 for _, _, m, _, _ in r if m == 'iso3166-1')
    fp_count = sum(1 for _, _, m, _, _ in r if m == 'fp_v1')
    print(f"  countries: {len(r)} UIDs (ISO: {iso_count}, fp: {fp_count})")

    r = generate_geographic_regions_uids(conn, dry_run)
    results['geographic_regions'] = r
    by_method = {}
    for _, _, m, _, _ in r:
        by_method[m] = by_method.get(m, 0) + 1
    method_str = ', '.join(f"{m}: {c}" for m, c in sorted(by_method.items()))
    print(f"  geographic_regions: {len(r)} UIDs ({method_str})")

    # Create unique indexes
    if not dry_run:
        for table in tables:
            create_uid_index(conn, table)
        print("\n  Created UNIQUE indexes on uid columns")

    conn.close()
    return results


def process_trilobase(db_path, dry_run=False):
    """Process trilobase.db taxonomic_ranks table."""
    conn = sqlite3.connect(db_path)

    added = add_uid_columns(conn, 'taxonomic_ranks')
    if added and not dry_run:
        print(f"  Added uid columns to taxonomic_ranks")
    elif not added:
        print(f"  taxonomic_ranks: uid columns already exist")

    print("\nGenerating UIDs...")
    r = generate_taxonomic_ranks_uids(conn, dry_run)

    by_method = {}
    by_confidence = {}
    for _, _, m, c, _ in r:
        by_method[m] = by_method.get(m, 0) + 1
        by_confidence[c] = by_confidence.get(c, 0) + 1

    method_str = ', '.join(f"{m}: {c}" for m, c in sorted(by_method.items()))
    conf_str = ', '.join(f"{c}: {n}" for c, n in sorted(by_confidence.items()))
    print(f"  taxonomic_ranks: {len(r)} UIDs ({method_str})")
    print(f"  Confidence: {conf_str}")

    if not dry_run:
        create_uid_index(conn, 'taxonomic_ranks')
        print("\n  Created UNIQUE index on uid column")

    conn.close()
    return {'taxonomic_ranks': r}


def report_results(results):
    """Print summary report."""
    print("\n=== Phase A UID Summary ===\n")
    total = 0
    for table, entries in results.items():
        by_method = {}
        by_confidence = {}
        null_uid = 0
        for _, uid, method, confidence, _ in entries:
            by_method[method] = by_method.get(method, 0) + 1
            by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
            if uid is None:
                null_uid += 1

        print(f"{table}: {len(entries)} records")
        print(f"  Methods: {by_method}")
        print(f"  Confidence: {by_confidence}")
        if null_uid:
            print(f"  NULL UIDs: {null_uid}")
        total += len(entries)
    print(f"\nTotal: {total} UIDs generated")


def verify_db(db_path, tables):
    """Verify UIDs in database."""
    conn = sqlite3.connect(db_path)
    print(f"\n=== Verification: {os.path.basename(db_path)} ===")

    for table in tables:
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        with_uid = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE uid IS NOT NULL"
        ).fetchone()[0]
        null_uid = total - with_uid

        # Check uniqueness
        distinct = conn.execute(
            f"SELECT COUNT(DISTINCT uid) FROM {table} WHERE uid IS NOT NULL"
        ).fetchone()[0]
        dupes = with_uid - distinct

        status = "OK" if null_uid == 0 and dupes == 0 else "ISSUE"
        print(f"  {table}: {with_uid}/{total} UIDs"
              f" (null={null_uid}, dupes={dupes}) [{status}]")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='UID Population Phase A — Deterministic UID Generation')
    parser.add_argument(
        '--paleocore-db', default=PALEOCORE_DB,
        help='Path to paleocore.db')
    parser.add_argument(
        '--trilobase-db', default=TRILOBASE_DB,
        help='Path to trilobase.db')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview without applying changes')
    parser.add_argument(
        '--report', action='store_true',
        help='Print detailed report after generation')
    parser.add_argument(
        '--paleocore-only', action='store_true',
        help='Only process paleocore.db')
    parser.add_argument(
        '--trilobase-only', action='store_true',
        help='Only process trilobase.db')
    args = parser.parse_args()

    paleocore_path = os.path.abspath(args.paleocore_db)
    trilobase_path = os.path.abspath(args.trilobase_db)

    do_paleocore = not args.trilobase_only
    do_trilobase = not args.paleocore_only

    if args.dry_run:
        print("=== DRY RUN (no changes will be made) ===\n")

    all_results = {}

    if do_paleocore:
        if not os.path.exists(paleocore_path):
            print(f"Error: {paleocore_path} not found", file=sys.stderr)
            sys.exit(1)
        print(f"--- PaleoCore DB: {os.path.basename(paleocore_path)} ---")
        results = process_paleocore(paleocore_path, args.dry_run)
        all_results.update(results)

        if not args.dry_run:
            verify_db(paleocore_path,
                      ['countries', 'geographic_regions',
                       'ics_chronostrat', 'temporal_ranges'])

    if do_trilobase:
        if not os.path.exists(trilobase_path):
            print(f"Error: {trilobase_path} not found", file=sys.stderr)
            sys.exit(1)
        print(f"\n--- Trilobase DB: {os.path.basename(trilobase_path)} ---")
        results = process_trilobase(trilobase_path, args.dry_run)
        all_results.update(results)

        if not args.dry_run:
            verify_db(trilobase_path, ['taxonomic_ranks'])

    if args.report or args.dry_run:
        report_results(all_results)


if __name__ == '__main__':
    main()
