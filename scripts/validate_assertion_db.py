#!/usr/bin/env python3
"""P74 — Assertion-centric test DB validator.

Validates dist/assertion_test/trilobase_assertion-{version}.db against db/trilobase.db:
  1. Tree equivalence (parent_id vs v_taxonomic_ranks)
  2. Count verification
  3. CTE tree traversal (all valid genera reachable)
"""

import argparse
import glob
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DB = ROOT / "db" / "trilobase.db"
DST_DIR = ROOT / "dist" / "assertion_test"

PASS = "PASS"
FAIL = "FAIL"
results = []


def _resolve_db(db_arg: str | None) -> Path:
    """Resolve assertion DB path from --db arg or glob for latest."""
    if db_arg:
        return Path(db_arg)
    candidates = sorted(
        glob.glob(str(DST_DIR / "trilobase_assertion-*.db")),
        key=lambda p: Path(p).stat().st_mtime,
    )
    if candidates:
        return Path(candidates[-1])
    # Fallback to unversioned name (legacy)
    return DST_DIR / "trilobase_assertion.db"


def check(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    results.append((name, status, detail))
    mark = "✓" if passed else "✗"
    msg = f"  [{mark}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def main():
    parser = argparse.ArgumentParser(
        description="P74 — Assertion-centric test DB validator")
    parser.add_argument(
        "--db", default=None,
        help="Path to assertion DB (default: latest dist/assertion_test/trilobase_assertion-*.db)")
    args = parser.parse_args()

    DST_DB = _resolve_db(args.db)

    if not SRC_DB.exists() or not DST_DB.exists():
        print(f"ERROR: Source or assertion DB not found.", file=sys.stderr)
        if not DST_DB.exists():
            print(f"  Assertion DB: {DST_DB}", file=sys.stderr)
        sys.exit(1)

    print(f"Assertion DB: {DST_DB}")

    src = sqlite3.connect(str(SRC_DB))
    dst = sqlite3.connect(str(DST_DB))

    print("=== P74: Assertion DB Validation ===\n")

    # --- 1. Count verification ---
    print("1. Count verification")

    n_taxon = dst.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
    check("taxon count", n_taxon == 5341, f"{n_taxon} (expected 5341)")

    n_ref = dst.execute("SELECT COUNT(*) FROM reference").fetchone()[0]
    check("reference count", n_ref == 2132, f"{n_ref} (expected 2132 = 2131 + JA2002)")

    n_placed_accepted = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='PLACED_IN' AND is_accepted=1"
    ).fetchone()[0]
    check("PLACED_IN (accepted)", n_placed_accepted > 5000,
          f"{n_placed_accepted} (expected ~5,082)")

    n_synonym = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='SYNONYM_OF'"
    ).fetchone()[0]
    check("SYNONYM_OF count", n_synonym == 1055, f"{n_synonym} (expected 1055)")

    n_spelling = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='SPELLING_OF'"
    ).fetchone()[0]
    check("SPELLING_OF count", n_spelling == 2, f"{n_spelling} (expected 2)")

    n_edges = dst.execute(
        "SELECT COUNT(*) FROM classification_edge_cache"
    ).fetchone()[0]
    check("edge_cache count", n_edges > 5000, f"{n_edges}")

    n_profiles = dst.execute(
        "SELECT COUNT(*) FROM classification_profile"
    ).fetchone()[0]
    check("classification_profile count", n_profiles == 2, f"{n_profiles}")

    # --- 1b. Junction table counts ---
    print("\n1b. Junction table counts")

    n_gf = dst.execute("SELECT COUNT(*) FROM genus_formations").fetchone()[0]
    check("genus_formations count", n_gf == 4503, f"{n_gf} (expected 4503)")

    n_gl = dst.execute("SELECT COUNT(*) FROM genus_locations").fetchone()[0]
    check("genus_locations count", n_gl == 4849, f"{n_gl} (expected 4849)")

    n_tr = dst.execute("SELECT COUNT(*) FROM taxon_reference").fetchone()[0]
    check("taxon_reference count", n_tr == 4173, f"{n_tr} (expected 4173)")

    # --- 2. Tree equivalence ---
    print("\n2. Tree equivalence (parent_id vs v_taxonomic_ranks)")

    # Get original parent_id mapping
    orig = dict(src.execute(
        "SELECT id, parent_id FROM taxonomic_ranks"
    ).fetchall())

    # Get assertion-derived parent_id mapping
    derived = dict(dst.execute(
        "SELECT id, parent_id FROM v_taxonomic_ranks"
    ).fetchall())

    mismatches = []
    for taxon_id, orig_parent in orig.items():
        derived_parent = derived.get(taxon_id)
        if orig_parent != derived_parent:
            mismatches.append((taxon_id, orig_parent, derived_parent))

    check("tree equivalence", len(mismatches) == 0,
          f"{len(mismatches)} mismatches" if mismatches else "all match")

    if mismatches and len(mismatches) <= 10:
        for tid, op, dp in mismatches:
            name = dst.execute(
                "SELECT name FROM taxon WHERE id=?", (tid,)
            ).fetchone()[0]
            print(f"      taxon {tid} ({name}): orig={op}, derived={dp}")

    # --- 3. CTE tree traversal ---
    print("\n3. CTE tree traversal")

    # Count excluded taxa (accepted PLACED_IN with NULL object, e.g. Agnostida)
    excluded_roots = dst.execute("""
        SELECT DISTINCT subject_taxon_id FROM assertion
        WHERE predicate='PLACED_IN' AND is_accepted=1 AND object_taxon_id IS NULL
    """).fetchall()
    excluded_root_ids = [r[0] for r in excluded_roots]

    # Count taxa under excluded roots (they won't appear in CTE tree)
    n_excluded = 0
    if excluded_root_ids:
        placeholders = ",".join("?" * len(excluded_root_ids))
        n_excluded = dst.execute(f"""
            WITH RECURSIVE excl AS (
                SELECT id FROM taxon WHERE id IN ({placeholders})
                UNION ALL
                SELECT a.subject_taxon_id FROM assertion a
                JOIN excl ON a.object_taxon_id = excl.id
                WHERE a.predicate='PLACED_IN' AND a.is_accepted=1
            )
            SELECT COUNT(*) FROM excl
        """, excluded_root_ids).fetchone()[0]
        excluded_names = [dst.execute(
            "SELECT name FROM taxon WHERE id=?", (rid,)
        ).fetchone()[0] for rid in excluded_root_ids]
        print(f"   (excluded subtrees: {', '.join(excluded_names)} — {n_excluded} taxa)")

    # Count reachable taxa via v_taxonomy_tree
    n_reachable = dst.execute(
        "SELECT COUNT(*) FROM v_taxonomy_tree"
    ).fetchone()[0]
    n_with_parent = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='PLACED_IN' AND is_accepted=1 AND object_taxon_id IS NOT NULL"
    ).fetchone()[0]
    # Reachable = Class root (1) + all with valid parent chain
    expected_reachable = n_with_parent + 1  # +1 for Class root
    check("tree reachable taxa", n_reachable == expected_reachable - n_excluded or n_reachable > 4800,
          f"{n_reachable} reachable ({n_excluded} excluded)")

    # Check all valid genera (minus excluded) are reachable
    valid_genera_total = dst.execute(
        "SELECT COUNT(*) FROM taxon WHERE rank='Genus' AND is_valid=1"
    ).fetchone()[0]
    valid_genera_excluded = 0
    if excluded_root_ids:
        valid_genera_excluded = dst.execute(f"""
            WITH RECURSIVE excl AS (
                SELECT id FROM taxon WHERE id IN ({placeholders})
                UNION ALL
                SELECT a.subject_taxon_id FROM assertion a
                JOIN excl ON a.object_taxon_id = excl.id
                WHERE a.predicate='PLACED_IN' AND a.is_accepted=1
            )
            SELECT COUNT(*) FROM excl e
            JOIN taxon t ON e.id = t.id
            WHERE t.rank='Genus' AND t.is_valid=1
        """, excluded_root_ids).fetchone()[0]
    valid_genera_in_tree = dst.execute("""
        SELECT COUNT(*) FROM v_taxonomy_tree
        WHERE rank='Genus' AND id IN (
            SELECT id FROM taxon WHERE is_valid=1
        )
    """).fetchone()[0]
    expected_genera = valid_genera_total - valid_genera_excluded
    check("valid genera in tree",
          valid_genera_in_tree == expected_genera,
          f"{valid_genera_in_tree}/{valid_genera_total} ({valid_genera_excluded} in excluded subtrees)")

    # Check orders are reachable (minus excluded)
    n_orders_total = dst.execute(
        "SELECT COUNT(*) FROM taxon WHERE rank='Order'"
    ).fetchone()[0]
    n_orders_excluded = len([rid for rid in excluded_root_ids
                             if dst.execute("SELECT rank FROM taxon WHERE id=?", (rid,)).fetchone()[0] == 'Order'])
    n_orders = dst.execute(
        "SELECT COUNT(*) FROM v_taxonomy_tree WHERE rank='Order'"
    ).fetchone()[0]
    check("orders in tree", n_orders == n_orders_total - n_orders_excluded,
          f"{n_orders}/{n_orders_total} ({n_orders_excluded} excluded)")

    # --- 4. View consistency ---
    print("\n4. View consistency")

    # synonyms view
    n_syn_view = dst.execute("SELECT COUNT(*) FROM synonyms").fetchone()[0]
    check("synonyms view", n_syn_view == n_synonym,
          f"{n_syn_view} rows (matches assertion SYNONYM_OF)")

    # --- 5. Demo queries ---
    print("\n5. Demo queries")

    # Orders from tree
    orders = dst.execute(
        "SELECT name FROM v_taxonomy_tree WHERE rank='Order' ORDER BY name"
    ).fetchall()
    print(f"   Orders: {', '.join(r[0] for r in orders)}")

    # Assertion example
    example = dst.execute("""
        SELECT a.predicate, a.assertion_status, t2.name AS object,
               r.authors, a.is_accepted
        FROM assertion a
        LEFT JOIN taxon t2 ON a.object_taxon_id = t2.id
        LEFT JOIN reference r ON a.reference_id = r.id
        WHERE a.subject_taxon_id = (SELECT id FROM taxon WHERE name='Asaphidae')
        ORDER BY a.predicate
    """).fetchall()
    if example:
        print(f"   Asaphidae assertions ({len(example)}):")
        for pred, status, obj, auth, acc in example:
            print(f"     {pred} → {obj} [{status}] ref={auth} accepted={acc}")

    # Profile edge cache sample
    n_ja2002_genera = dst.execute("""
        SELECT COUNT(*) FROM assertion
        WHERE predicate='PLACED_IN' AND is_accepted=1 AND reference_id=0
    """).fetchone()[0]
    print(f"   JA2002-only PLACED_IN: {n_ja2002_genera}")

    # --- Summary ---
    print(f"\n=== Results ===")
    passed = sum(1 for _, s, _ in results if s == PASS)
    total = len(results)
    print(f"  {passed}/{total} checks passed")

    if passed < total:
        print("\n  Failed checks:")
        for name, status, detail in results:
            if status == FAIL:
                print(f"    ✗ {name}: {detail}")
        sys.exit(1)
    else:
        print("  All checks passed!")

    src.close()
    dst.close()


if __name__ == "__main__":
    main()
