#!/usr/bin/env python3
"""P78 — Treatise (2004) import validator.

Validates that the Treatise data was correctly imported into the assertion DB.

Run AFTER import_treatise.py:
    python scripts/validate_treatise_import.py
"""

import json
import sqlite3
import sys
from pathlib import Path

from db_path import find_assertion_db

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CH4_JSON = DATA_DIR / "treatise_ch4_taxonomy.json"
CH5_JSON = DATA_DIR / "treatise_ch5_taxonomy.json"

PASS = "PASS"
FAIL = "FAIL"
results = []


def check(name: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    results.append((name, status, detail))
    mark = "\u2713" if passed else "\u2717"
    msg = f"  [{mark}] {name}"
    if detail:
        msg += f" \u2014 {detail}"
    print(msg)


def _count_json_nodes(node: dict, rank: str) -> int:
    """Count nodes of a given rank in a JSON tree (recursive)."""
    count = 1 if node.get("rank", "").lower() == rank else 0
    for child in node.get("children", []):
        count += _count_json_nodes(child, rank)
    return count


def _collect_json_genera(node: dict, result: list = None) -> list:
    """Collect all genus names from JSON tree."""
    if result is None:
        result = []
    rank = node.get("rank", "").lower()
    if rank == "genus":
        result.append(node["name"])
    for child in node.get("children", []):
        _collect_json_genera(child, result)
    return result


def main():
    db_path = Path(find_assertion_db())
    if not db_path.exists():
        print(f"ERROR: Assertion DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    print(f"=== P78: Treatise Import Validation ===\n")
    print(f"  DB: {db_path}")

    # Load JSON for cross-checking
    with open(CH4_JSON) as f:
        ch4 = json.load(f)
    with open(CH5_JSON) as f:
        ch5 = json.load(f)

    # --- 1. Treatise references ---
    print("\n1. Treatise references")

    refs = conn.execute("""
        SELECT id, authors FROM reference
        WHERE reference_type = 'incollection' AND year = 2004
          AND (authors LIKE '%SHERGOLD%' OR authors LIKE '%REPINA%')
    """).fetchall()
    check("Treatise references exist", len(refs) == 2,
          f"{len(refs)} found (expected 2)")

    ref_ids = [r[0] for r in refs]

    # --- 2. New taxon counts ---
    print("\n2. New taxon counts")

    # Subfamily count
    n_subfamily = conn.execute(
        "SELECT COUNT(*) FROM taxon WHERE rank = 'Subfamily'"
    ).fetchone()[0]
    check("Subfamily taxa created", n_subfamily >= 30,
          f"{n_subfamily} (expected ~35)")

    # Superfamily new taxa
    n_superfamily = conn.execute(
        "SELECT COUNT(*) FROM taxon WHERE rank = 'Superfamily'"
    ).fetchone()[0]
    check("Superfamily taxa", n_superfamily >= 8,
          f"{n_superfamily}")

    # New families
    new_families = conn.execute("""
        SELECT name FROM taxon WHERE rank = 'Family'
        AND name IN ('SPINAGNOSTIDAE', 'PHALACROMIDAE', 'SPHAERAGNOSTIDAE', 'Menneraspidae')
    """).fetchall()
    check("New families (4 expected)", len(new_families) == 4,
          f"{len(new_families)}: {[r[0] for r in new_families]}")

    # 3 new genera
    new_genera = conn.execute("""
        SELECT name FROM taxon WHERE rank = 'Genus'
        AND name IN ('Iofgia', 'Macannaia', 'Pseudopaokannia')
    """).fetchall()
    check("New genera (3 expected)", len(new_genera) == 3,
          f"{len(new_genera)}: {[r[0] for r in new_genera]}")

    # Placeholder taxa
    n_placeholder = conn.execute(
        "SELECT COUNT(*) FROM taxon WHERE is_placeholder = 1"
    ).fetchone()[0]
    check("Placeholder taxa exist", n_placeholder >= 2,
          f"{n_placeholder}")

    # --- 3. Treatise assertions ---
    print("\n3. Treatise PLACED_IN assertions")

    if ref_ids:
        placeholders = ",".join("?" * len(ref_ids))
        n_treatise_assertions = conn.execute(f"""
            SELECT COUNT(*) FROM assertion
            WHERE predicate = 'PLACED_IN' AND reference_id IN ({placeholders})
        """, ref_ids).fetchone()[0]
    else:
        n_treatise_assertions = 0

    check("Treatise PLACED_IN assertions", n_treatise_assertions >= 400,
          f"{n_treatise_assertions} (expected ~421)")

    # All Treatise assertions should be is_accepted = 0
    if ref_ids:
        n_accepted = conn.execute(f"""
            SELECT COUNT(*) FROM assertion
            WHERE predicate = 'PLACED_IN' AND reference_id IN ({placeholders})
            AND is_accepted = 1
        """, ref_ids).fetchone()[0]
    else:
        n_accepted = 0
    check("Treatise assertions not accepted (is_accepted=0)",
          n_accepted == 0, f"{n_accepted} accepted (should be 0)")

    # --- 4. treatise2004 profile ---
    print("\n4. Classification profile")

    profile = conn.execute(
        "SELECT id, name FROM classification_profile WHERE name = 'treatise2004'"
    ).fetchone()
    check("treatise2004 profile exists", profile is not None,
          f"id={profile[0]}" if profile else "NOT FOUND")

    if profile:
        profile_id = profile[0]

        # Edge count
        n_edges = conn.execute(
            "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = ?",
            (profile_id,)
        ).fetchone()[0]
        default_edges = conn.execute(
            "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = 1"
        ).fetchone()[0]
        check("Edge cache populated", n_edges > default_edges,
              f"{n_edges} (default: {default_edges})")

        # Genera coverage — all default genera should be in treatise profile
        default_genera = set(r[0] for r in conn.execute("""
            SELECT ec.child_id FROM classification_edge_cache ec
            JOIN taxon t ON ec.child_id = t.id
            WHERE ec.profile_id = 1 AND t.rank = 'Genus'
        """).fetchall())
        treatise_genera = set(r[0] for r in conn.execute("""
            SELECT ec.child_id FROM classification_edge_cache ec
            JOIN taxon t ON ec.child_id = t.id
            WHERE ec.profile_id = ? AND t.rank = 'Genus'
        """, (profile_id,)).fetchall())
        missing = default_genera - treatise_genera
        check("All default genera preserved in treatise profile",
              len(missing) == 0,
              f"{len(missing)} missing" if missing else "all preserved")

    # --- 5. Agnostida → Trilobita connection ---
    print("\n5. Key structural checks")

    if profile:
        # Agnostida → Trilobita
        agnostida_parent = conn.execute("""
            SELECT parent_id FROM classification_edge_cache
            WHERE profile_id = ? AND child_id = 5341
        """, (profile_id,)).fetchone()
        check("Agnostida \u2192 Trilobita",
              agnostida_parent and agnostida_parent[0] == 1,
              f"parent_id={agnostida_parent[0] if agnostida_parent else 'NONE'}")

        # Eodiscida → Agnostida
        eodiscida_parent = conn.execute("""
            SELECT parent_id FROM classification_edge_cache
            WHERE profile_id = ? AND child_id = 2
        """, (profile_id,)).fetchone()
        check("Eodiscida \u2192 Agnostida",
              eodiscida_parent and eodiscida_parent[0] == 5341,
              f"parent_id={eodiscida_parent[0] if eodiscida_parent else 'NONE'}")

    # --- 6. JSON completeness (subgenus excluded) ---
    print("\n6. JSON completeness (subgenus excluded)")

    json_genera_ch4 = _collect_json_genera(ch4["taxonomy"])
    json_genera_ch5 = _collect_json_genera(ch5["taxonomy"])
    all_json_genera = set(json_genera_ch4 + json_genera_ch5)

    # Check all JSON genera exist as taxon
    missing_genera = []
    for name in all_json_genera:
        r = conn.execute(
            "SELECT id FROM taxon WHERE LOWER(name) = LOWER(?)", (name,)
        ).fetchone()
        if not r:
            missing_genera.append(name)

    check("All JSON genera exist in taxon table",
          len(missing_genera) == 0,
          f"{len(missing_genera)} missing: {missing_genera}" if missing_genera
          else f"all {len(all_json_genera)} found")

    # Check all JSON genera have a Treatise PLACED_IN assertion
    if ref_ids:
        genera_with_assertion = set()
        for name in all_json_genera:
            tid = conn.execute(
                "SELECT id FROM taxon WHERE LOWER(name) = LOWER(?)", (name,)
            ).fetchone()
            if tid:
                has = conn.execute(f"""
                    SELECT 1 FROM assertion
                    WHERE subject_taxon_id = ?
                      AND predicate = 'PLACED_IN'
                      AND reference_id IN ({placeholders})
                """, [tid[0]] + ref_ids).fetchone()
                if has:
                    genera_with_assertion.add(name)

        n_with = len(genera_with_assertion)
        n_without = len(all_json_genera) - n_with
        check("JSON genera have Treatise assertions",
              n_without == 0,
              f"{n_with}/{len(all_json_genera)} have assertions"
              + (f", missing: {all_json_genera - genera_with_assertion}"
                 if n_without else ""))

    # --- 7. assertion_status distribution ---
    print("\n7. Assertion status distribution")

    if ref_ids:
        for status in ["asserted", "questionable", "incertae_sedis", "indet"]:
            n = conn.execute(f"""
                SELECT COUNT(*) FROM assertion
                WHERE predicate = 'PLACED_IN'
                  AND reference_id IN ({placeholders})
                  AND assertion_status = ?
            """, ref_ids + [status]).fetchone()[0]
            print(f"   {status}: {n}")

    # --- 8. Provenance ---
    print("\n8. Provenance")

    n_prov = conn.execute("SELECT COUNT(*) FROM provenance").fetchone()[0]
    check("Provenance updated", n_prov >= 4,
          f"{n_prov} records (expected >= 4)")

    # --- 9. Profile count ---
    print("\n9. Profiles")

    n_profiles = conn.execute(
        "SELECT COUNT(*) FROM classification_profile"
    ).fetchone()[0]
    check("3 profiles exist", n_profiles == 3,
          f"{n_profiles}")

    # --- Summary ---
    print(f"\n=== Results ===")
    passed = sum(1 for _, s, _ in results if s == PASS)
    total = len(results)
    print(f"  {passed}/{total} checks passed")

    if passed < total:
        print("\n  Failed checks:")
        for name, status, detail in results:
            if status == FAIL:
                print(f"    \u2717 {name}: {detail}")
        sys.exit(1)
    else:
        print("  All checks passed!")

    conn.close()


if __name__ == "__main__":
    main()
