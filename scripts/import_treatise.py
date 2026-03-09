#!/usr/bin/env python3
"""P78 — Treatise (2004) taxonomy import into assertion DB.

Reads treatise_ch4_taxonomy.json (Agnostida) and treatise_ch5_taxonomy.json
(Redlichiida), then adds Treatise 2004 classification as a third opinion
source to the existing assertion-centric DB.

Run AFTER create_assertion_db.py:
    python scripts/create_assertion_db.py
    python scripts/import_treatise.py
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

# Well-known taxon IDs
TRILOBITA_ID = 1
EODISCIDA_ID = 2
EODISCINA_ID = 5353
AGNOSTIDA_ID = 5341


# ---------------------------------------------------------------------------
# Reference insertion
# ---------------------------------------------------------------------------

def insert_references(cur: sqlite3.Cursor) -> dict:
    """Insert Treatise ch4 and ch5 references. Returns {chapter: ref_id}."""
    # Read JSON source metadata
    with open(CH4_JSON) as f:
        ch4_meta = json.load(f)
    with open(CH5_JSON) as f:
        ch5_meta = json.load(f)

    refs = {}

    # Ch4: Agnostida — Shergold, Laurie, & Sun (2004)
    cur.execute("""
        INSERT INTO reference (authors, year, title, journal, volume, pages,
                               editors, book_title, reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "SHERGOLD, J.H., LAURIE, J.R., & SUN, X.",
        2004,
        "Classification and review of the trilobite order Agnostida Salter, 1864: "
        "an Australian perspective",
        None, None,
        ch4_meta.get("pages", "331-403"),
        "Kaesler, R.L.",
        "Treatise on Invertebrate Paleontology, Part O, Arthropoda 1, "
        "Trilobita (Revised), Volume 1",
        "incollection",
        f"{ch4_meta['source']}, p. {ch4_meta.get('pages', '331-403')}",
    ))
    refs["ch4"] = cur.lastrowid

    # Ch5: Redlichiida — Palmer & Repina (2004)
    cur.execute("""
        INSERT INTO reference (authors, year, title, journal, volume, pages,
                               editors, book_title, reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "PALMER, A.R. & REPINA, L.N.",
        2004,
        "Introduction to subclass Librostoma",
        None, None,
        ch5_meta.get("pages", "404-481"),
        "Kaesler, R.L.",
        "Treatise on Invertebrate Paleontology, Part O, Arthropoda 1, "
        "Trilobita (Revised), Volume 1",
        "incollection",
        f"{ch5_meta['source']}, p. {ch5_meta.get('pages', '404-481')}",
    ))
    refs["ch5"] = cur.lastrowid

    return refs


# ---------------------------------------------------------------------------
# Taxon matching / creation
# ---------------------------------------------------------------------------

def _build_name_index(cur: sqlite3.Cursor) -> dict:
    """Build {lower(name)+rank: id} index from existing taxa."""
    rows = cur.execute("SELECT id, name, rank FROM taxon").fetchall()
    idx = {}
    for tid, name, rank in rows:
        key = f"{name.lower()}|{rank.lower()}"
        idx[key] = tid
    return idx


def _next_taxon_id(cur: sqlite3.Cursor) -> int:
    return cur.execute("SELECT MAX(id) FROM taxon").fetchone()[0] + 1


def _create_taxon(cur: sqlite3.Cursor, next_id: int, name: str, rank: str,
                  author: str = None, year=None, is_placeholder: int = 0,
                  notes: str = None) -> int:
    """Insert a new taxon and return its id."""
    cur.execute("""
        INSERT INTO taxon (id, name, rank, author, year, is_placeholder, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (next_id, name, rank, author, str(year) if year else None,
          is_placeholder, notes))
    return next_id


# ---------------------------------------------------------------------------
# Tree traversal and assertion generation
# ---------------------------------------------------------------------------

class TreatiseImporter:
    def __init__(self, cur: sqlite3.Cursor, ref_id: int, chapter: str):
        self.cur = cur
        self.ref_id = ref_id
        self.chapter = chapter
        self.name_idx = _build_name_index(cur)
        self.next_id = _next_taxon_id(cur)
        self.stats = {
            "matched": 0,
            "created": 0,
            "assertions": 0,
            "skipped_subgenus": 0,
        }
        self.created_taxa = []

    def _match_or_create(self, node: dict) -> int | None:
        """Match existing taxon or create new one. Returns taxon_id or None for skipped."""
        rank = node["rank"].lower()
        name = node["name"]

        # Skip subgenus
        if rank == "subgenus":
            self.stats["skipped_subgenus"] += 1
            return None

        # Handle "unrecognizable" container → treat as Family
        if rank == "unrecognizable":
            tid = self._create_new(name, "Family", node, is_placeholder=1)
            return tid

        # Handle uncertain/UNCERTAIN containers
        if name.lower() == "uncertain":
            db_rank = rank.capitalize()  # e.g. 'subfamily' → 'Subfamily'
            # Get note for context
            note = node.get("note", f"Treatise (2004) {db_rank} uncertain")
            placeholder_name = "Uncertain"
            tid = self._create_new(placeholder_name, db_rank, {},
                                   is_placeholder=1, notes=note)
            return tid

        # Normalize rank for lookup
        db_rank = rank.capitalize()
        if db_rank == "Superfamily":
            db_rank = "Superfamily"

        # Special case: Eodiscina suborder → use existing Eodiscina taxon
        if name.lower() == "eodiscina" and rank == "suborder":
            self.stats["matched"] += 1
            return EODISCINA_ID

        # Try matching by name + rank
        key = f"{name.lower()}|{db_rank.lower()}"
        if key in self.name_idx:
            self.stats["matched"] += 1
            return self.name_idx[key]

        # Try case-insensitive match
        key_lower = f"{name.lower()}|{db_rank.lower()}"
        if key_lower in self.name_idx:
            self.stats["matched"] += 1
            return self.name_idx[key_lower]

        # New taxon needed
        tid = self._create_new(name, db_rank, node)
        return tid

    def _create_new(self, name: str, rank: str, node: dict,
                    is_placeholder: int = 0, notes: str = None) -> int:
        tid = _create_taxon(
            self.cur, self.next_id, name, rank,
            author=node.get("author"),
            year=node.get("year"),
            is_placeholder=is_placeholder,
            notes=notes,
        )
        self.name_idx[f"{name.lower()}|{rank.lower()}"] = tid
        self.next_id += 1
        self.stats["created"] += 1
        self.created_taxa.append((tid, name, rank))
        return tid

    def _insert_assertion(self, child_id: int, parent_id: int,
                          status: str = "asserted",
                          notes: str = None) -> None:
        self.cur.execute("""
            INSERT INTO assertion (subject_taxon_id, predicate, object_taxon_id,
                                   reference_id, assertion_status,
                                   curation_confidence, is_accepted, notes)
            VALUES (?, 'PLACED_IN', ?, ?, ?, 'high', 0, ?)
        """, (child_id, parent_id, self.ref_id, status, notes))
        self.stats["assertions"] += 1

    def process_tree(self, node: dict, parent_id: int | None = None) -> None:
        """Recursively process a taxonomy tree node."""
        tid = self._match_or_create(node)
        if tid is None:
            return  # skipped (subgenus)

        # Create PLACED_IN assertion if parent given
        if parent_id is not None:
            # Determine assertion_status
            is_uncertain_container = (
                node.get("name", "").lower() == "uncertain"
            )
            is_in_uncertain_parent = False  # handled below per-child
            is_genus_uncertain = node.get("uncertain", False)

            if is_uncertain_container:
                status = "incertae_sedis"
            elif is_genus_uncertain:
                status = "questionable"
            else:
                status = "asserted"

            notes = None

            self._insert_assertion(tid, parent_id, status=status, notes=notes)

        # Process children
        children = node.get("children", [])
        is_uncertain_node = (node.get("name", "").lower() == "uncertain")
        is_unrecognizable_node = (node.get("rank", "").lower() == "unrecognizable")

        for child in children:
            child_rank = child.get("rank", "").lower()
            if child_rank == "subgenus":
                self.stats["skipped_subgenus"] += 1
                continue

            # Delegate unrecognizable containers
            if child_rank == "unrecognizable":
                self.process_unrecognizable(child, tid)
                continue

            child_tid = self._match_or_create(child)
            if child_tid is None:
                continue

            # Determine status for this child
            if is_uncertain_node:
                child_status = "incertae_sedis"
            elif is_unrecognizable_node:
                child_status = "indet"
            elif child.get("uncertain", False):
                child_status = "questionable"
            else:
                child_status = "asserted"

            self._insert_assertion(child_tid, tid, status=child_status)

            # Recurse into child's children (skip the child itself, already processed)
            for grandchild in child.get("children", []):
                self.process_tree(grandchild, parent_id=child_tid)

    def process_unrecognizable(self, node: dict, parent_id: int) -> None:
        """Process unrecognizable container and its genera."""
        tid = self._match_or_create(node)
        if tid is None:
            return

        # Container PLACED_IN parent
        self._insert_assertion(tid, parent_id, status="asserted",
                               notes="Unrecognizable genera container")

        for child in node.get("children", []):
            child_rank = child.get("rank", "").lower()
            if child_rank == "subgenus":
                self.stats["skipped_subgenus"] += 1
                continue

            child_tid = self._match_or_create(child)
            if child_tid is None:
                continue

            self._insert_assertion(child_tid, tid, status="indet")


# ---------------------------------------------------------------------------
# Edge cache for treatise2004 profile
# ---------------------------------------------------------------------------

def build_treatise_profile(cur: sqlite3.Cursor) -> dict:
    """Create treatise2004 profile and build its edge cache.

    Algorithm: hybrid approach — start with treatise1959 edges (if available,
    otherwise default), then replace only the taxa that the Treatise 2004
    explicitly places.  Taxa not mentioned in the Treatise 2004 keep their
    base profile placement.

    1. Copy base profile edges (treatise1959 if available, else default)
    2. Collect the set of taxa that have Treatise PLACED_IN assertions
    3. For those taxa only, remove their base edge and use the Treatise edge
    4. Add edges for new taxa (subfamilies etc.) that have no base edge
    5. Ensure Agnostida → Trilobita edge
    """
    # 1. Insert profile
    # Determine base profile: treatise1959 if exists, else default (id=1)
    base_row = cur.execute(
        "SELECT id FROM classification_profile WHERE name = 'treatise1959'"
    ).fetchone()
    base_profile_id = base_row[0] if base_row else 1
    base_name = "treatise1959" if base_row else "default"

    cur.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "treatise2004",
        f"Treatise (2004) for Agnostida/Redlichiida, {base_name} for other orders",
        json.dumps({
            "description": "hybrid",
            "builder": "import_treatise.py",
            "base_profile": base_name,
            "scope": ["Agnostida", "Redlichiida", "Eodiscida"],
        }),
    ))
    profile_id = cur.lastrowid

    # 2. Copy all base profile edges
    cur.execute("""
        INSERT INTO classification_edge_cache (profile_id, child_id, parent_id)
        SELECT ?, child_id, parent_id
        FROM classification_edge_cache
        WHERE profile_id = ?
    """, (profile_id, base_profile_id))
    n_copied = cur.execute("SELECT changes()").fetchone()[0]

    # 3. Find Treatise reference IDs
    treatise_ref_ids = [r[0] for r in cur.execute(
        "SELECT id FROM reference WHERE reference_type = 'incollection' AND year = 2004"
        " AND (authors LIKE '%SHERGOLD%' OR authors LIKE '%REPINA%')"
    ).fetchall()]

    if not treatise_ref_ids:
        total_edges = cur.execute(
            "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = ?",
            (profile_id,)
        ).fetchone()[0]
        return {"profile_id": profile_id, "copied": n_copied,
                "replaced": 0, "added": 0, "total_edges": total_edges}

    # 4. Get all Treatise PLACED_IN assertions (subject → object)
    placeholders = ",".join("?" * len(treatise_ref_ids))
    treatise_edges = cur.execute(f"""
        SELECT subject_taxon_id, object_taxon_id
        FROM assertion
        WHERE predicate = 'PLACED_IN'
          AND reference_id IN ({placeholders})
          AND object_taxon_id IS NOT NULL
    """, treatise_ref_ids).fetchall()

    # 5. For each Treatise subject, replace its edge in the profile
    n_replaced = 0
    n_added = 0
    for child_id, parent_id in treatise_edges:
        # Check if this child already has an edge in the profile
        existing = cur.execute("""
            SELECT parent_id FROM classification_edge_cache
            WHERE profile_id = ? AND child_id = ?
        """, (profile_id, child_id)).fetchone()

        if existing:
            # Replace with Treatise placement
            cur.execute("""
                UPDATE classification_edge_cache
                SET parent_id = ?
                WHERE profile_id = ? AND child_id = ?
            """, (parent_id, profile_id, child_id))
            n_replaced += 1
        else:
            # New taxon (e.g. Subfamily) — insert
            cur.execute("""
                INSERT INTO classification_edge_cache (profile_id, child_id, parent_id)
                VALUES (?, ?, ?)
            """, (profile_id, child_id, parent_id))
            n_added += 1

    # 6. Remove Eodiscida: move its children under Eodiscina
    eodiscida_children = cur.execute("""
        SELECT child_id FROM classification_edge_cache
        WHERE profile_id = ? AND parent_id = ?
    """, (profile_id, EODISCIDA_ID)).fetchall()
    for (child_id,) in eodiscida_children:
        cur.execute("""
            UPDATE classification_edge_cache
            SET parent_id = ?
            WHERE profile_id = ? AND child_id = ?
        """, (EODISCINA_ID, profile_id, child_id))
    cur.execute("""
        DELETE FROM classification_edge_cache
        WHERE profile_id = ? AND child_id = ?
    """, (profile_id, EODISCIDA_ID))

    # 7. Ensure Agnostida → Trilobita edge
    existing = cur.execute("""
        SELECT parent_id FROM classification_edge_cache
        WHERE profile_id = ? AND child_id = ?
    """, (profile_id, AGNOSTIDA_ID)).fetchone()
    if existing:
        if existing[0] != TRILOBITA_ID:
            cur.execute("""
                UPDATE classification_edge_cache
                SET parent_id = ?
                WHERE profile_id = ? AND child_id = ?
            """, (TRILOBITA_ID, profile_id, AGNOSTIDA_ID))
    else:
        cur.execute("""
            INSERT INTO classification_edge_cache (profile_id, child_id, parent_id)
            VALUES (?, ?, ?)
        """, (profile_id, AGNOSTIDA_ID, TRILOBITA_ID))

    total_edges = cur.execute(
        "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = ?",
        (profile_id,)
    ).fetchone()[0]

    return {
        "profile_id": profile_id,
        "base_profile": base_name,
        "copied": n_copied,
        "replaced": n_replaced,
        "added": n_added,
        "total_edges": total_edges,
    }


# ---------------------------------------------------------------------------
# Provenance & metadata
# ---------------------------------------------------------------------------

def update_provenance_and_metadata(cur: sqlite3.Cursor) -> None:
    """Add Treatise 2004 to provenance and schema_descriptions."""
    # Provenance
    max_prov = cur.execute("SELECT MAX(id) FROM provenance").fetchone()[0] or 0
    cur.execute("""
        INSERT INTO provenance (id, source_type, citation, description, year, url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        max_prov + 1,
        "supplementary",
        "Kaesler, R.L. (Ed.), 2004, Treatise on Invertebrate Paleontology, "
        "Part O, Arthropoda 1, Trilobita (Revised), Volume 1: "
        "Geological Society of America / University of Kansas.",
        "Agnostida (Ch.4) and Redlichiida (Ch.5) classification — "
        "alternative opinion to Adrain 2011",
        2004, None,
    ))

    # schema_descriptions for new elements
    new_descs = [
        ("taxon", "rank",
         "Taxonomic rank: Class, Order, Suborder, Superfamily, Family, "
         "Subfamily, Genus (Subfamily added P78 for Treatise 2004)"),
        ("classification_profile", "name",
         "Profile names: default, ja2002_strict, treatise2004"),
    ]
    for table, col, desc in new_descs:
        # Update if exists, insert if not
        existing = cur.execute(
            "SELECT rowid FROM schema_descriptions WHERE table_name=? AND column_name=?",
            (table, col)
        ).fetchone()
        if existing:
            cur.execute(
                "UPDATE schema_descriptions SET description=? WHERE table_name=? AND column_name=?",
                (desc, table, col))
        else:
            cur.execute(
                "INSERT INTO schema_descriptions (table_name, column_name, description) VALUES (?,?,?)",
                (table, col, desc))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    db_path = Path(find_assertion_db())
    if not db_path.exists():
        print(f"ERROR: Assertion DB not found: {db_path}", file=sys.stderr)
        print("Run create_assertion_db.py first.", file=sys.stderr)
        sys.exit(1)

    for json_path in [CH4_JSON, CH5_JSON]:
        if not json_path.exists():
            print(f"ERROR: JSON not found: {json_path}", file=sys.stderr)
            sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    cur = conn.cursor()

    print(f"=== P78: Treatise (2004) Import ===\n")
    print(f"  DB: {db_path}")

    # 1. Insert references
    print("\n1. Inserting Treatise references...")
    refs = insert_references(cur)
    conn.commit()
    print(f"   Ch4 ref id: {refs['ch4']}")
    print(f"   Ch5 ref id: {refs['ch5']}")

    # 2. Load JSON
    print("\n2. Loading taxonomy JSON...")
    with open(CH4_JSON) as f:
        ch4 = json.load(f)
    with open(CH5_JSON) as f:
        ch5 = json.load(f)

    # 3. Process Ch4 (Agnostida)
    print("\n3. Processing Chapter 4 (Agnostida)...")
    imp4 = TreatiseImporter(cur, refs["ch4"], "ch4")

    # Agnostida PLACED_IN Trilobita (Treatise opinion)
    imp4._insert_assertion(
        AGNOSTIDA_ID, TRILOBITA_ID,
        status="asserted",
        notes="Treatise (2004): Agnostida placed within Trilobita",
    )

    # Process the Agnostida tree — children of the root order
    root4 = ch4["taxonomy"]
    for child in root4.get("children", []):
        imp4.process_tree(child, parent_id=AGNOSTIDA_ID)

    conn.commit()
    print(f"   Matched: {imp4.stats['matched']}")
    print(f"   Created: {imp4.stats['created']}")
    print(f"   Assertions: {imp4.stats['assertions']}")
    print(f"   Skipped subgenera: {imp4.stats['skipped_subgenus']}")

    # 4. Process Ch5 (Redlichiida)
    print("\n4. Processing Chapter 5 (Redlichiida)...")
    imp5 = TreatiseImporter(cur, refs["ch5"], "ch5")

    # Process the Redlichiida tree — children of the root order
    root5 = ch5["taxonomy"]
    for child in root5.get("children", []):
        imp5.process_tree(child, parent_id=9)  # 9 = Redlichiida

    conn.commit()
    print(f"   Matched: {imp5.stats['matched']}")
    print(f"   Created: {imp5.stats['created']}")
    print(f"   Assertions: {imp5.stats['assertions']}")
    print(f"   Skipped subgenera: {imp5.stats['skipped_subgenus']}")

    # 5. Classification profile + edge cache
    print("\n5. Building treatise2004 classification profile...")
    profile_stats = build_treatise_profile(cur)
    conn.commit()
    print(f"   Profile ID: {profile_stats['profile_id']}")
    print(f"   Base profile: {profile_stats['base_profile']}")
    print(f"   Copied from base: {profile_stats['copied']}")
    print(f"   Replaced edges: {profile_stats['replaced']}")
    print(f"   Added new edges: {profile_stats['added']}")
    print(f"   Total edges: {profile_stats['total_edges']}")

    # 6. Provenance & metadata
    print("\n6. Updating provenance and metadata...")
    update_provenance_and_metadata(cur)
    conn.commit()
    print("   Done.")

    # Summary
    total_created = imp4.stats["created"] + imp5.stats["created"]
    total_assertions = imp4.stats["assertions"] + imp5.stats["assertions"]
    total_matched = imp4.stats["matched"] + imp5.stats["matched"]

    print(f"\n=== Summary ===")
    print(f"  References added:  2")
    print(f"  Taxa matched:      {total_matched}")
    print(f"  Taxa created:      {total_created}")
    print(f"  Assertions added:  {total_assertions}")
    print(f"  Profile edges:     {profile_stats['total_edges']}")

    if imp4.created_taxa or imp5.created_taxa:
        print(f"\n  New taxa:")
        for tid, name, rank in imp4.created_taxa + imp5.created_taxa:
            print(f"    [{rank}] {name} (id={tid})")

    conn.close()
    print(f"\nDone. DB: {db_path}")


if __name__ == "__main__":
    main()
