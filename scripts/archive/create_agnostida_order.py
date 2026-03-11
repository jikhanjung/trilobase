#!/usr/bin/env python3
"""
Create Agnostida Order and move 10 families via PLACED_IN opinions.

1. Insert Agnostida Order under Class Trilobita (parent_id=1)
2. Insert 10 PLACED_IN opinions (is_accepted=1) → triggers auto-move parent_id
3. Recalculate Order Uncertain genera_count

Idempotent: skips if Agnostida Order already exists.
"""

import argparse
import sqlite3
import sys

DB_PATH = 'db/trilobase.db'

AGNOSTIDA_FAMILIES = [
    (201, 'Agnostidae', 32),
    (202, 'Ammagnostidae', 13),
    (206, 'Clavagnostidae', 11),
    (207, 'Condylopygidae', 3),
    (209, 'Diplagnostidae', 33),
    (211, 'Doryagnostidae', 3),
    (212, 'Glyptagnostidae', 3),
    (213, 'Metagnostidae', 23),
    (216, 'Peronopsidae', 21),
    (218, 'Ptychagnostidae', 20),
]

ORDER_UNCERTAIN_ID = 144


def create_agnostida_order(db_path: str, dry_run: bool = False) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = {'agnostida_id': None, 'opinions_created': 0, 'skipped': []}

    # Step 1: Create Agnostida Order (idempotent)
    existing = cursor.execute(
        "SELECT id FROM taxonomic_ranks WHERE name = 'Agnostida' AND rank = 'Order'"
    ).fetchone()

    if existing:
        agnostida_id = existing['id']
        results['agnostida_id'] = agnostida_id
        print(f"  Agnostida Order already exists (id={agnostida_id})")
    else:
        total_genera = sum(g for _, _, g in AGNOSTIDA_FAMILIES)
        print(f"  Create Agnostida Order (parent_id=1, genera_count={total_genera})")
        if not dry_run:
            cursor.execute("""
                INSERT INTO taxonomic_ranks (name, rank, parent_id, author, year, genera_count, notes,
                    uid, uid_method, uid_confidence)
                VALUES ('Agnostida', 'Order', 1, 'SALTER', '1864', ?,
                    'Order created based on traditional classification. Excluded from Adrain (2011) Trilobita sensu stricto.',
                    'scoda:taxon:order:Agnostida', 'name', 'high')
            """, (total_genera,))
            agnostida_id = cursor.lastrowid
            results['agnostida_id'] = agnostida_id
            print(f"  → Agnostida id={agnostida_id}")
        else:
            agnostida_id = '<new>'
            results['agnostida_id'] = agnostida_id

    # Step 2: Create PLACED_IN opinions for each family
    for fam_id, fam_name, genera in AGNOSTIDA_FAMILIES:
        # Check if opinion already exists
        existing_op = cursor.execute(
            "SELECT id FROM taxonomic_opinions WHERE taxon_id = ? AND opinion_type = 'PLACED_IN'",
            (fam_id,)
        ).fetchone()

        if existing_op:
            results['skipped'].append(f"{fam_name} (id={fam_id}, opinion already exists)")
            continue

        # Verify family is currently under Order Uncertain
        fam = cursor.execute(
            'SELECT parent_id FROM taxonomic_ranks WHERE id = ?', (fam_id,)
        ).fetchone()
        if not fam:
            print(f"  WARNING: Family id={fam_id} ({fam_name}) not found!")
            continue
        if fam['parent_id'] != ORDER_UNCERTAIN_ID:
            results['skipped'].append(f"{fam_name} (id={fam_id}, parent_id={fam['parent_id']} != {ORDER_UNCERTAIN_ID})")
            continue

        print(f"  Opinion: {fam_name} (id={fam_id}, {genera} genera) → Agnostida")
        if not dry_run:
            cursor.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
                     assertion_status, curation_confidence, is_accepted, notes)
                VALUES (?, 'PLACED_IN', ?, NULL, 'asserted', 'medium', 1,
                    'Traditional classification. Family name contains agnostid root. Adrain (2011) excluded Agnostida from Trilobita sensu stricto classification.')
            """, (fam_id, agnostida_id))
        results['opinions_created'] += 1

    # Step 3: Recalculate Order Uncertain genera_count
    if not dry_run:
        new_count = cursor.execute("""
            SELECT COALESCE(SUM(tr.genera_count), 0) as cnt
            FROM taxonomic_ranks tr
            WHERE tr.parent_id = ? AND tr.rank = 'Family'
        """, (ORDER_UNCERTAIN_ID,)).fetchone()['cnt']
        cursor.execute(
            'UPDATE taxonomic_ranks SET genera_count = ? WHERE id = ?',
            (new_count, ORDER_UNCERTAIN_ID)
        )
        print(f"\n  Order Uncertain genera_count updated to {new_count}")

        conn.commit()
        print(f"Committed. Created Agnostida Order + {results['opinions_created']} opinions.")
    else:
        remaining_families = 78 - 10  # after Group A fix: 78, minus Agnostida 10
        remaining_genera = sum(
            g for fid, _, g in AGNOSTIDA_FAMILIES
            if not any(s for s in results['skipped'] if f"id={fid}" in s)
        )
        print(f"\n[DRY RUN] Would create Agnostida Order + {results['opinions_created']} opinions.")
        print(f"  Order Uncertain would have ~{remaining_families} families")

    if results['skipped']:
        print(f"Skipped: {results['skipped']}")

    conn.close()
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Agnostida Order with PLACED_IN opinions')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--db', default=DB_PATH, help=f'Database path (default: {DB_PATH})')
    args = parser.parse_args()

    print(f"=== Create Agnostida Order ===")
    print(f"DB: {args.db}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLY'}\n")

    create_agnostida_order(args.db, dry_run=args.dry_run)
