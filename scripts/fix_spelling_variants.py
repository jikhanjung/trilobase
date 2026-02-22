#!/usr/bin/env python3
"""
Fix Group A spelling variant duplicates in trilobase.db.

Three cases:
  1. Shirakiellidae (id=196): empty duplicate → delete
  2. Dokimocephalidae (id=210) → Dokimokephalidae (id=134): move 46 genera, delete
  3. Chengkouaspidae (id=205) → Chengkouaspididae (id=36): move 11 genera, delete

Idempotent: skips if source entries already deleted.
"""

import argparse
import sqlite3
import sys

DB_PATH = 'db/trilobase.db'

CASES = [
    {
        'label': 'Shirakiellidae duplicate',
        'source_id': 196,
        'target_id': None,  # just delete, no genera to move
        'expected_genera': 0,
    },
    {
        'label': 'Dokimocephalidae → Dokimokephalidae',
        'source_id': 210,
        'target_id': 134,
        'expected_genera': 46,
    },
    {
        'label': 'Chengkouaspidae → Chengkouaspididae',
        'source_id': 205,
        'target_id': 36,
        'expected_genera': 11,
    },
]


def fix_spelling_variants(db_path: str, dry_run: bool = False) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {'deleted': [], 'moved_genera': 0, 'skipped': []}

    for case in CASES:
        sid = case['source_id']
        tid = case['target_id']

        # Check if source still exists
        row = cursor.execute(
            'SELECT id, name, genera_count FROM taxonomic_ranks WHERE id = ?', (sid,)
        ).fetchone()
        if not row:
            results['skipped'].append(f"{case['label']} (id={sid} already deleted)")
            continue

        # Count children to move
        children = cursor.execute(
            'SELECT COUNT(*) as cnt FROM taxonomic_ranks WHERE parent_id = ?', (sid,)
        ).fetchone()['cnt']

        # Check FK safety
        for tbl, col in [
            ('taxon_bibliography', 'taxon_id'),
            ('synonyms', 'junior_taxon_id'),
            ('taxonomic_opinions', 'taxon_id'),
            ('taxonomic_opinions', 'related_taxon_id'),
        ]:
            fk_count = cursor.execute(
                f'SELECT COUNT(*) as cnt FROM {tbl} WHERE {col} = ?', (sid,)
            ).fetchone()['cnt']
            if fk_count > 0:
                print(f"ERROR: {case['label']} has {fk_count} FK references in {tbl}.{col}")
                conn.close()
                sys.exit(1)

        if tid and children > 0:
            print(f"  Move {children} genera: parent_id {sid} → {tid}")
            if not dry_run:
                cursor.execute(
                    'UPDATE taxonomic_ranks SET parent_id = ? WHERE parent_id = ?',
                    (tid, sid)
                )
                # Update genera_count on target
                new_count = cursor.execute(
                    'SELECT SUM(genera_count) as cnt FROM taxonomic_ranks WHERE parent_id = ? AND rank = ?',
                    (tid, 'Genus')
                ).fetchone()
                # Use children count since these are genera
                cursor.execute(
                    'UPDATE taxonomic_ranks SET genera_count = ? WHERE id = ?',
                    (children, tid)
                )
            results['moved_genera'] += children

        print(f"  Delete id={sid} ({row['name']})")
        if not dry_run:
            cursor.execute('DELETE FROM taxonomic_ranks WHERE id = ?', (sid,))
        results['deleted'].append(sid)

    if not dry_run:
        conn.commit()
        print(f"\nCommitted. Deleted {len(results['deleted'])} entries, moved {results['moved_genera']} genera.")
    else:
        print(f"\n[DRY RUN] Would delete {len(results['deleted'])} entries, move {results['moved_genera']} genera.")

    if results['skipped']:
        print(f"Skipped: {results['skipped']}")

    conn.close()
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fix spelling variant duplicates')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--db', default=DB_PATH, help=f'Database path (default: {DB_PATH})')
    args = parser.parse_args()

    print(f"=== Fix Spelling Variants ===")
    print(f"DB: {args.db}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLY'}\n")

    fix_spelling_variants(args.db, dry_run=args.dry_run)
