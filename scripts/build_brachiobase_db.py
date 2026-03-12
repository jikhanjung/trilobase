#!/usr/bin/env python3
"""Build brachiobase DB from Treatise brachiopod source files.

Two classification profiles:
  Profile 1: Treatise 1965 (original) — vol1 + vol2
  Profile 2: Treatise Revised 2000-2006 — vol2 + vol3 + vol4 + vol5

Pure source-driven build (no canonical DB dependency).

Usage:
    python scripts/build_brachiobase_db.py [--version 0.2.0]
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "0.2.0"

# ---------------------------------------------------------------------------
# Source file groups per classification profile
# ---------------------------------------------------------------------------

PROFILES = [
    {
        "name": "Treatise 1965",
        "description": "Treatise on Invertebrate Paleontology, Part H, Brachiopoda (1965)",
        "sources": [
            "treatise_brachiopoda_1965_vol1.txt",
            "treatise_brachiopoda_1965_vol2.txt",
        ],
        "reference": {
            "authors": "WILLIAMS, A., ROWELL, A.J., MUIR-WOOD, H.M. & others",
            "year": 1965,
            "title": "Treatise on Invertebrate Paleontology, Part H, Brachiopoda",
            "publisher": "Geological Society of America & University of Kansas Press",
            "reference_type": "book",
            "raw_entry": (
                "Williams, A., et al., 1965. Treatise on Invertebrate Paleontology, "
                "Part H, Brachiopoda, Volumes 1 & 2."
            ),
        },
    },
    {
        "name": "Treatise Revised 2000-2006",
        "description": "Treatise on Invertebrate Paleontology, Part H, Brachiopoda (Revised), 2000-2006",
        "sources": [
            "treatise_brachiopoda_2000_vol2.txt",
            "treatise_brachiopoda_2000_vol3.txt",
            "treatise_brachiopoda_2002_vol4.txt",
            "treatise_brachiopoda_2006_vol5.txt",
        ],
        "reference": {
            "authors": "WILLIAMS, A., CARLSON, S.J., BRUNTON, C.H.C. & others",
            "year": 2000,
            "title": "Treatise on Invertebrate Paleontology, Part H, Brachiopoda (Revised), Volumes 2-5",
            "publisher": "Geological Society of America & University of Kansas",
            "reference_type": "book",
            "raw_entry": (
                "Williams, A., Carlson, S.J., Brunton, C.H.C. & others, 2000-2006. "
                "Treatise on Invertebrate Paleontology, Part H, Brachiopoda (Revised), "
                "Volumes 2-5."
            ),
        },
    },
]

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"
DST_DIR = ROOT / "db"


# ---------------------------------------------------------------------------
# Source file parser (shared logic with trilobase)
# ---------------------------------------------------------------------------

def parse_source_header(text: str):
    """Parse YAML-like header from a source file."""
    if not text.startswith("---"):
        return {}, text

    end = text.index("---", 3)
    header_text = text[3:end].strip()
    body = text[end + 3:].strip()

    header = {}
    m = re.search(r'^reference:\s*(.+)$', header_text, re.MULTILINE)
    if m:
        header["reference"] = m.group(1).strip()

    scopes = []
    for sm in re.finditer(
        r'-\s+taxon:\s*(\S+)\s+coverage:\s*(\S+)', header_text
    ):
        scopes.append({"taxon": sm.group(1), "coverage": sm.group(2)})
    header["scope"] = scopes

    return header, body


RANK_KEYWORDS = {
    "Phylum", "Subphylum", "Class", "Order", "Suborder",
    "Superfamily", "Family", "Subfamily",
}
RANK_ORDER = {
    "Phylum": -2, "Subphylum": -1,
    "Class": 0, "Order": 1, "Suborder": 2, "Superfamily": 3,
    "Family": 4, "Subfamily": 5, "Genus": 6,
}


def parse_hierarchy_body(body: str, default_leaf_rank="Genus"):
    """Parse hierarchy body into list of placement records."""
    placements = []
    stack = []  # [(rank_order, name, rank)]

    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Synonym lines
        syn_match = re.match(r'^\s*(=|~)\s+(.+)$', stripped)
        if syn_match and placements:
            marker = syn_match.group(1)
            syn_text = syn_match.group(2).strip()
            predicate = "SYNONYM_OF" if marker == "=" else "SPELLING_OF"
            sm = re.match(r'^(\S+)\s*\(([^)]+)\)$', syn_text)
            if sm:
                target = sm.group(1)
                detail = sm.group(2)
            else:
                target = syn_text.split()[0] if syn_text else syn_text
                detail = ""
            placements[-1]["synonyms"].append({
                "predicate": predicate,
                "target": target,
                "detail": detail,
            })
            continue

        # Subgenus lines (e.g. "S. (Strophomena)") — skip
        subgenus_match = re.match(r'^\s+\w+\.\s+\(', stripped)
        if subgenus_match:
            continue

        # Status markers
        status = "asserted"
        line = stripped
        if line.startswith("?"):
            status = "questionable"
            line = line[1:].strip()
        if "[incertae sedis]" in line:
            status = "incertae_sedis"
            line = line.replace("[incertae sedis]", "").strip()

        # Unassigned genera header — skip
        if "UNASSIGNED" in line.upper() or "GENERA UNASSIGNED" in line.upper():
            continue

        # Determine rank
        rank = None
        has_explicit_rank = False
        for kw in RANK_KEYWORDS:
            if line.startswith(kw + " "):
                rank = kw
                has_explicit_rank = True
                line = line[len(kw):].strip()
                break

        if rank is None:
            rank = default_leaf_rank

        # Parse name and authority
        clean = re.sub(r'\[.*?\]', '', line).strip()
        clean = clean.split("|")[0].strip()

        parts = clean.split(None, 1)
        if not parts:
            continue
        name = parts[0].strip()
        authority_str = parts[1].strip() if len(parts) > 1 else ""

        # Normalize ALL CAPS names
        if rank in ("Family", "Subfamily", "Superfamily", "Suborder") and name == name.upper() and len(name) > 1:
            name = name[0] + name[1:].lower()

        # Parse author, year
        author = ""
        year = ""
        if authority_str:
            ym = re.search(r',?\s*(\d{4}[a-z]?)\s*$', authority_str)
            if ym:
                year = ym.group(1)
                author = authority_str[:ym.start()].strip().rstrip(",")
            else:
                author = authority_str

        # Parent from rank hierarchy
        cur_order = RANK_ORDER.get(rank, 6)
        while stack and stack[-1][0] >= cur_order:
            stack.pop()

        parent_name = stack[-1][1] if stack else None
        parent_rank = stack[-1][2] if stack else None

        stack.append((cur_order, name, rank))

        placements.append({
            "name": name,
            "rank": rank,
            "author": author,
            "year": year,
            "parent_name": parent_name,
            "parent_rank": parent_rank,
            "status": status,
            "synonyms": [],
        })

    return placements


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def create_schema(cur):
    cur.executescript("""
    CREATE TABLE taxon (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rank TEXT NOT NULL
            CHECK(rank IN ('Phylum','Subphylum','Class','Order','Suborder',
                           'Superfamily','Family','Subfamily','Genus')),
        author TEXT,
        year TEXT,
        year_suffix TEXT,
        notes TEXT,
        is_placeholder INTEGER DEFAULT 0,
        type_species TEXT,
        type_species_author TEXT,
        formation TEXT,
        location TEXT,
        family TEXT,
        temporal_code TEXT,
        is_valid INTEGER DEFAULT 1,
        raw_entry TEXT,
        created_at TIMESTAMP
    );

    CREATE TABLE reference (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        authors TEXT,
        year INTEGER,
        year_suffix TEXT,
        title TEXT,
        journal TEXT,
        volume TEXT,
        pages TEXT,
        publisher TEXT,
        city TEXT,
        editors TEXT,
        book_title TEXT,
        reference_type TEXT DEFAULT 'article',
        raw_entry TEXT,
        created_at TIMESTAMP
    );

    CREATE TABLE assertion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_taxon_id INTEGER NOT NULL REFERENCES taxon(id),
        predicate TEXT NOT NULL
            CHECK(predicate IN ('PLACED_IN','SYNONYM_OF','SPELLING_OF','RANK_AS','VALID_AS')),
        object_taxon_id INTEGER REFERENCES taxon(id),
        value_text TEXT,
        reference_id INTEGER REFERENCES reference(id),
        assertion_status TEXT DEFAULT 'asserted'
            CHECK(assertion_status IN ('asserted','incertae_sedis','questionable','indet')),
        curation_confidence TEXT DEFAULT 'high',
        synonym_type TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_assertion_subject ON assertion(subject_taxon_id);
    CREATE INDEX idx_assertion_predicate ON assertion(predicate);

    CREATE TABLE classification_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        rule_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE classification_edge_cache (
        profile_id INTEGER NOT NULL REFERENCES classification_profile(id),
        child_id INTEGER NOT NULL REFERENCES taxon(id),
        parent_id INTEGER REFERENCES taxon(id),
        PRIMARY KEY (profile_id, child_id)
    );
    """)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def resolve_taxon(name, rank, dst, taxon_index, new_taxa_cache):
    key = (name.lower(), rank.lower())
    if key in taxon_index:
        return taxon_index[key]
    if key in new_taxa_cache:
        return new_taxa_cache[key]

    is_placeholder = 1 if name.lower() in ("uncertain", "unrecognizable") else 0
    cur = dst.execute("""
        INSERT INTO taxon (name, rank, is_placeholder, is_valid, created_at)
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
    """, (name, rank, is_placeholder))
    new_id = cur.lastrowid
    taxon_index[key] = new_id
    new_taxa_cache[key] = new_id
    return new_id


def process_source(dst, source_file, ref_id, taxon_index, new_taxa_cache):
    """Process source file, generating taxa, assertions, and edges."""
    text = source_file.read_text(encoding="utf-8")
    header, body = parse_source_header(text)
    placements = parse_hierarchy_body(body, default_leaf_rank="Genus")

    edges = []
    counts = {"taxon": 0, "PLACED_IN": 0, "SYNONYM_OF": 0, "SPELLING_OF": 0}
    placed_children = set()

    for p in placements:
        child_id = resolve_taxon(p["name"], p["rank"], dst, taxon_index, new_taxa_cache)

        # Update author/year if we have them and the taxon doesn't yet
        if p["author"] or p["year"]:
            dst.execute("""
                UPDATE taxon SET author = COALESCE(NULLIF(author, ''), ?),
                                 year = COALESCE(NULLIF(year, ''), ?)
                WHERE id = ? AND (author IS NULL OR author = '' OR year IS NULL OR year = '')
            """, (p["author"], p["year"], child_id))

        # Type species from raw entry
        ts_match = re.search(r'\[\*(.+?)\]', p.get("raw_entry", "") or "")
        if ts_match:
            dst.execute("UPDATE taxon SET type_species = ? WHERE id = ? AND type_species IS NULL",
                        (ts_match.group(1), child_id))

        if p["parent_name"] and child_id not in placed_children:
            parent_id = resolve_taxon(
                p["parent_name"], p["parent_rank"], dst, taxon_index, new_taxa_cache)

            dst.execute("""
                INSERT OR IGNORE INTO assertion
                    (subject_taxon_id, predicate, object_taxon_id,
                     reference_id, assertion_status, curation_confidence)
                VALUES (?, 'PLACED_IN', ?, ?, ?, 'high')
            """, (child_id, parent_id, ref_id, p["status"]))
            counts["PLACED_IN"] += 1
            edges.append((child_id, parent_id))
            placed_children.add(child_id)

        # Synonyms
        for syn in p["synonyms"]:
            target_id = resolve_taxon(
                syn["target"], "Genus", dst, taxon_index, new_taxa_cache)
            syn_type = ""
            if syn["detail"]:
                st_match = re.match(r'(j\.s\.s\.|j\.o\.s\.)', syn["detail"])
                if st_match:
                    syn_type = st_match.group(1)
            pred = syn["predicate"]
            dst.execute("""
                INSERT OR IGNORE INTO assertion
                    (subject_taxon_id, predicate, object_taxon_id,
                     reference_id, assertion_status, curation_confidence,
                     synonym_type, notes)
                VALUES (?, ?, ?, ?, 'asserted', 'high', ?, ?)
            """, (child_id, pred, target_id, ref_id, syn_type, syn["detail"]))
            counts[pred] = counts.get(pred, 0) + 1

    counts["taxon"] = len(taxon_index) + len(new_taxa_cache)
    return counts, edges


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def create_views(cur):
    cur.executescript("""
    CREATE VIEW v_taxonomy_tree AS
    WITH RECURSIVE tree AS (
        SELECT t.id, t.name, t.rank, CAST(NULL AS INTEGER) AS parent_id, 0 AS depth
        FROM taxon t
        WHERE t.id IN (
            SELECT DISTINCT e.parent_id FROM classification_edge_cache e WHERE e.profile_id = 1
        )
        AND t.id NOT IN (
            SELECT e.child_id FROM classification_edge_cache e WHERE e.profile_id = 1
        )
        UNION ALL
        SELECT t.id, t.name, t.rank, e.parent_id, tree.depth + 1
        FROM classification_edge_cache e
        JOIN tree ON e.parent_id = tree.id
        JOIN taxon t ON t.id = e.child_id
        WHERE e.profile_id = 1
    )
    SELECT * FROM tree;

    CREATE VIEW v_taxonomic_ranks AS
    SELECT t.*,
           (SELECT e.parent_id FROM classification_edge_cache e
            WHERE e.child_id = t.id AND e.profile_id = 1
            LIMIT 1) AS parent_id
    FROM taxon t;

    CREATE VIEW synonyms AS
    SELECT a.id, a.subject_taxon_id AS junior_taxon_id,
           ot.name AS senior_taxon_name,
           a.object_taxon_id AS senior_taxon_id,
           a.synonym_type,
           r.authors AS fide_author, CAST(r.year AS TEXT) AS fide_year,
           a.notes
    FROM assertion a
    LEFT JOIN taxon ot ON a.object_taxon_id = ot.id
    LEFT JOIN reference r ON a.reference_id = r.id
    WHERE a.predicate = 'SYNONYM_OF';
    """)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def _build_queries():
    return [
        ("taxonomy_tree", "Hierarchical tree from roots down (profile-aware)",
         "SELECT t.id, t.name, t.rank, NULL as parent_id, t.author\n"
         "FROM taxon t\n"
         "WHERE t.id IN (\n"
         "  SELECT DISTINCT e.parent_id FROM classification_edge_cache e\n"
         "  WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         ") AND t.id NOT IN (\n"
         "  SELECT e.child_id FROM classification_edge_cache e\n"
         "  WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         ")\n"
         "UNION ALL\n"
         "SELECT t.id, t.name, t.rank, e.parent_id, t.author\n"
         "FROM taxon t\n"
         "JOIN classification_edge_cache e ON e.child_id = t.id\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1) AND t.rank != 'Genus'\n"
         "ORDER BY rank, name",
         '{"profile_id": "integer"}'),

        ("taxonomy_tree_genera_counts", "Count of genera per direct parent",
         "SELECT e.parent_id, COUNT(*) AS genera_count\n"
         "FROM classification_edge_cache e\n"
         "JOIN taxon g ON g.id = e.child_id AND g.rank = 'Genus'\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         "GROUP BY e.parent_id",
         '{"profile_id": "integer"}'),

        ("family_genera", "Genera under a family/subfamily subtree",
         "WITH RECURSIVE subtree AS (\n"
         "    SELECT child_id FROM classification_edge_cache\n"
         "    WHERE parent_id = :family_id AND profile_id = COALESCE(:profile_id, 1)\n"
         "    UNION ALL\n"
         "    SELECT e.child_id FROM classification_edge_cache e\n"
         "    JOIN subtree s ON e.parent_id = s.child_id\n"
         "    WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         ")\n"
         "SELECT t.id, t.name, t.author, t.year, t.type_species, t.location, t.is_valid\n"
         "FROM taxon t JOIN subtree ON subtree.child_id = t.id\n"
         "WHERE t.rank = 'Genus'\n"
         "ORDER BY t.name",
         '{"family_id": "integer", "profile_id": "integer"}'),

        ("genera_list", "All genera",
         "SELECT t.id, t.name, t.author, t.year, t.family, t.temporal_code,\n"
         "       t.is_valid, t.location\n"
         "FROM taxon t WHERE t.rank = 'Genus'\n"
         "ORDER BY t.name", None),

        ("taxon_detail", "Full detail for a taxon",
         "SELECT t.*,\n"
         "       parent.name as parent_name, parent.rank as parent_rank,\n"
         "       e.parent_id as parent_id\n"
         "FROM taxon t\n"
         "LEFT JOIN classification_edge_cache e ON e.child_id = t.id\n"
         "  AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "LEFT JOIN taxon parent ON e.parent_id = parent.id\n"
         "WHERE t.id = :taxon_id",
         '{"taxon_id": "integer", "profile_id": "integer"}'),

        ("taxon_assertions", "All assertions for a taxon",
         "SELECT a.id as assertion_id, a.predicate, a.object_taxon_id,\n"
         "       ot.name as object_name, ot.rank as object_rank,\n"
         "       a.reference_id, r.authors as ref_authors, r.year as ref_year,\n"
         "       a.assertion_status, a.curation_confidence,\n"
         "       a.synonym_type, a.notes\n"
         "FROM assertion a\n"
         "LEFT JOIN taxon ot ON a.object_taxon_id = ot.id\n"
         "LEFT JOIN reference r ON a.reference_id = r.id\n"
         "WHERE a.subject_taxon_id = :taxon_id\n"
         "ORDER BY a.predicate, r.year",
         '{"taxon_id": "integer"}'),

        ("taxon_children", "Children of a taxon",
         "SELECT t.id, t.name, t.rank, t.author,\n"
         "  (SELECT COUNT(*) FROM classification_edge_cache e2\n"
         "   JOIN taxon g ON g.id = e2.child_id AND g.rank = 'Genus'\n"
         "   WHERE e2.parent_id = t.id AND e2.profile_id = COALESCE(:profile_id, 1)\n"
         "  ) AS genera_count\n"
         "FROM taxon t\n"
         "JOIN classification_edge_cache e ON e.child_id = t.id\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1) AND e.parent_id = :taxon_id\n"
         "ORDER BY t.rank, t.name",
         '{"taxon_id": "integer", "profile_id": "integer"}'),

        ("genus_hierarchy", "Ancestor chain for a taxon",
         "WITH RECURSIVE ancestors AS (\n"
         "  SELECT t.id, t.name, t.rank, t.author, 0 as depth\n"
         "  FROM classification_edge_cache e\n"
         "  JOIN taxon t ON e.parent_id = t.id\n"
         "  WHERE e.child_id = :taxon_id\n"
         "    AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "  UNION ALL\n"
         "  SELECT t.id, t.name, t.rank, t.author, anc.depth + 1\n"
         "  FROM ancestors anc\n"
         "  JOIN classification_edge_cache e ON e.child_id = anc.id\n"
         "    AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "  JOIN taxon t ON e.parent_id = t.id\n"
         ")\n"
         "SELECT id, name, rank, author FROM ancestors ORDER BY depth DESC",
         '{"taxon_id": "integer", "profile_id": "integer"}'),

        ("assertion_list", "All assertions",
         "SELECT a.id, a.predicate,\n"
         "       st.name as subject_name, st.rank as subject_rank,\n"
         "       ot.name as object_name,\n"
         "       r.authors as ref_authors, r.year as ref_year,\n"
         "       a.assertion_status\n"
         "FROM assertion a\n"
         "JOIN taxon st ON a.subject_taxon_id = st.id\n"
         "LEFT JOIN taxon ot ON a.object_taxon_id = ot.id\n"
         "LEFT JOIN reference r ON a.reference_id = r.id\n"
         "ORDER BY a.predicate, st.name", None),

        ("reference_list", "All references",
         "SELECT id, authors, year, year_suffix, title, journal, volume, pages,\n"
         "       reference_type\n"
         "FROM reference ORDER BY authors, year", None),

        ("profile_list", "All classification profiles",
         "SELECT cp.id, cp.name, cp.description, cp.rule_json,\n"
         "       (SELECT COUNT(*) FROM classification_edge_cache ec WHERE ec.profile_id = cp.id) as edge_count,\n"
         "       cp.created_at\n"
         "FROM classification_profile cp ORDER BY cp.id", None),

        ("classification_profiles_selector", "Available classification profiles",
         "SELECT id, name, description FROM classification_profile ORDER BY id",
         None),

        ("radial_tree_nodes", "Valid taxon nodes for radial tree",
         "SELECT id, name, rank, is_valid, temporal_code, author, year\n"
         "FROM taxon WHERE is_valid = 1 OR rank <> 'Genus'\n"
         "ORDER BY rank, name", None),

        ("radial_tree_edges", "Parent-child edges for radial tree",
         "SELECT child_id, parent_id\n"
         "FROM classification_edge_cache\n"
         "WHERE profile_id = :profile_id",
         '{"profile_id": "integer"}'),
    ]


# ---------------------------------------------------------------------------
# UI Manifest
# ---------------------------------------------------------------------------

def _build_manifest():
    return {
        "default_view": "taxonomy_tree",
        "global_controls": [
            {
                "type": "select",
                "param": "profile_id",
                "label": "Profile",
                "source_query": "classification_profiles_selector",
                "value_key": "id",
                "label_key": "name",
                "default": 1,
            },
        ],
        "views": {
            "taxonomy_tree": {
                "type": "hierarchy",
                "display": "tree",
                "title": "Taxonomy",
                "description": "Brachiopod hierarchical classification (Treatise 1965 & Revised 2000-2006)",
                "source_query": "taxonomy_tree",
                "icon": "bi-diagram-3",
                "hierarchy_options": {
                    "id_key": "id", "parent_key": "parent_id", "label_key": "name",
                    "rank_key": "rank", "sort_by": "label", "order_key": "id",
                },
                "tree_display": {
                    "leaf_rank": "Family",
                    "count_key": "genera_count",
                    "on_node_info": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    "item_query": "family_genera",
                    "item_param": "family_id",
                    "item_columns": [
                        {"key": "name", "label": "Genus", "italic": True},
                        {"key": "is_valid", "label": "Valid", "type": "boolean",
                         "true_label": "Yes", "false_label": "No"},
                        {"key": "author", "label": "Author"},
                        {"key": "year", "label": "Year"},
                        {"key": "type_species", "label": "Type Species", "truncate": 40},
                    ],
                    "on_item_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    "item_valid_filter": {"key": "is_valid", "label": "Valid only", "default": True},
                },
            },
            "genera_table": {
                "type": "table",
                "title": "Genera",
                "description": "Flat list of all brachiopod genera",
                "source_query": "genera_list",
                "icon": "bi-table",
                "columns": [
                    {"key": "name", "label": "Genus", "sortable": True, "searchable": True, "italic": True},
                    {"key": "author", "label": "Author", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True},
                    {"key": "family", "label": "Family", "sortable": True, "searchable": True},
                    {"key": "is_valid", "label": "Valid", "sortable": True, "type": "boolean",
                     "true_label": "Yes", "false_label": "No"},
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
            },
            "assertion_table": {
                "type": "table",
                "title": "Assertions",
                "description": "Taxonomic assertions",
                "source_query": "assertion_list",
                "icon": "bi-link-45deg",
                "columns": [
                    {"key": "predicate", "label": "Predicate", "sortable": True, "searchable": True},
                    {"key": "subject_name", "label": "Subject", "sortable": True, "searchable": True, "italic": True},
                    {"key": "subject_rank", "label": "Rank", "sortable": True},
                    {"key": "object_name", "label": "Object", "sortable": True, "searchable": True},
                    {"key": "ref_authors", "label": "Reference", "sortable": True, "searchable": True},
                    {"key": "ref_year", "label": "Year", "sortable": True},
                    {"key": "assertion_status", "label": "Status", "sortable": True},
                ],
                "default_sort": {"key": "subject_name", "direction": "asc"},
            },
            "reference_table": {
                "type": "table",
                "title": "References",
                "description": "Literature references",
                "source_query": "reference_list",
                "icon": "bi-book",
                "columns": [
                    {"key": "authors", "label": "Authors", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True},
                    {"key": "title", "label": "Title", "searchable": True},
                    {"key": "journal", "label": "Journal", "searchable": True},
                ],
                "default_sort": {"key": "authors", "direction": "asc"},
                "searchable": True,
            },
            # === Detail views ===
            "taxon_detail_view": {
                "type": "detail",
                "title": "Taxon Detail",
                "source_query": "taxon_detail",
                "id_param": "taxon_id",
                "title_key": "name",
                "subtitle_template": "{rank} — {author}, {year}",
                "sections": [
                    {
                        "title": "Classification",
                        "fields": [
                            {"key": "rank", "label": "Rank"},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "parent_name", "label": "Parent"},
                            {"key": "type_species", "label": "Type Species"},
                        ],
                    },
                    {
                        "title": "Children",
                        "type": "table",
                        "source_query": "taxon_children",
                        "params": {"taxon_id": "{id}"},
                        "columns": [
                            {"key": "name", "label": "Name", "italic": True},
                            {"key": "rank", "label": "Rank"},
                            {"key": "author", "label": "Author"},
                            {"key": "genera_count", "label": "Genera", "type": "number"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                    {
                        "title": "Assertions",
                        "type": "table",
                        "source_query": "taxon_assertions",
                        "params": {"taxon_id": "{id}"},
                        "columns": [
                            {"key": "predicate", "label": "Type"},
                            {"key": "object_name", "label": "Object"},
                            {"key": "ref_authors", "label": "Reference"},
                            {"key": "ref_year", "label": "Year"},
                            {"key": "assertion_status", "label": "Status"},
                        ],
                    },
                    {
                        "title": "Classification Path",
                        "type": "breadcrumb",
                        "source_query": "genus_hierarchy",
                        "params": {"taxon_id": "{id}"},
                        "label_key": "name",
                        "on_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                ],
            },
        },
    }


# ---------------------------------------------------------------------------
# SCODA metadata
# ---------------------------------------------------------------------------

def write_scoda_metadata(cur, version, ref_id):
    now = datetime.now(timezone.utc).isoformat()

    # artifact_metadata
    cur.execute("""
        CREATE TABLE artifact_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    metadata = {
        "artifact_id": "brachiobase",
        "name": "Brachiobase",
        "version": version,
        "description": "Brachiopod genus-level taxonomy from the Treatise (1965 & Revised 2000-2006)",
        "license": "CC-BY-4.0",
        "created_at": now,
    }
    cur.executemany(
        "INSERT INTO artifact_metadata (key, value) VALUES (?, ?)",
        metadata.items())

    # provenance
    cur.execute("""
        CREATE TABLE provenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            citation TEXT,
            url TEXT,
            accessed_at TIMESTAMP,
            notes TEXT
        )
    """)
    cur.execute("""
        INSERT INTO provenance (source_type, citation, notes)
        VALUES (?, ?, ?)
    """, (
        "publication",
        "Williams, A., Carlson, S.J., Brunton, C.H.C. & others, 2000. "
        "Treatise on Invertebrate Paleontology, Part H, Brachiopoda (Revised), "
        "Volumes 2 & 3. Geological Society of America & University of Kansas.",
        "Linguliformea, Craniiformea, and Rhynchonelliformea (part). "
        "Genus-level classification with type species.",
    ))

    # schema_descriptions
    cur.execute("""
        CREATE TABLE schema_descriptions (
            table_name TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        )
    """)
    descs = [
        ("taxon", None, "Brachiopod taxa from Phylum to Genus"),
        ("taxon", "rank", "Taxonomic rank: Phylum, Subphylum, Class, Order, Suborder, Superfamily, Family, Subfamily, Genus"),
        ("assertion", None, "Taxonomic assertions linking taxa"),
        ("assertion", "predicate", "PLACED_IN, SYNONYM_OF, SPELLING_OF, RANK_AS, VALID_AS"),
        ("reference", None, "Literature references"),
        ("classification_profile", None, "Named classification profiles"),
        ("classification_edge_cache", None, "Pre-computed parent-child edges per profile"),
    ]
    cur.executemany(
        "INSERT INTO schema_descriptions (table_name, column_name, description) VALUES (?,?,?)",
        descs)

    # ui_queries
    cur.execute("""
        CREATE TABLE ui_queries (
            name TEXT PRIMARY KEY,
            description TEXT,
            sql TEXT NOT NULL,
            params_json TEXT
        )
    """)
    cur.executemany(
        "INSERT INTO ui_queries (name, description, sql, params_json) VALUES (?,?,?,?)",
        _build_queries())

    # ui_display_intent
    cur.execute("""
        CREATE TABLE ui_display_intent (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            display_type TEXT DEFAULT 'text',
            label TEXT,
            sortable INTEGER DEFAULT 0,
            searchable INTEGER DEFAULT 0,
            visible INTEGER DEFAULT 1,
            format TEXT,
            display_order INTEGER DEFAULT 0,
            PRIMARY KEY (table_name, column_name)
        )
    """)
    intents = [
        ("taxon", "name", "text", "Name", 1, 1, 1, "italic", 1),
        ("taxon", "rank", "text", "Rank", 1, 0, 1, None, 2),
        ("taxon", "author", "text", "Author", 1, 1, 1, None, 3),
        ("taxon", "year", "text", "Year", 1, 0, 1, None, 4),
        ("taxon", "type_species", "text", "Type Species", 0, 0, 1, "italic", 5),
    ]
    cur.executemany("""
        INSERT INTO ui_display_intent
            (table_name, column_name, display_type, label, sortable, searchable,
             visible, format, display_order)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, intents)

    # ui_manifest
    cur.execute("""
        CREATE TABLE ui_manifest (
            name TEXT PRIMARY KEY,
            description TEXT,
            manifest_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json) VALUES ('default', ?, ?)",
        ("Brachiobase default UI manifest",
         json.dumps(_build_manifest(), indent=2, ensure_ascii=False)))

    # editable_entities
    cur.execute("""
        CREATE TABLE editable_entities (
            entity_name TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            display_name TEXT,
            fields_json TEXT NOT NULL
        )
    """)
    cur.execute("""
        INSERT INTO editable_entities (entity_name, table_name, display_name, fields_json)
        VALUES ('taxon', 'taxon', 'Taxon', ?)
    """, (json.dumps([
        {"name": "name", "type": "text", "required": True, "label": "Name"},
        {"name": "rank", "type": "select", "required": True, "label": "Rank",
         "options": ["Phylum", "Subphylum", "Class", "Order", "Suborder",
                     "Superfamily", "Family", "Subfamily", "Genus"]},
        {"name": "author", "type": "text", "label": "Author"},
        {"name": "year", "type": "text", "label": "Year"},
        {"name": "type_species", "type": "text", "label": "Type Species"},
        {"name": "notes", "type": "textarea", "label": "Notes"},
        {"name": "is_valid", "type": "boolean", "label": "Valid", "default": True},
    ]),))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Build brachiobase DB from source')
    parser.add_argument('--version', default=VERSION, help=f'Version (default: {VERSION})')
    args = parser.parse_args()

    version = args.version
    dst_path = DST_DIR / f"brachiobase-{version}.db"

    # Verify all source files exist
    for profile in PROFILES:
        for src_name in profile["sources"]:
            src_path = SOURCES / src_name
            if not src_path.exists():
                print(f"Error: Source file not found: {src_path}", file=sys.stderr)
                sys.exit(1)

    # Clean slate
    if dst_path.exists():
        dst_path.unlink()

    DST_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building brachiobase v{version}")
    print(f"  Output: {dst_path}")
    print(f"  Profiles: {len(PROFILES)}")

    conn = sqlite3.connect(str(dst_path))
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")

    # Phase 1: Schema
    print("\n[1/5] Creating schema...")
    create_schema(cur)
    conn.commit()

    # Shared taxon index across all profiles (taxa are shared, edges differ)
    taxon_index = {}
    all_ref_ids = []

    # Phase 2-3: Process each profile
    for pi, profile in enumerate(PROFILES, 1):
        profile_name = profile["name"]
        print(f"\n[2/5] Profile {pi}: {profile_name}")

        # Insert reference
        ref = profile["reference"]
        cur.execute("""
            INSERT INTO reference (authors, year, title, publisher, reference_type, raw_entry)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ref["authors"], ref["year"], ref["title"],
              ref["publisher"], ref["reference_type"], ref["raw_entry"]))
        ref_id = cur.lastrowid
        all_ref_ids.append(ref_id)
        conn.commit()
        print(f"  Reference id: {ref_id}")

        # Process source files for this profile
        print(f"[3/5] Processing {len(profile['sources'])} source files...")
        all_edges = []
        total_counts = {"PLACED_IN": 0, "SYNONYM_OF": 0, "SPELLING_OF": 0}
        new_taxa_cache = {}

        for src_name in profile["sources"]:
            src_path = SOURCES / src_name
            print(f"  {src_name}...", end=" ", flush=True)
            counts, edges = process_source(
                conn, src_path, ref_id, taxon_index, new_taxa_cache)
            conn.commit()
            all_edges.extend(edges)
            for k in total_counts:
                total_counts[k] += counts.get(k, 0)
            print(f"({counts['PLACED_IN']} placements)")

        # Merge new_taxa_cache into taxon_index
        taxon_index.update(new_taxa_cache)

        # Build classification profile
        print(f"[4/5] Building classification profile {pi}...")
        cur.execute("""
            INSERT INTO classification_profile (name, description, rule_json)
            VALUES (?, ?, ?)
        """, (
            profile_name,
            profile["description"],
            json.dumps({"sources": profile["sources"]}),
        ))
        profile_id = cur.lastrowid
        cur.executemany(f"""
            INSERT OR IGNORE INTO classification_edge_cache (profile_id, child_id, parent_id)
            VALUES ({profile_id}, ?, ?)
        """, all_edges)
        conn.commit()

        # Bridge orphan roots to Phylum BRACHIOPODA
        phylum_id = resolve_taxon("BRACHIOPODA", "Phylum", conn, taxon_index, new_taxa_cache)
        taxon_index.update(new_taxa_cache)
        orphan_roots = conn.execute("""
            SELECT DISTINCT e.parent_id, t.name, t.rank
            FROM classification_edge_cache e
            JOIN taxon t ON e.parent_id = t.id
            WHERE e.profile_id = ?
              AND t.id != ?
              AND t.id NOT IN (
                  SELECT e2.child_id FROM classification_edge_cache e2
                  WHERE e2.profile_id = ?
              )
        """, (profile_id, phylum_id, profile_id)).fetchall()

        if orphan_roots:
            bridge_edges = [(oid, phylum_id) for oid, _, _ in orphan_roots]
            cur.executemany(f"""
                INSERT OR IGNORE INTO classification_edge_cache (profile_id, child_id, parent_id)
                VALUES ({profile_id}, ?, ?)
            """, bridge_edges)
            conn.commit()
            print(f"  Bridge edges to Phylum BRACHIOPODA: {len(bridge_edges)}")
            for oid, oname, orank in orphan_roots:
                print(f"    {orank} {oname} -> Phylum BRACHIOPODA")

        edge_count = conn.execute(
            "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = ?",
            (profile_id,)
        ).fetchone()[0]
        print(f"  Profile {profile_id} ({profile_name}): {edge_count} edges")
        print(f"  PLACED_IN: {total_counts['PLACED_IN']}, "
              f"SYNONYM_OF: {total_counts['SYNONYM_OF']}")

    # Phase 5: Views + SCODA metadata
    total_taxa = conn.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
    total_assertions = conn.execute("SELECT COUNT(*) FROM assertion").fetchone()[0]

    print(f"\n[5/5] Writing views and SCODA metadata...")
    create_views(cur)
    write_scoda_metadata(cur, version, all_ref_ids[0])
    conn.commit()

    # Summary
    rank_counts = conn.execute(
        "SELECT rank, COUNT(*) FROM taxon GROUP BY rank ORDER BY "
        "CASE rank WHEN 'Phylum' THEN 0 WHEN 'Subphylum' THEN 1 "
        "WHEN 'Class' THEN 2 WHEN 'Order' THEN 3 WHEN 'Suborder' THEN 4 "
        "WHEN 'Superfamily' THEN 5 WHEN 'Family' THEN 6 "
        "WHEN 'Subfamily' THEN 7 WHEN 'Genus' THEN 8 END"
    ).fetchall()

    total_edges = conn.execute(
        "SELECT COUNT(*) FROM classification_edge_cache"
    ).fetchone()[0]

    print(f"\n=== Brachiobase v{version} ===")
    for rank, cnt in rank_counts:
        print(f"  {rank}: {cnt}")
    print(f"  Total taxa: {total_taxa}")
    print(f"  Assertions: {total_assertions}")
    print(f"  Total edges: {total_edges}")
    for pi, profile in enumerate(PROFILES, 1):
        ec = conn.execute(
            "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = ?",
            (pi,)).fetchone()[0]
        print(f"  Profile {pi} ({profile['name']}): {ec} edges")
    print(f"  DB: {dst_path}")
    print(f"  Size: {dst_path.stat().st_size:,} bytes")

    conn.close()


if __name__ == '__main__':
    main()
