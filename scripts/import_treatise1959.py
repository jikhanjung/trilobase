#!/usr/bin/env python3
"""Import Treatise (1959) taxonomy into assertion DB.

Reads data/treatise_1959_taxonomy.json, cleans OCR genus names via fuzzy
matching against existing DB genera, then creates a 'treatise1959' profile
with full Order→Genus classification.

Rerunnable: deletes any existing treatise1959 profile data before importing.

Usage:
    python scripts/import_treatise1959.py
"""

import json
import sqlite3
import sys
import difflib
from collections import defaultdict
from pathlib import Path

from db_path import find_assertion_db

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TAXONOMY_JSON = DATA_DIR / "treatise_1959_taxonomy.json"

TRILOBITA_ID = 1

# Manual OCR corrections: garbled name → correct name (or None to skip)
MANUAL_FIXES = {
    "Mesamacida": None,       # noise (p.211)
    "Hoalicfiza": None,       # noise (p.218)
    "Subfamuly": None,        # "Subfamily" misread (p.235)
    "Ingieheidia": "Inglefieldia",  # OCR garble (p.260)
    "Urianae": None,          # subfamily suffix (p.267)
    "Aolcus": None,           # noise (p.295)
    "Gelemnurus": "Illaenurus",     # OCR garble (p.373)
    "Aeglinidue": None,       # family suffix (p.381)
    "Zoological": None,       # sentence fragment (p.387)
}


def clean_genera_names(genera_flat, db_genera_set):
    """Apply fuzzy matching to fix OCR-garbled genus names.

    Returns list of cleaned genera dicts with 'original_name' preserved
    when changed. Entries mapped to None in MANUAL_FIXES are removed.
    """
    cleaned = []
    stats = {"exact": 0, "fuzzy_fixed": 0, "manual_fixed": 0, "removed": 0, "new": 0}

    for g in genera_flat:
        name = g["name"]

        # Manual fix first
        if name in MANUAL_FIXES:
            fixed = MANUAL_FIXES[name]
            if fixed is None:
                stats["removed"] += 1
                continue
            g = dict(g)
            g["original_name"] = name
            g["name"] = fixed
            name = fixed
            stats["manual_fixed"] += 1

        # Exact match in DB
        if name in db_genera_set:
            cleaned.append(g)
            stats["exact"] += 1
            continue

        # Fuzzy match (≥85%)
        matches = difflib.get_close_matches(name, db_genera_set, n=1, cutoff=0.85)
        if matches:
            g = dict(g)
            g["original_name"] = name
            g["name"] = matches[0]
            cleaned.append(g)
            stats["fuzzy_fixed"] += 1
            continue

        # No match — keep as-is (new taxon not in DB)
        cleaned.append(g)
        stats["new"] += 1

    return cleaned, stats


def delete_existing_profile(cur, conn):
    """Remove any existing treatise1959 profile and its data."""
    row = cur.execute(
        "SELECT id FROM classification_profile WHERE name = 'treatise1959'"
    ).fetchone()
    if row is None:
        return False

    profile_id = row[0]
    print(f"  Removing existing treatise1959 profile (id={profile_id})...")

    # Delete edge cache
    cur.execute(
        "DELETE FROM classification_edge_cache WHERE profile_id = ?",
        (profile_id,)
    )
    edges_deleted = cur.execute("SELECT changes()").fetchone()[0]

    # Find reference for this profile
    # Find the reference we created (match by reference_type='book' and exact author)
    ref_rows = cur.execute(
        "SELECT id FROM reference WHERE authors = 'MOORE, R.C. (Ed.)' "
        "AND year = 1959 AND reference_type = 'book'"
    ).fetchall()

    assertions_deleted = 0
    for ref_row in ref_rows:
        ref_id = ref_row[0]
        # Delete assertions with this reference first (FK constraint)
        cur.execute(
            "DELETE FROM assertion WHERE reference_id = ?", (ref_id,)
        )
        assertions_deleted += cur.execute("SELECT changes()").fetchone()[0]

    # Now safe to delete references (no more FK references)
    for ref_row in ref_rows:
        cur.execute("DELETE FROM reference WHERE id = ?", (ref_row[0],))

    # Delete profile
    cur.execute(
        "DELETE FROM classification_profile WHERE id = ?", (profile_id,)
    )

    # Delete provenance entry
    cur.execute(
        "DELETE FROM provenance WHERE citation LIKE '%1959%Treatise%'"
    )

    conn.commit()
    print(f"    Edges deleted: {edges_deleted}")
    print(f"    Assertions deleted: {assertions_deleted}")
    return True


def insert_reference(cur):
    """Insert reference for Treatise 1959. Returns ref_id."""
    cur.execute("""
        INSERT INTO reference (authors, year, title, journal, volume, pages,
                               editors, book_title, reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "MOORE, R.C. (Ed.)",
        1959,
        "Treatise on Invertebrate Paleontology, Part O, Arthropoda 1",
        None, None,
        "O1-O560",
        "MOORE, R.C.",
        "Treatise on Invertebrate Paleontology, Part O, "
        "Arthropoda 1, Trilobitomorpha",
        "book",
        "Moore, R.C. (Ed.), 1959, Treatise on Invertebrate Paleontology, "
        "Part O, Arthropoda 1, Trilobitomorpha: Geological Society of America "
        "& University of Kansas Press, O1-O560.",
    ))
    return cur.lastrowid


def _build_name_index(cur):
    """Build {lower(name)|rank: id} index from existing taxa."""
    rows = cur.execute("SELECT id, name, rank FROM taxon").fetchall()
    idx = {}
    for tid, name, rank in rows:
        key = f"{name.lower()}|{rank.lower()}"
        idx[key] = tid
    return idx


def _next_taxon_id(cur):
    return cur.execute("SELECT MAX(id) FROM taxon").fetchone()[0] + 1


class Treatise1959Importer:
    def __init__(self, cur, ref_id):
        self.cur = cur
        self.ref_id = ref_id
        self.name_idx = _build_name_index(cur)
        self.next_id = _next_taxon_id(cur)
        self.stats = {
            "matched": 0,
            "created": 0,
            "assertions": 0,
            "skipped": 0,
            "dup_skipped": 0,
        }
        self.created_taxa = []
        self.asserted_children = set()  # track child_ids already given PLACED_IN

    def _match_or_create(self, name, rank, author=None, year=None,
                         is_placeholder=0, notes=None):
        """Match existing taxon or create new one. Returns taxon_id."""
        db_rank = rank.capitalize()
        if db_rank == "Superfamily":
            db_rank = "Superfamily"

        key = f"{name.lower()}|{db_rank.lower()}"
        if key in self.name_idx:
            self.stats["matched"] += 1
            return self.name_idx[key]

        # Create new taxon
        tid = self.next_id
        self.cur.execute("""
            INSERT INTO taxon (id, name, rank, author, year, is_placeholder, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tid, name, db_rank, author, str(year) if year else None,
              is_placeholder, notes))
        self.name_idx[key] = tid
        self.next_id += 1
        self.stats["created"] += 1
        self.created_taxa.append((tid, name, db_rank))
        return tid

    def _insert_assertion(self, child_id, parent_id, status="asserted",
                          notes=None):
        self.cur.execute("""
            INSERT INTO assertion (subject_taxon_id, predicate, object_taxon_id,
                                   reference_id, assertion_status,
                                   curation_confidence, is_accepted, notes)
            VALUES (?, 'PLACED_IN', ?, ?, ?, 'medium', 0, ?)
        """, (child_id, parent_id, self.ref_id, status, notes))
        self.stats["assertions"] += 1

    def process_tree(self, node, parent_id=None):
        """Recursively process taxonomy tree node."""
        rank = node.get("rank", "").lower()
        name = node.get("name", "")

        # Skip notes and empty nodes
        if rank == "note" or not name:
            return

        # Skip subgenus
        if rank == "subgenus":
            self.stats["skipped"] += 1
            return

        # Handle "Order Uncertain" etc.
        is_uncertain = "uncertain" in name.lower()

        # Match or create this taxon
        tid = self._match_or_create(
            name, rank,
            author=node.get("author"),
            year=node.get("year"),
            is_placeholder=1 if is_uncertain else 0,
        )

        # Create PLACED_IN assertion (skip if already asserted — dedup)
        if parent_id is not None:
            if tid in self.asserted_children:
                self.stats["dup_skipped"] += 1
            else:
                status = "incertae_sedis" if is_uncertain else "asserted"
                self._insert_assertion(tid, parent_id, status=status)
                self.asserted_children.add(tid)

        # Process children
        for child in node.get("children", []):
            self.process_tree(child, parent_id=tid)


def build_treatise1959_profile(cur, ref_id):
    """Create treatise1959 profile and build edge cache.

    Strategy: standalone — only include edges from 1959 Treatise assertions.
    No default edges are copied. The tree only contains taxa that the
    1959 Treatise explicitly places.
    """
    cur.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "treatise1959",
        "Treatise (1959) complete trilobite classification — "
        "all 7 orders + Order Uncertain",
        json.dumps({
            "description": "standalone",
            "builder": "import_treatise1959.py",
            "scope": "all_orders",
        }),
    ))
    profile_id = cur.lastrowid

    # Build edge cache from 1959 Treatise assertions only
    cur.execute("""
        INSERT INTO classification_edge_cache (profile_id, child_id, parent_id)
        SELECT ?, subject_taxon_id, object_taxon_id
        FROM assertion
        WHERE predicate = 'PLACED_IN'
          AND reference_id = ?
          AND object_taxon_id IS NOT NULL
    """, (profile_id, ref_id))
    n_edges = cur.execute("SELECT changes()").fetchone()[0]

    return {
        "profile_id": profile_id,
        "total_edges": n_edges,
    }


def update_provenance(cur):
    """Add Treatise 1959 provenance entry."""
    max_prov = cur.execute("SELECT MAX(id) FROM provenance").fetchone()[0] or 0
    cur.execute("""
        INSERT INTO provenance (id, source_type, citation, description, year, url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        max_prov + 1,
        "supplementary",
        "Moore, R.C. (Ed.), 1959, Treatise on Invertebrate Paleontology, "
        "Part O, Arthropoda 1, Trilobitomorpha: "
        "Geological Society of America / University of Kansas Press.",
        "Complete trilobite classification (all orders) — "
        "alternative historical opinion from 1959",
        1959, None,
    ))


def main():
    db_path = Path(find_assertion_db())
    if not db_path.exists():
        print(f"ERROR: Assertion DB not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if not TAXONOMY_JSON.exists():
        print(f"ERROR: Taxonomy JSON not found: {TAXONOMY_JSON}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    print(f"=== Treatise (1959) Import ===\n")
    print(f"  DB: {db_path}")
    print(f"  JSON: {TAXONOMY_JSON}")

    # 0. Remove existing profile if rerunning
    print("\n0. Checking for existing treatise1959 profile...")
    deleted = delete_existing_profile(cur, conn)
    if not deleted:
        print("  No existing profile found.")

    # 1. Load taxonomy JSON
    print("\n1. Loading taxonomy JSON...")
    with open(TAXONOMY_JSON) as f:
        taxonomy = json.load(f)
    genera_flat = taxonomy.get("genera_flat", [])
    print(f"   Genera in JSON: {len(genera_flat)}")

    # 2. Clean genus names via fuzzy matching
    print("\n2. Cleaning genus names (fuzzy match against DB)...")
    db_genera = set(
        r[0] for r in cur.execute(
            'SELECT name FROM taxon WHERE rank = "Genus"'
        ).fetchall()
    )
    cleaned_genera, clean_stats = clean_genera_names(genera_flat, db_genera)
    print(f"   Exact match:   {clean_stats['exact']}")
    print(f"   Fuzzy fixed:   {clean_stats['fuzzy_fixed']}")
    print(f"   Manual fixed:  {clean_stats['manual_fixed']}")
    print(f"   Removed noise: {clean_stats['removed']}")
    print(f"   New (no match): {clean_stats['new']}")
    print(f"   Total cleaned: {len(cleaned_genera)}")

    # Update genera in the taxonomy tree with cleaned names
    # Build a lookup: old_name -> new_name
    name_fixes = {}
    for g in cleaned_genera:
        if "original_name" in g:
            name_fixes[g["original_name"]] = g["name"]
    removed_names = {k for k, v in MANUAL_FIXES.items() if v is None}

    def fix_tree_genera(node):
        """Apply name fixes to genus nodes in tree."""
        if node.get("rank") == "genus":
            name = node["name"]
            if name in removed_names:
                return False  # mark for removal
            if name in name_fixes:
                node["name"] = name_fixes[name]
        children = node.get("children", [])
        node["children"] = [c for c in children if fix_tree_genera(c)]
        return True

    fix_tree_genera(taxonomy["taxonomy"])

    # 3. Insert reference
    print("\n3. Inserting reference...")
    ref_id = insert_reference(cur)
    conn.commit()
    print(f"   Reference id: {ref_id}")

    # 4. Process taxonomy tree
    print("\n4. Processing taxonomy tree...")
    imp = Treatise1959Importer(cur, ref_id)

    # Root is Class Trilobita — use existing Trilobita taxon
    root = taxonomy["taxonomy"]
    trilobita_id = TRILOBITA_ID

    # Process each order under Trilobita
    for order_node in root.get("children", []):
        imp.process_tree(order_node, parent_id=trilobita_id)

    conn.commit()
    print(f"   Matched: {imp.stats['matched']}")
    print(f"   Created: {imp.stats['created']}")
    print(f"   Assertions: {imp.stats['assertions']}")
    print(f"   Skipped: {imp.stats['skipped']}")
    if imp.stats['dup_skipped']:
        print(f"   Dup skipped: {imp.stats['dup_skipped']}")

    # 5. Build profile + edge cache
    print("\n5. Building treatise1959 classification profile...")
    profile_stats = build_treatise1959_profile(cur, ref_id)
    conn.commit()
    print(f"   Profile ID: {profile_stats['profile_id']}")
    print(f"   Total edges: {profile_stats['total_edges']} (standalone, no default copy)")

    # 6. Provenance
    print("\n6. Updating provenance...")
    update_provenance(cur)
    conn.commit()

    # Summary
    print(f"\n=== Summary ===")
    print(f"  Reference added:   id={ref_id}")
    print(f"  Taxa matched:      {imp.stats['matched']}")
    print(f"  Taxa created:      {imp.stats['created']}")
    print(f"  Assertions added:  {imp.stats['assertions']}")
    print(f"  Profile edges:     {profile_stats['total_edges']}")

    if imp.created_taxa:
        print(f"\n  New taxa (first 30):")
        for tid, name, rank in imp.created_taxa[:30]:
            print(f"    [{rank}] {name} (id={tid})")
        if len(imp.created_taxa) > 30:
            print(f"    ... and {len(imp.created_taxa) - 30} more")

    conn.close()
    print(f"\nDone. DB: {db_path}")


if __name__ == "__main__":
    main()
