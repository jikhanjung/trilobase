#!/usr/bin/env python3
"""
Restructure Agnostida opinions: family-level → order-level.

Agnostida families always belong to Agnostida (undisputed). The dispute is
whether Agnostida itself belongs in Trilobita:
  - JA2002: included Agnostida in Trilobita (genus list contains agnostid genera)
  - A2011:  excluded Agnostida from Trilobita sensu stricto

This script:
  1. Deletes 10 family PLACED_IN Agnostida opinions (unnecessary)
  2. Inserts 2 order-level opinions for Agnostida:
     - JA2002: PLACED_IN Trilobita (is_accepted=0)
     - A2011:  PLACED_IN NULL = excluded (is_accepted=1) → trigger sets parent_id=NULL

Idempotent. Usage:
    python scripts/restructure_agnostida_opinions.py [--dry-run]
"""

import argparse
import sqlite3
import sys

DB_PATH = 'db/trilobase.db'

AGNOSTIDA_ID = 5341
TRILOBITA_ID = 1
ADRAIN_2011_BIB_ID = 2131


def main():
    parser = argparse.ArgumentParser(description='Restructure Agnostida opinions')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    dry_run = args.dry_run

    if dry_run:
        print("=== DRY RUN MODE ===\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # Step 1: Delete family-level PLACED_IN opinions for Agnostida
        family_opinions = conn.execute(
            "SELECT o.id, t.name FROM taxonomic_opinions o "
            "JOIN taxonomic_ranks t ON o.taxon_id = t.id "
            "WHERE o.opinion_type = 'PLACED_IN' AND o.related_taxon_id = ? "
            "AND t.rank = 'Family'",
            (AGNOSTIDA_ID,)
        ).fetchall()

        if family_opinions:
            ids = [r[0] for r in family_opinions]
            names = [r[1] for r in family_opinions]
            print(f"Step 1: Delete {len(family_opinions)} family PLACED_IN opinions")
            for name in names:
                print(f"  - {name}")
            if not dry_run:
                conn.execute(
                    f"DELETE FROM taxonomic_opinions WHERE id IN ({','.join('?' * len(ids))})",
                    ids
                )
                print(f"  Deleted {len(ids)} opinions.")
        else:
            print("Step 1: SKIP — no family PLACED_IN opinions for Agnostida")

        # Step 2: Insert order-level opinions for Agnostida
        existing = conn.execute(
            "SELECT id, related_taxon_id, is_accepted, notes FROM taxonomic_opinions "
            "WHERE taxon_id = ? AND opinion_type = 'PLACED_IN'",
            (AGNOSTIDA_ID,)
        ).fetchall()

        has_ja2002 = any(r[1] == TRILOBITA_ID for r in existing)
        has_a2011 = any(r[1] is None for r in existing)

        print(f"\nStep 2: Insert Agnostida order-level opinions")

        if has_ja2002:
            print("  SKIP: JA2002 opinion already exists")
        else:
            print("  Inserting JA2002: Agnostida PLACED_IN Trilobita (not accepted)")
            if not dry_run:
                conn.execute(
                    "INSERT INTO taxonomic_opinions "
                    "(taxon_id, opinion_type, related_taxon_id, bibliography_id, "
                    " assertion_status, curation_confidence, is_accepted, notes) "
                    "VALUES (?, 'PLACED_IN', ?, NULL, 'asserted', 'high', 0, ?)",
                    (AGNOSTIDA_ID, TRILOBITA_ID,
                     'Jell & Adrain (2002) included Agnostida genera in their trilobite genus list, '
                     'implicitly placing Agnostida within Trilobita.')
                )

        if has_a2011:
            print("  SKIP: A2011 opinion already exists")
        else:
            print("  Inserting A2011: Agnostida excluded from Trilobita (accepted)")
            if not dry_run:
                conn.execute(
                    "INSERT INTO taxonomic_opinions "
                    "(taxon_id, opinion_type, related_taxon_id, bibliography_id, "
                    " assertion_status, curation_confidence, is_accepted, notes) "
                    "VALUES (?, 'PLACED_IN', NULL, ?, 'asserted', 'high', 1, ?)",
                    (AGNOSTIDA_ID, ADRAIN_2011_BIB_ID,
                     'Adrain (2011) excluded Agnostida from Trilobita sensu stricto. '
                     'Suprafamilial classification does not include agnostid families.')
                )

        if not dry_run:
            conn.commit()

            # Verify
            parent = conn.execute(
                "SELECT parent_id FROM taxonomic_ranks WHERE id = ?", (AGNOSTIDA_ID,)
            ).fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM taxonomic_opinions").fetchone()[0]
            families = conn.execute(
                "SELECT COUNT(*) FROM taxonomic_ranks WHERE parent_id = ? AND rank = 'Family'",
                (AGNOSTIDA_ID,)
            ).fetchone()[0]

            print(f"\nVerification:")
            print(f"  Agnostida parent_id: {parent} (expected: None)")
            print(f"  Agnostida families:  {families} (expected: 10)")
            print(f"  Total opinions:      {total} (expected: 6)")
        else:
            print("\n[DRY RUN] No changes made.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
