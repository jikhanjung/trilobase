#!/usr/bin/env python3
"""Rebuild Trilobase + PaleoCore databases from source texts.

Usage:
    python scripts/rebuild_database.py [--output-dir DIR] [--validate] [--ref-db PATH]

This orchestrator runs the modular pipeline steps in order:
  1. clean      — load source text files
  2. hierarchy  — parse adrain2011.txt → hierarchy nodes
  3. parse      — parse genus entries → GenusRecord list
  4. load_data  — create trilobase.db (schema, ranks, opinions, bibliography)
  5. paleocore  — create paleocore.db (countries, formations, COW, ICS, regions)
  6. junctions  — populate genus_formations, genus_locations
  7. metadata   — insert SCODA metadata + UI queries
  8. validate   — verify counts against expected values
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

# Project root (one level up from scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(
        description='Rebuild Trilobase databases from source texts.')
    parser.add_argument(
        '--output-dir', '-o', type=Path,
        default=PROJECT_ROOT / 'dist' / 'rebuild',
        help='Output directory for rebuilt databases (default: dist/rebuild/)')
    parser.add_argument(
        '--validate', '-v', action='store_true',
        help='Run validation checks after build')
    parser.add_argument(
        '--ref-db', type=Path,
        default=PROJECT_ROOT / 'db' / 'trilobase.db',
        help='Reference DB for ui_queries/manifest (default: db/trilobase.db)')
    args = parser.parse_args()

    out_dir: Path = args.output_dir
    ref_db: Path = args.ref_db

    # Source data paths
    genus_list_path = PROJECT_ROOT / 'data' / 'trilobite_genus_list.txt'
    adrain_path = PROJECT_ROOT / 'data' / 'adrain2011.txt'
    bib_path = PROJECT_ROOT / 'data' / 'Jell_and_Adrain_2002_Literature_Cited.txt'
    cow_csv_path = PROJECT_ROOT / 'vendor' / 'cow' / 'v2024' / 'States2024' / 'statelist2024.csv'
    ics_ttl_path = PROJECT_ROOT / 'vendor' / 'ics' / 'gts2020' / 'chart.ttl'

    # Verify source files exist
    missing = []
    for label, p in [('genus list', genus_list_path),
                     ('adrain2011', adrain_path),
                     ('bibliography', bib_path),
                     ('COW csv', cow_csv_path),
                     ('ICS ttl', ics_ttl_path)]:
        if not p.exists():
            missing.append(f'  {label}: {p}')
    if missing:
        print('ERROR: Missing source files:')
        for m in missing:
            print(m)
        sys.exit(1)

    # Prepare output directory
    out_dir.mkdir(parents=True, exist_ok=True)
    trilobase_path = out_dir / 'trilobase.db'
    paleocore_path = out_dir / 'paleocore.db'

    # Remove old files if present
    for p in [trilobase_path, paleocore_path]:
        if p.exists():
            p.unlink()

    t_start = time.time()

    # --- Step 1: Clean (text loading) ---
    _step('Step 1: Loading source texts')
    from pipeline.clean import load_genus_list
    lines = load_genus_list(genus_list_path)
    print(f'    {len(lines)} genus lines loaded')

    # --- Step 2: Hierarchy ---
    _step('Step 2: Parsing hierarchy')
    from pipeline.hierarchy import parse_hierarchy
    hierarchy_nodes = parse_hierarchy(adrain_path)
    print(f'    {len(hierarchy_nodes)} hierarchy nodes')

    # --- Step 3: Parse genera ---
    _step('Step 3: Parsing genera')
    from pipeline.parse_genera import parse_all
    genera = parse_all(lines)
    print(f'    {len(genera)} genera parsed')

    # --- Step 4: Load data (trilobase.db) ---
    _step('Step 4: Creating trilobase.db')
    from pipeline.load_data import load_all
    name_to_id = load_all(trilobase_path, hierarchy_nodes, genera, bib_path)
    print(f'    name_to_id: {len(name_to_id)} entries')

    # --- Step 5: PaleoCore ---
    _step('Step 5: Creating paleocore.db')
    from pipeline.paleocore import create_paleocore
    country_map, formation_map = create_paleocore(
        paleocore_path, genera, cow_csv_path, ics_ttl_path)
    print(f'    {len(country_map)} countries, {len(formation_map)} formations')

    # --- Step 6: Junctions ---
    _step('Step 6: Populating junction tables')
    from pipeline.junctions import load_junctions
    load_junctions(trilobase_path, paleocore_path,
                   genera, name_to_id, country_map, formation_map)

    # --- Step 7: Metadata ---
    _step('Step 7: Loading SCODA metadata')
    from pipeline.metadata import load_metadata
    load_metadata(trilobase_path, ref_db if ref_db.exists() else None)

    elapsed = time.time() - t_start
    print(f'\n  Build complete in {elapsed:.1f}s')
    print(f'    trilobase.db: {trilobase_path}')
    print(f'    paleocore.db: {paleocore_path}')

    # --- Step 8: Validate ---
    if args.validate:
        _step('Step 8: Validation')
        from pipeline.validate import validate
        passed, failed = validate(trilobase_path, paleocore_path)
        if failed > 0:
            print(f'\n  WARNING: {failed} validation(s) failed!')
            sys.exit(2)
        else:
            print(f'\n  All {passed} validations passed.')

    return 0


def _step(label: str):
    """Print a step header."""
    print(f'\n  [{label}]')


if __name__ == '__main__':
    sys.exit(main() or 0)
