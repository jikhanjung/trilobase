#!/usr/bin/env python3
"""
Populate formations.country and formations.period in paleocore.db.

Uses reverse-lookup through genus_formations/genus_locations/taxonomic_ranks
to derive the most likely country and period for each formation.

Logic:
  Country: genus_formations → genus_locations.region_id → geographic_regions
           (resolve region→parent country). Majority vote per formation.
  Period:  genus_formations → taxonomic_ranks.temporal_code → temporal_ranges.name
           Majority vote per formation.

Usage:
  python scripts/populate_formation_metadata.py               # apply
  python scripts/populate_formation_metadata.py --dry-run      # preview without writing
  python scripts/populate_formation_metadata.py --report        # statistics only
"""

import argparse
import os
import sqlite3
import sys
from collections import Counter


TRILOBASE_DB = os.path.join(os.path.dirname(__file__), '..', 'trilobase.db')
PALEOCORE_DB = os.path.join(os.path.dirname(__file__), '..', 'paleocore.db')


def get_connection():
    """Open trilobase.db and ATTACH paleocore.db as pc."""
    conn = sqlite3.connect(TRILOBASE_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"ATTACH DATABASE '{PALEOCORE_DB}' AS pc")
    return conn


def compute_country_mapping(conn):
    """
    For each formation, find the most frequent country among its linked genera.

    Uses genus_locations.region_id → geographic_regions (which has standardized
    country names). For region-level entries, resolve to parent country.

    Returns: dict[formation_id] -> country_name
    """
    rows = conn.execute("""
        SELECT gf.formation_id,
               CASE gr.level
                   WHEN 'country' THEN gr.name
                   WHEN 'region'  THEN p.name
               END AS country_name
        FROM genus_formations gf
        JOIN genus_locations gl ON gf.genus_id = gl.genus_id
        JOIN pc.geographic_regions gr ON gl.region_id = gr.id
        LEFT JOIN pc.geographic_regions p ON gr.parent_id = p.id
    """).fetchall()

    # Group by formation_id and count countries
    formation_countries = {}
    for formation_id, country_name in rows:
        if country_name is None:
            continue
        if formation_id not in formation_countries:
            formation_countries[formation_id] = Counter()
        formation_countries[formation_id][country_name] += 1

    # Pick most common country for each formation
    result = {}
    multi_country = {}
    for fid, counter in formation_countries.items():
        most_common = counter.most_common()
        result[fid] = most_common[0][0]
        if len(most_common) > 1:
            multi_country[fid] = most_common

    return result, multi_country


def compute_period_mapping(conn):
    """
    For each formation, find the most frequent period name among its linked genera.

    Uses temporal_ranges.name (human-readable, e.g. "Lower Cambrian").

    Returns: dict[formation_id] -> period_name
    """
    rows = conn.execute("""
        SELECT gf.formation_id, tr.name AS period_name
        FROM genus_formations gf
        JOIN taxonomic_ranks t ON gf.genus_id = t.id
        JOIN pc.temporal_ranges tr ON t.temporal_code = tr.code
        WHERE t.temporal_code IS NOT NULL
          AND t.temporal_code != 'INDET'
    """).fetchall()

    # Group by formation_id and count period names
    formation_periods = {}
    for formation_id, period_name in rows:
        if period_name is None:
            continue
        if formation_id not in formation_periods:
            formation_periods[formation_id] = Counter()
        formation_periods[formation_id][period_name] += 1

    # Pick most common period for each formation
    result = {}
    multi_period = {}
    for fid, counter in formation_periods.items():
        most_common = counter.most_common()
        result[fid] = most_common[0][0]
        if len(most_common) > 1:
            multi_period[fid] = most_common

    return result, multi_period


def get_formation_names(conn):
    """Get formation_id → name mapping."""
    rows = conn.execute("SELECT id, name FROM pc.formations").fetchall()
    return {r[0]: r[1] for r in rows}


def print_report(conn, country_map, multi_country, period_map, multi_period):
    """Print detailed report of what would be updated."""
    total = conn.execute("SELECT COUNT(*) FROM pc.formations").fetchone()[0]
    names = get_formation_names(conn)

    print(f"\n{'='*60}")
    print(f"Formation Metadata Backfill Report")
    print(f"{'='*60}")
    print(f"\nTotal formations: {total}")
    print(f"Country resolvable: {len(country_map)} ({len(country_map)*100/total:.1f}%)")
    print(f"Period resolvable:  {len(period_map)} ({len(period_map)*100/total:.1f}%)")
    print(f"Country not resolvable: {total - len(country_map)}")
    print(f"Period not resolvable:  {total - len(period_map)}")

    # Multi-country formations
    print(f"\n--- Multi-country formations: {len(multi_country)} ---")
    for fid, counts in sorted(multi_country.items(), key=lambda x: -sum(c for _, c in x[1])):
        name = names.get(fid, f"id={fid}")
        parts = [f"{c}({n})" for c, n in counts]
        chosen = counts[0][0]
        print(f"  {name}: {', '.join(parts)} → {chosen}")

    # Multi-period formations
    print(f"\n--- Multi-period formations: {len(multi_period)} ---")
    for fid, counts in sorted(multi_period.items(), key=lambda x: -sum(c for _, c in x[1])):
        name = names.get(fid, f"id={fid}")
        parts = [f"{p}({n})" for p, n in counts]
        chosen = counts[0][0]
        print(f"  {name}: {', '.join(parts)} → {chosen}")

    # Unresolvable formations
    all_ids = set(names.keys())
    no_country = all_ids - set(country_map.keys())
    no_period = all_ids - set(period_map.keys())

    if no_country:
        print(f"\n--- Formations without country ({len(no_country)}) ---")
        for fid in sorted(no_country):
            print(f"  {names[fid]}")

    if no_period:
        print(f"\n--- Formations without period ({len(no_period)}) ---")
        for fid in sorted(no_period):
            print(f"  {names[fid]}")

    # Sample output
    print(f"\n--- Sample updates (first 20) ---")
    count = 0
    for fid in sorted(country_map.keys()):
        if count >= 20:
            break
        name = names.get(fid, f"id={fid}")
        country = country_map.get(fid, '(none)')
        period = period_map.get(fid, '(none)')
        print(f"  {name}: country={country}, period={period}")
        count += 1


def apply_updates(conn, country_map, period_map):
    """Write country and period to paleocore.db formations table."""
    pc_conn = sqlite3.connect(PALEOCORE_DB)
    pc_conn.execute("PRAGMA journal_mode=WAL")

    updated_country = 0
    updated_period = 0

    for fid, country in country_map.items():
        pc_conn.execute(
            "UPDATE formations SET country = ? WHERE id = ?",
            (country, fid)
        )
        updated_country += 1

    for fid, period in period_map.items():
        pc_conn.execute(
            "UPDATE formations SET period = ? WHERE id = ?",
            (period, fid)
        )
        updated_period += 1

    pc_conn.commit()
    pc_conn.close()

    return updated_country, updated_period


def main():
    parser = argparse.ArgumentParser(
        description='Populate formations.country and formations.period in paleocore.db')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be updated without writing')
    parser.add_argument('--report', action='store_true',
                        help='Print detailed report only')
    args = parser.parse_args()

    if not os.path.exists(TRILOBASE_DB):
        print(f"Error: trilobase.db not found at {TRILOBASE_DB}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(PALEOCORE_DB):
        print(f"Error: paleocore.db not found at {PALEOCORE_DB}", file=sys.stderr)
        sys.exit(1)

    conn = get_connection()

    print("Computing country mapping...")
    country_map, multi_country = compute_country_mapping(conn)
    print(f"  → {len(country_map)} formations mapped to country "
          f"({len(multi_country)} with multiple countries)")

    print("Computing period mapping...")
    period_map, multi_period = compute_period_mapping(conn)
    print(f"  → {len(period_map)} formations mapped to period "
          f"({len(multi_period)} with multiple periods)")

    if args.report or args.dry_run:
        print_report(conn, country_map, multi_country, period_map, multi_period)
        if args.dry_run:
            print("\n[DRY RUN] No changes written.")
        conn.close()
        return

    # Apply updates
    updated_country, updated_period = apply_updates(conn, country_map, period_map)
    conn.close()

    print(f"\nDone!")
    print(f"  Updated country: {updated_country} formations")
    print(f"  Updated period:  {updated_period} formations")

    # Verify
    verify_conn = sqlite3.connect(PALEOCORE_DB)
    null_country = verify_conn.execute(
        "SELECT COUNT(*) FROM formations WHERE country IS NULL").fetchone()[0]
    null_period = verify_conn.execute(
        "SELECT COUNT(*) FROM formations WHERE period IS NULL").fetchone()[0]
    total = verify_conn.execute("SELECT COUNT(*) FROM formations").fetchone()[0]
    verify_conn.close()

    print(f"\nVerification:")
    print(f"  Total formations: {total}")
    print(f"  Country NULL: {null_country}")
    print(f"  Period NULL:  {null_period}")


if __name__ == '__main__':
    main()
