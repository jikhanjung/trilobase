#!/usr/bin/env python3
"""Build ostracobase DB from Treatise Ostracoda source file.

Single classification profile:
  Profile 1: Treatise 1961 (Part Q, Arthropoda 3 — Ostracoda)

Pure source-driven build (no canonical DB dependency).

Usage:
    python scripts/build_ostracobase_db.py [--version 0.1.0]
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from db_path import find_paleocore_db

VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Source file groups per classification profile
# ---------------------------------------------------------------------------

PROFILES = [
    {
        "name": "Treatise 1961",
        "description": "Treatise on Invertebrate Paleontology, Part Q, Arthropoda 3 — Ostracoda (1961)",
        "sources": [
            "treatise_ostracoda_1961.txt",
        ],
        "reference": {
            "authors": "MOORE, R.C., SCOTT, H.W. & others",
            "year": 1961,
            "title": "Treatise on Invertebrate Paleontology, Part Q, Arthropoda 3 — Crustacea, Ostracoda",
            "publisher": "Geological Society of America & University of Kansas Press",
            "reference_type": "book",
            "raw_entry": (
                "Moore, R.C., Scott, H.W. & others, 1961. "
                "Treatise on Invertebrate Paleontology, Part Q, Arthropoda 3 — "
                "Crustacea, Ostracoda. Geological Society of America & University of Kansas Press."
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
    "Phylum", "Subclass", "Class", "Order", "Suborder",
    "Superfamily", "Family", "Subfamily",
}
RANK_ORDER = {
    "Phylum": -2, "Subclass": -1,
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

        # Parse name and authority; extract location and temporal_code from | fields
        clean = re.sub(r'\[.*?\]', '', line).strip()
        pipe_fields = clean.split("|")
        clean = pipe_fields[0].strip()
        location = pipe_fields[1].strip() if len(pipe_fields) > 1 else ""
        temporal_code = pipe_fields[2].strip() if len(pipe_fields) > 2 else ""
        # If only 2 fields, the second might be temporal_code (no location)
        if len(pipe_fields) == 2 and re.match(r'^[A-Z]{2,}', pipe_fields[1].strip()):
            temporal_code = pipe_fields[1].strip()
            location = ""

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
            "location": location,
            "temporal_code": temporal_code,
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
            CHECK(rank IN ('Phylum','Subphylum','Subclass','Class','Order','Suborder',
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

        # Update temporal_code and location
        if p.get("temporal_code"):
            dst.execute("UPDATE taxon SET temporal_code = ? WHERE id = ? AND (temporal_code IS NULL OR temporal_code = '')",
                        (p["temporal_code"], child_id))
        if p.get("location"):
            dst.execute("UPDATE taxon SET location = ? WHERE id = ? AND (location IS NULL OR location = '')",
                        (p["location"], child_id))

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

        # --- Profile diff ---
        ("profile_diff", "Compare edges between two classification profiles",
         "SELECT\n"
         "    COALESCE(a.child_id, b.child_id) AS taxon_id,\n"
         "    t.name AS taxon_name,\n"
         "    t.rank AS taxon_rank,\n"
         "    pa.name AS parent_a,\n"
         "    pb.name AS parent_b,\n"
         "    CASE\n"
         "        WHEN b.child_id IS NULL THEN 'removed'\n"
         "        WHEN a.child_id IS NULL THEN 'added'\n"
         "        WHEN a.parent_id != b.parent_id THEN 'moved'\n"
         "    END AS diff_status\n"
         "FROM classification_edge_cache a\n"
         "LEFT JOIN classification_edge_cache b\n"
         "    ON a.child_id = b.child_id AND b.profile_id = :compare_profile_id\n"
         "LEFT JOIN taxon t ON t.id = COALESCE(a.child_id, b.child_id)\n"
         "LEFT JOIN taxon pa ON pa.id = a.parent_id\n"
         "LEFT JOIN taxon pb ON pb.id = b.parent_id\n"
         "WHERE a.profile_id = :profile_id\n"
         "    AND (b.child_id IS NULL OR a.parent_id != b.parent_id)\n"
         "\n"
         "UNION ALL\n"
         "\n"
         "SELECT\n"
         "    b.child_id AS taxon_id,\n"
         "    t.name AS taxon_name,\n"
         "    t.rank AS taxon_rank,\n"
         "    NULL AS parent_a,\n"
         "    pb.name AS parent_b,\n"
         "    'added' AS diff_status\n"
         "FROM classification_edge_cache b\n"
         "LEFT JOIN classification_edge_cache a\n"
         "    ON b.child_id = a.child_id AND a.profile_id = :profile_id\n"
         "LEFT JOIN taxon t ON t.id = b.child_id\n"
         "LEFT JOIN taxon pb ON pb.id = b.parent_id\n"
         "WHERE b.profile_id = :compare_profile_id\n"
         "    AND a.child_id IS NULL\n"
         "\n"
         "ORDER BY diff_status, taxon_rank, taxon_name",
         '{"profile_id": "integer", "compare_profile_id": "integer"}'),

        # --- Profile diff edges (for Diff Tree rendering) ---
        # --- Timeline ---
        ("timeline_geologic_periods", "Geologic time periods for timeline axis (Mya steps)",
         "SELECT fad_mya AS id, code AS name, -fad_mya AS sort_order\n"
         "FROM temporal_code_mya\n"
         "WHERE code IN ('LCAM','MCAM','UCAM','LORD','MORD','UORD',\n"
         "               'LSIL','USIL','LDEV','MDEV','UDEV',\n"
         "               'MISS','PENN','LPERM','UPERM',\n"
         "               'LTRI','MTRI','UTRI','LJUR','MJUR','UJUR',\n"
         "               'LCRET','UCRET','TERT','HOL')\n"
         "UNION ALL\n"
         "SELECT 0.0 AS id, 'Recent' AS name, 0.0 AS sort_order\n"
         "ORDER BY sort_order",
         None),

        ("timeline_publication_years", "Distinct genus naming years for timeline axis",
         "SELECT DISTINCT CAST(t.year AS INTEGER) AS year, CAST(t.year AS INTEGER) AS label\n"
         "FROM taxon t\n"
         "JOIN classification_edge_cache e ON e.child_id = t.id\n"
         "  AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "WHERE t.rank = 'Genus' AND t.year IS NOT NULL\n"
         "ORDER BY year",
         '{"profile_id": "integer"}'),

        ("taxonomy_tree_by_geologic", "Taxa filtered by geologic time (Mya snapshot)",
         "WITH RECURSIVE filtered_genera AS (\n"
         "    SELECT t.id\n"
         "    FROM taxon t\n"
         "    JOIN classification_edge_cache e ON e.child_id = t.id AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "    WHERE t.rank = 'Genus'\n"
         "    AND (:timeline_value IS NULL OR t.temporal_code IN (\n"
         "        SELECT tr.code FROM temporal_code_mya tr\n"
         "        WHERE tr.fad_mya >= :timeline_value AND tr.lad_mya <= :timeline_value\n"
         "    ))\n"
         "), ancestors AS (\n"
         "    SELECT id AS taxon_id FROM filtered_genera\n"
         "    UNION\n"
         "    SELECT e.parent_id\n"
         "    FROM classification_edge_cache e\n"
         "    JOIN ancestors a ON e.child_id = a.taxon_id\n"
         "    WHERE e.profile_id = COALESCE(:profile_id, 1) AND e.parent_id IS NOT NULL\n"
         ")\n"
         "SELECT t.id, t.name, t.rank, t.author, t.year, t.temporal_code, t.is_valid\n"
         "FROM taxon t\n"
         "WHERE t.id IN (SELECT taxon_id FROM ancestors)\n"
         "ORDER BY t.id",
         '{"profile_id": "integer", "timeline_value": "real"}'),

        ("tree_edges_by_geologic", "Edges filtered by geologic time (Mya snapshot)",
         "WITH RECURSIVE filtered_genera AS (\n"
         "    SELECT t.id\n"
         "    FROM taxon t\n"
         "    JOIN classification_edge_cache e ON e.child_id = t.id AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "    WHERE t.rank = 'Genus'\n"
         "    AND (:timeline_value IS NULL OR t.temporal_code IN (\n"
         "        SELECT tr.code FROM temporal_code_mya tr\n"
         "        WHERE tr.fad_mya >= :timeline_value AND tr.lad_mya <= :timeline_value\n"
         "    ))\n"
         "), ancestors AS (\n"
         "    SELECT id AS taxon_id FROM filtered_genera\n"
         "    UNION\n"
         "    SELECT e.parent_id\n"
         "    FROM classification_edge_cache e\n"
         "    JOIN ancestors a ON e.child_id = a.taxon_id\n"
         "    WHERE e.profile_id = COALESCE(:profile_id, 1) AND e.parent_id IS NOT NULL\n"
         ")\n"
         "SELECT e.child_id, e.parent_id\n"
         "FROM classification_edge_cache e\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         "AND e.child_id IN (SELECT taxon_id FROM ancestors)\n"
         "AND e.parent_id IN (SELECT taxon_id FROM ancestors)",
         '{"profile_id": "integer", "timeline_value": "real"}'),

        ("taxonomy_tree_by_pubyear", "Taxa filtered by naming year (cumulative)",
         "WITH RECURSIVE filtered_genera AS (\n"
         "    SELECT t.id\n"
         "    FROM taxon t\n"
         "    JOIN classification_edge_cache e ON e.child_id = t.id AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "    WHERE t.rank = 'Genus'\n"
         "    AND t.year IS NOT NULL AND CAST(t.year AS INTEGER) <= :timeline_value\n"
         "), ancestors AS (\n"
         "    SELECT id AS taxon_id FROM filtered_genera\n"
         "    UNION\n"
         "    SELECT e.parent_id\n"
         "    FROM classification_edge_cache e\n"
         "    JOIN ancestors a ON e.child_id = a.taxon_id\n"
         "    WHERE e.profile_id = COALESCE(:profile_id, 1) AND e.parent_id IS NOT NULL\n"
         ")\n"
         "SELECT t.id, t.name, t.rank, t.author, t.year, t.temporal_code, t.is_valid\n"
         "FROM taxon t\n"
         "WHERE t.id IN (SELECT taxon_id FROM ancestors)\n"
         "ORDER BY t.id",
         '{"profile_id": "integer", "timeline_value": "integer"}'),

        ("tree_edges_by_pubyear", "Edges filtered by naming year (cumulative)",
         "WITH RECURSIVE filtered_genera AS (\n"
         "    SELECT t.id\n"
         "    FROM taxon t\n"
         "    JOIN classification_edge_cache e ON e.child_id = t.id AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "    WHERE t.rank = 'Genus'\n"
         "    AND t.year IS NOT NULL AND CAST(t.year AS INTEGER) <= :timeline_value\n"
         "), ancestors AS (\n"
         "    SELECT id AS taxon_id FROM filtered_genera\n"
         "    UNION\n"
         "    SELECT e.parent_id\n"
         "    FROM classification_edge_cache e\n"
         "    JOIN ancestors a ON e.child_id = a.taxon_id\n"
         "    WHERE e.profile_id = COALESCE(:profile_id, 1) AND e.parent_id IS NOT NULL\n"
         ")\n"
         "SELECT e.child_id, e.parent_id\n"
         "FROM classification_edge_cache e\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         "AND e.child_id IN (SELECT taxon_id FROM ancestors)\n"
         "AND e.parent_id IN (SELECT taxon_id FROM ancestors)",
         '{"profile_id": "integer", "timeline_value": "integer"}'),

        ("profile_diff_edges", "Diff edges: base profile structure with change status vs compare",
         "SELECT\n"
         "    a.child_id,\n"
         "    a.parent_id,\n"
         "    a.parent_id AS parent_id_a,\n"
         "    b.parent_id AS parent_id_b,\n"
         "    CASE\n"
         "        WHEN b.child_id IS NULL THEN 'removed'\n"
         "        WHEN a.parent_id != b.parent_id THEN 'moved'\n"
         "        ELSE 'same'\n"
         "    END AS diff_status\n"
         "FROM classification_edge_cache a\n"
         "LEFT JOIN classification_edge_cache b\n"
         "    ON a.child_id = b.child_id AND b.profile_id = :compare_profile_id\n"
         "WHERE a.profile_id = :profile_id\n"
         "\n"
         "UNION ALL\n"
         "\n"
         "SELECT\n"
         "    b.child_id,\n"
         "    b.parent_id,\n"
         "    NULL AS parent_id_a,\n"
         "    b.parent_id AS parent_id_b,\n"
         "    'added' AS diff_status\n"
         "FROM classification_edge_cache b\n"
         "LEFT JOIN classification_edge_cache a\n"
         "    ON b.child_id = a.child_id AND a.profile_id = :profile_id\n"
         "WHERE b.profile_id = :compare_profile_id\n"
         "    AND a.child_id IS NULL",
         '{"profile_id": "integer", "compare_profile_id": "integer"}'),
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
                "description": "Ostracode hierarchical classification (Treatise 1955)",
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
                "description": "Flat list of all ostracode genera",
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
            # === Tree Chart ===
            "tree_chart": {
                "type": "hierarchy",
                "display": "tree_chart",
                "title": "Tree",
                "description": "Ostracode taxonomy tree — radial or rectangular layout",
                "icon": "bi-diagram-3",
                "source_query": "radial_tree_nodes",
                "hierarchy_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "rank_key": "rank",
                },
                "tree_chart_options": {
                    "edge_query": "radial_tree_edges",
                    "edge_params": {"profile_id": "$profile_id"},
                    "color_key": "rank",
                    "leaf_rank": "Genus",
                    "on_node_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    "rank_radius": {
                        "_root": 0,
                        "Phylum": 0.03,
                        "Subclass": 0.06,
                        "Class": 0.10,
                        "Order": 0.18,
                        "Suborder": 0.28,
                        "Superfamily": 0.40,
                        "Family": 0.54,
                        "Subfamily": 0.70,
                        "Genus": 1.0,
                    },
                },
            },
            # === Profile Comparison (compound view) ===
            "profile_comparison": {
                "type": "compound",
                "title": "Comparison",
                "icon": "bi-arrow-left-right",
                "controls": [
                    {
                        "type": "select",
                        "param": "base_profile_id",
                        "label": "From",
                        "source_query": "classification_profiles_selector",
                        "value_key": "id",
                        "label_key": "name",
                        "default": 1,
                    },
                    {
                        "type": "select",
                        "param": "compare_profile_id",
                        "label": "To",
                        "source_query": "classification_profiles_selector",
                        "value_key": "id",
                        "label_key": "name",
                        "default": 2,
                    },
                ],
                "default_sub_view": "diff_table",
                "sub_views": {
                    "diff_table": {
                        "title": "Diff Table",
                        "display": "table",
                        "description": "Differences between two classification profiles",
                        "source_query": "profile_diff",
                        "searchable": True,
                        "columns": [
                            {"key": "taxon_name", "label": "Taxon", "sortable": True, "searchable": True, "italic": True},
                            {"key": "taxon_rank", "label": "Rank", "sortable": True, "searchable": True},
                            {"key": "parent_a", "label": "From Parent", "sortable": True, "searchable": True},
                            {"key": "parent_b", "label": "To Parent", "sortable": True, "searchable": True},
                            {"key": "diff_status", "label": "Status", "sortable": True, "searchable": True},
                        ],
                        "default_sort": {"key": "diff_status", "direction": "asc"},
                        "row_color_key": "diff_status",
                        "row_color_map": {
                            "moved": "warning",
                            "added": "success",
                            "removed": "danger",
                        },
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "taxon_id"},
                    },
                    "diff_tree": {
                        "title": "Diff Tree",
                        "display": "tree_chart",
                        "description": "Single merged tree with diff color coding",
                        "source_query": "radial_tree_nodes",
                        "hierarchy_options": {
                            "id_key": "id",
                            "parent_key": "parent_id",
                            "label_key": "name",
                            "rank_key": "rank",
                        },
                        "tree_chart_options": {
                            "source_view": "tree_chart",
                            "rank_radius": {
                                "_root": 0,
                                "Class": 0.06,
                                "Order": 0.14,
                                "Suborder": 0.24,
                                "Superfamily": 0.36,
                                "Family": 0.50,
                                "Subfamily": 0.66,
                                "Genus": 1.0,
                            },
                            "diff_mode": {
                                "edge_query": "profile_diff_edges",
                                "edge_params": {
                                    "profile_id": "$base_profile_id",
                                    "compare_profile_id": "$compare_profile_id",
                                },
                                "colors": {
                                    "same": "#adb5bd",
                                    "moved": "#fd7e14",
                                    "added": "#198754",
                                    "removed": "#dc3545",
                                },
                                "show_ghost_edges": False,
                            },
                        },
                    },
                    "side_by_side": {
                        "title": "Side-by-Side",
                        "display": "side_by_side",
                        "description": "Two tree charts side by side for visual comparison",
                        "source_query": "radial_tree_nodes",
                        "hierarchy_options": {
                            "id_key": "id",
                            "parent_key": "parent_id",
                            "label_key": "name",
                            "rank_key": "rank",
                        },
                        "tree_chart_options": {
                            "source_view": "tree_chart",
                        },
                    },
                    "morph": {
                        "title": "Animation",
                        "display": "tree_chart_morph",
                        "description": "Animated transition between two classification trees",
                        "source_query": "radial_tree_nodes",
                        "hierarchy_options": {
                            "id_key": "id",
                            "parent_key": "parent_id",
                            "label_key": "name",
                            "rank_key": "rank",
                        },
                        "tree_chart_options": {
                            "source_view": "tree_chart",
                        },
                    },
                },
            },
            # === Timeline (compound view) ===
            "timeline_view": {
                "type": "compound",
                "title": "Timeline",
                "icon": "bi-clock-history",
                "controls": [],
                "default_sub_view": "timeline",
                "sub_views": {
                    "timeline": {
                        "title": "Timeline",
                        "display": "tree_chart_timeline",
                        "description": "Taxonomy tree animated over geologic time or publication year",
                        "source_query": "taxonomy_tree_by_geologic",
                        "hierarchy_options": {
                            "id_key": "id",
                            "parent_key": "parent_id",
                            "label_key": "name",
                            "rank_key": "rank",
                        },
                        "tree_chart_options": {
                            "default_layout": "radial",
                            "color_key": "rank",
                            "leaf_rank": "Genus",
                            "on_node_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                            "rank_radius": {
                                "_root": 0,
                                "Phylum": 0.03,
                                "Subclass": 0.06,
                                "Class": 0.10,
                                "Order": 0.18,
                                "Suborder": 0.28,
                                "Superfamily": 0.40,
                                "Family": 0.54,
                                "Subfamily": 0.70,
                                "Genus": 1.0,
                            },
                            "edge_query": "tree_edges_by_geologic",
                            "edge_params": {"profile_id": "$profile_id"},
                            "edge_id_key": "child_id",
                            "edge_parent_key": "parent_id",
                        },
                        "timeline_options": {
                            "param_name": "timeline_value",
                            "default_step_size": 1,
                            "axis_modes": [
                                {
                                    "key": "geologic",
                                    "label": "Geologic Time",
                                    "axis_query": "timeline_geologic_periods",
                                    "value_key": "id",
                                    "label_key": "name",
                                    "order_key": "sort_order",
                                    "source_query_override": "taxonomy_tree_by_geologic",
                                    "edge_query_override": "tree_edges_by_geologic",
                                },
                                {
                                    "key": "pubyear",
                                    "label": "Publication Year",
                                    "axis_query": "timeline_publication_years",
                                    "value_key": "year",
                                    "label_key": "label",
                                    "order_key": "year",
                                    "source_query_override": "taxonomy_tree_by_pubyear",
                                    "edge_query_override": "tree_edges_by_pubyear",
                                },
                            ],
                        },
                    },
                },
            },
            # === Detail views ===
            "taxon_detail_view": {
                "type": "detail",
                "title": "Taxon Detail",
                "source_query": "taxon_detail",
                "source_param": "taxon_id",
                "sub_queries": {
                    "children": {"query": "taxon_children", "params": {"taxon_id": "id"}},
                    "assertions": {"query": "taxon_assertions", "params": {"taxon_id": "id"}},
                    "hierarchy": {"query": "genus_hierarchy", "params": {"taxon_id": "id"}},
                },
                "title_template": {"format": '<span class="badge bg-secondary me-2">{rank}</span> {name}'},
                "sections": [
                    {
                        "title": "Classification",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "rank", "label": "Rank"},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "parent_name", "label": "Parent",
                             "format": "link",
                             "link": {"detail_view": "taxon_detail_view", "id_path": "parent_id"},
                             "suffix_key": "parent_rank", "suffix_format": "({value})"},
                            {"key": "type_species", "label": "Type Species"},
                            {"key": "temporal_code", "label": "Range"},
                        ],
                    },
                    {
                        "title": "Children ({count})",
                        "type": "linked_table",
                        "data_key": "children",
                        "condition": "children",
                        "columns": [
                            {"key": "name", "label": "Name", "italic": True},
                            {"key": "rank", "label": "Rank"},
                            {"key": "author", "label": "Author"},
                            {"key": "genera_count", "label": "Genera", "type": "number"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                    {
                        "title": "Assertions ({count})",
                        "type": "linked_table",
                        "data_key": "assertions",
                        "condition": "assertions",
                        "columns": [
                            {"key": "predicate", "label": "Type"},
                            {"key": "object_name", "label": "Object"},
                            {"key": "ref_authors", "label": "Reference"},
                            {"key": "ref_year", "label": "Year"},
                            {"key": "assertion_status", "label": "Status"},
                        ],
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
        "artifact_id": "ostracobase",
        "name": "Ostracobase",
        "version": version,
        "description": "Ostracode genus-level taxonomy from the Treatise (1961)",
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
        "Moore, R.C., Scott, H.W. & others, 1961. "
        "Treatise on Invertebrate Paleontology, Part Q, Arthropoda 3 — "
        "Crustacea, Ostracoda. Geological Society of America & University of Kansas Press.",
        "Ostracoda genus-level classification with type species.",
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
        ("taxon", None, "Ostracode taxa from Subphylum to Genus"),
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
        ("Ostracobase default UI manifest",
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
         "options": ["Phylum", "Subclass", "Class", "Order", "Suborder",
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
    parser = argparse.ArgumentParser(description='Build ostracobase DB from source')
    parser.add_argument('--version', default=VERSION, help=f'Version (default: {VERSION})')
    args = parser.parse_args()

    version = args.version
    dst_path = DST_DIR / f"ostracobase-{version}.db"

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

    print(f"Building ostracobase v{version}")
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

        # Bridge orphan roots to Subphylum OSTRACODA
        phylum_id = resolve_taxon("OSTRACODA", "Subclass", conn, taxon_index, new_taxa_cache)
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
            print(f"  Bridge edges to Subphylum OSTRACODA: {len(bridge_edges)}")
            for oid, oname, orank in orphan_roots:
                print(f"    {orank} {oname} -> Subphylum OSTRACODA")

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

    # Build temporal_code_mya mapping table
    print("  Building temporal_code_mya table...")
    pc_db = Path(find_paleocore_db())
    conn.execute(f"ATTACH DATABASE '{pc_db}' AS pc")
    conn.execute("""
        CREATE TABLE temporal_code_mya AS
        SELECT code, start_mya AS fad_mya, end_mya AS lad_mya
        FROM pc.temporal_ranges
        WHERE start_mya IS NOT NULL
        UNION ALL SELECT 'TERT', 66.0, 2.58
        UNION ALL SELECT 'HOL', 0.0117, 0.0
        UNION ALL SELECT 'REC', 0.0117, 0.0
    """)
    # Also add any compound codes found in the data (e.g., LDEV-MDEV)
    compound_codes = conn.execute("""
        SELECT DISTINCT t.temporal_code FROM taxon t
        WHERE t.temporal_code LIKE '%-%'
        AND t.temporal_code NOT IN (SELECT code FROM temporal_code_mya)
    """).fetchall()
    for (code,) in compound_codes:
        parts = code.split('-')
        if len(parts) == 2:
            fad = conn.execute("SELECT fad_mya FROM temporal_code_mya WHERE code = ?", (parts[0],)).fetchone()
            lad = conn.execute("SELECT lad_mya FROM temporal_code_mya WHERE code = ?", (parts[1],)).fetchone()
            if fad and lad:
                conn.execute("INSERT INTO temporal_code_mya VALUES (?, ?, ?)", (code, fad[0], lad[0]))
    n_tcm = conn.execute("SELECT COUNT(*) FROM temporal_code_mya").fetchone()[0]
    conn.execute("DETACH DATABASE pc")
    conn.commit()
    print(f"  → {n_tcm} temporal_code_mya mappings")

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

    print(f"\n=== Ostracobase v{version} ===")
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
