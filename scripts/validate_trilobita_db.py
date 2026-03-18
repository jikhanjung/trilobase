#!/usr/bin/env python3
"""P74 — Trilobita DB validator.

Validates db/trilobita-{version}.db against db/trilobita-canonical-{version}.db:
  1. Tree equivalence (parent_id vs v_taxonomic_ranks)
  2. Count verification
  3. CTE tree traversal (all valid genera reachable)
"""

import argparse
import glob
import sqlite3
import sys
from pathlib import Path

from db_path import find_canonical_db

ROOT = Path(__file__).resolve().parent.parent
SRC_DB = Path(find_canonical_db())
DST_DIR = ROOT / "db"

PASS = "PASS"
FAIL = "FAIL"
results = []


def _resolve_db(db_arg: str | None) -> Path:
    """Resolve assertion DB path from --db arg or glob for latest."""
    if db_arg:
        return Path(db_arg)
    candidates = sorted(
        [p for p in glob.glob(str(DST_DIR / "trilobita-*.db"))
         if "canonical" not in p and "assertion" not in p],
        key=lambda p: Path(p).stat().st_mtime,
    )
    if candidates:
        return Path(candidates[-1])
    # Fallback to unversioned name (legacy)
    return DST_DIR / "trilobita.db"


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
        help="Path to trilobita DB (default: latest db/trilobita-*.db)")
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
    check("taxon count", n_taxon >= 5341, f"{n_taxon} (expected >= 5341)")

    n_ref = dst.execute("SELECT COUNT(*) FROM reference").fetchone()[0]
    check("reference count", n_ref >= 2132, f"{n_ref} (expected >= 2132)")

    n_default_edges = dst.execute(
        "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id=1"
    ).fetchone()[0]
    check("default profile edges", n_default_edges > 5000,
          f"{n_default_edges} (expected ~5,113)")

    n_synonym = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='SYNONYM_OF'"
    ).fetchone()[0]
    check("SYNONYM_OF count", n_synonym >= 1055, f"{n_synonym} (expected >= 1055)")

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
    check("classification_profile count", n_profiles >= 2, f"{n_profiles}")

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

    # Get assertion-derived parent_id mapping (from default profile edge_cache)
    derived = dict(dst.execute(
        "SELECT id, parent_id FROM v_taxonomic_ranks"
    ).fetchall())

    mismatches = []
    for taxon_id, orig_parent in orig.items():
        derived_parent = derived.get(taxon_id)
        if orig_parent != derived_parent:
            mismatches.append((taxon_id, orig_parent, derived_parent))

    n_orig = len(orig)
    n_match = n_orig - len(mismatches)
    pct = n_match / n_orig * 100 if n_orig else 0
    # Allow up to 5% mismatches (0.2.0 has corrected family names, additional placements)
    check("tree equivalence", pct >= 95.0,
          f"{n_match}/{n_orig} match ({pct:.1f}%), {len(mismatches)} differ")

    if mismatches and len(mismatches) <= 10:
        for tid, op, dp in mismatches:
            name = dst.execute(
                "SELECT name FROM taxon WHERE id=?", (tid,)
            ).fetchone()[0]
            print(f"      taxon {tid} ({name}): orig={op}, derived={dp}")

    # --- 3. Profile checks ---
    print("\n3. Profile checks")

    # Count reachable taxa via v_taxonomy_tree (edge_cache based, should be fast)
    n_reachable = dst.execute(
        "SELECT COUNT(*) FROM v_taxonomy_tree"
    ).fetchone()[0]
    check("tree reachable taxa", n_reachable > 4800,
          f"{n_reachable} reachable via default profile tree")

    # Check all valid genera in default profile
    valid_genera_total = dst.execute(
        "SELECT COUNT(*) FROM taxon WHERE rank='Genus' AND is_valid=1"
    ).fetchone()[0]
    # Count valid genera without default profile placement
    valid_genera_no_placement = dst.execute("""
        SELECT COUNT(*) FROM taxon t
        WHERE t.rank = 'Genus' AND t.is_valid = 1
          AND NOT EXISTS (
              SELECT 1 FROM classification_edge_cache e
              WHERE e.child_id = t.id AND e.profile_id = 1
          )
    """).fetchone()[0]
    valid_genera_in_profile = dst.execute("""
        SELECT COUNT(*) FROM classification_edge_cache e
        JOIN taxon t ON e.child_id = t.id
        WHERE e.profile_id = 1 AND t.rank = 'Genus' AND t.is_valid = 1
    """).fetchone()[0]
    unplaced_pct = valid_genera_no_placement / valid_genera_total * 100 if valid_genera_total else 0
    placed_pct = valid_genera_in_profile / valid_genera_total * 100 if valid_genera_total else 0
    check("valid genera in default profile",
          placed_pct >= 95.0,
          f"{valid_genera_in_profile}/{valid_genera_total} ({placed_pct:.1f}%) in profile, "
          f"{valid_genera_no_placement} without placement ({unplaced_pct:.1f}%)")

    # Check orders reachable per profile
    profiles = dst.execute(
        "SELECT id, name FROM classification_profile ORDER BY id"
    ).fetchall()
    for pid, pname in profiles:
        n_orders_in_profile = dst.execute("""
            SELECT COUNT(DISTINCT e.child_id) FROM classification_edge_cache e
            JOIN taxon t ON e.child_id = t.id
            WHERE e.profile_id = ? AND t.rank = 'Order'
        """, (pid,)).fetchone()[0]
        check(f"orders in profile '{pname}'", n_orders_in_profile > 0,
              f"{n_orders_in_profile} orders")

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
               r.authors
        FROM assertion a
        LEFT JOIN taxon t2 ON a.object_taxon_id = t2.id
        LEFT JOIN reference r ON a.reference_id = r.id
        WHERE a.subject_taxon_id = (SELECT id FROM taxon WHERE name='Asaphidae')
        ORDER BY a.predicate
    """).fetchall()
    if example:
        print(f"   Asaphidae assertions ({len(example)}):")
        for pred, status, obj, auth in example:
            print(f"     {pred} → {obj} [{status}] ref={auth}")

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
