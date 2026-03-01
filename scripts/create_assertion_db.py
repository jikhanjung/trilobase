#!/usr/bin/env python3
"""P74 — Assertion-centric test DB builder.

Reads db/trilobase-{version}.db and creates
db/trilobase_assertion-{version}.db with:
  - taxon (no parent_id)
  - reference (renamed bibliography)
  - assertion (subject/predicate/object)
  - classification_profile + classification_edge_cache
  - compatibility views (v_taxonomy_tree, v_taxonomic_ranks, synonyms)

Canonical DB is NOT modified.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from db_path import find_trilobase_db

ASSERTION_VERSION = "0.1.1"

ROOT = Path(__file__).resolve().parent.parent
SRC_DB = Path(find_trilobase_db())
DST_DIR = ROOT / "db"

# Adrain 2011 bibliography id in source DB
ADRAIN_2011_BIB_ID = 2131
# Jell & Adrain 2002 is NOT in bibliography — we'll insert it as reference id 0
# (using id that won't collide with existing bibliography ids 1..2131)
JA2002_REF_ID = 0  # will be inserted manually


def create_schema(cur: sqlite3.Cursor) -> None:
    """Create all tables and indexes."""
    cur.executescript("""
    -- taxon: no parent_id
    CREATE TABLE taxon (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        rank TEXT NOT NULL,
        author TEXT,
        year TEXT,
        year_suffix TEXT,
        notes TEXT,
        is_placeholder INTEGER DEFAULT 0,
        genera_count INTEGER DEFAULT 0,
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

    -- reference: bibliography with renamed table
    CREATE TABLE reference (
        id INTEGER PRIMARY KEY,
        authors TEXT NOT NULL,
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
        raw_entry TEXT NOT NULL,
        created_at TIMESTAMP
    );

    -- assertion: subject/predicate/object
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
        is_accepted INTEGER DEFAULT 0,
        synonym_type TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_assertion_subject ON assertion(subject_taxon_id);
    CREATE INDEX idx_assertion_predicate ON assertion(predicate);
    CREATE UNIQUE INDEX idx_unique_accepted
        ON assertion(subject_taxon_id, predicate) WHERE is_accepted = 1;

    -- classification_profile
    CREATE TABLE classification_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        rule_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- classification_edge_cache
    CREATE TABLE classification_edge_cache (
        profile_id INTEGER NOT NULL REFERENCES classification_profile(id),
        child_id INTEGER NOT NULL REFERENCES taxon(id),
        parent_id INTEGER REFERENCES taxon(id),
        PRIMARY KEY (profile_id, child_id)
    );

    -- Junction tables (copied from canonical DB)
    CREATE TABLE genus_formations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        genus_id INTEGER NOT NULL REFERENCES taxon(id),
        formation_id INTEGER NOT NULL,
        is_type_locality INTEGER DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(genus_id, formation_id)
    );
    CREATE INDEX idx_gf_genus ON genus_formations(genus_id);
    CREATE INDEX idx_gf_formation ON genus_formations(formation_id);

    CREATE TABLE genus_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        genus_id INTEGER NOT NULL REFERENCES taxon(id),
        country_id INTEGER NOT NULL,
        region TEXT,
        is_type_locality INTEGER DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        region_id INTEGER,
        UNIQUE(genus_id, country_id, region)
    );
    CREATE INDEX idx_gl_genus ON genus_locations(genus_id);
    CREATE INDEX idx_gl_country ON genus_locations(country_id);
    CREATE INDEX idx_gl_region ON genus_locations(region_id);

    CREATE TABLE taxon_reference (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        taxon_id INTEGER NOT NULL REFERENCES taxon(id),
        reference_id INTEGER NOT NULL REFERENCES reference(id),
        relationship_type TEXT NOT NULL DEFAULT 'original_description'
            CHECK(relationship_type IN ('original_description', 'fide')),
        opinion_id INTEGER,
        match_confidence TEXT NOT NULL DEFAULT 'high'
            CHECK(match_confidence IN ('high', 'medium', 'low')),
        match_method TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(taxon_id, reference_id, relationship_type, opinion_id)
    );
    CREATE INDEX idx_tr_taxon ON taxon_reference(taxon_id);
    CREATE INDEX idx_tr_ref ON taxon_reference(reference_id);
    CREATE INDEX idx_tr_type ON taxon_reference(relationship_type);
    """)


def copy_taxon(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    """Copy taxonomic_ranks → taxon (excluding parent_id, uid columns)."""
    rows = src.execute("""
        SELECT id, name, rank, author, year, year_suffix, notes,
               is_placeholder, genera_count, type_species, type_species_author,
               formation, location, family, temporal_code, is_valid,
               raw_entry, created_at
        FROM taxonomic_ranks
    """).fetchall()
    dst.executemany("""
        INSERT INTO taxon (id, name, rank, author, year, year_suffix, notes,
                           is_placeholder, genera_count, type_species, type_species_author,
                           formation, location, family, temporal_code, is_valid,
                           raw_entry, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    return len(rows)


def copy_reference(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    """Copy bibliography → reference, plus insert Jell & Adrain 2002."""
    rows = src.execute("""
        SELECT id, authors, year, year_suffix, title, journal, volume, pages,
               publisher, city, editors, book_title, reference_type,
               raw_entry, created_at
        FROM bibliography
    """).fetchall()
    dst.executemany("""
        INSERT INTO reference (id, authors, year, year_suffix, title, journal,
                               volume, pages, publisher, city, editors, book_title,
                               reference_type, raw_entry, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

    # Insert Jell & Adrain 2002 as reference id 0
    dst.execute("""
        INSERT INTO reference (id, authors, year, title, journal, volume, pages,
                               reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        JA2002_REF_ID,
        "JELL, P.A. & ADRAIN, J.M.",
        2002,
        "Available Generic Names for Trilobites",
        "Memoirs of the Queensland Museum",
        "48",
        "331-553",
        "article",
        "Jell, P.A., and Adrain, J.M., 2002, Available Generic Names for Trilobites: "
        "Memoirs of the Queensland Museum, v. 48, p. 331-553.",
    ))

    # Update Adrain 2011 with correct bibliographic details
    dst.execute("""
        UPDATE reference SET
            title = ?,
            journal = ?,
            volume = ?,
            pages = ?,
            editors = ?,
            book_title = ?,
            reference_type = ?,
            raw_entry = ?
        WHERE id = ?
    """, (
        "Class Trilobita Walch, 1771",
        "Zootaxa",
        "3148",
        "104",
        "Zhang, Z.-Q.",
        "Animal biodiversity: An outline of higher-level classification "
        "and survey of taxonomic richness",
        "incollection",
        "Adrain, J.M., 2011, Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) "
        "Animal biodiversity: An outline of higher-level classification and survey "
        "of taxonomic richness: Zootaxa, v. 3148, p. 104.",
        ADRAIN_2011_BIB_ID,
    ))
    return len(rows) + 1


def convert_opinions(src: sqlite3.Connection, dst: sqlite3.Connection) -> dict:
    """Convert taxonomic_opinions → assertion."""
    opinions = src.execute("""
        SELECT id, taxon_id, opinion_type, related_taxon_id,
               bibliography_id, assertion_status, curation_confidence,
               is_accepted, synonym_type, notes, created_at
        FROM taxonomic_opinions
    """).fetchall()

    counts = {"PLACED_IN": 0, "SYNONYM_OF": 0, "SPELLING_OF": 0}
    for op in opinions:
        (op_id, taxon_id, opinion_type, related_taxon_id,
         bib_id, status, confidence, accepted, syn_type, notes, created) = op
        dst.execute("""
            INSERT INTO assertion (subject_taxon_id, predicate, object_taxon_id,
                                   reference_id, assertion_status, curation_confidence,
                                   is_accepted, synonym_type, notes, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (taxon_id, opinion_type, related_taxon_id,
              bib_id, status, confidence, accepted, syn_type, notes, created))
        counts[opinion_type] = counts.get(opinion_type, 0) + 1

    return counts


def generate_placed_in(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    """Generate PLACED_IN assertions from parent_id for taxons not already covered."""
    # Get taxon ids that already have a PLACED_IN assertion (from opinions)
    existing = set(
        r[0] for r in dst.execute(
            "SELECT DISTINCT subject_taxon_id FROM assertion WHERE predicate='PLACED_IN'"
        ).fetchall()
    )

    # Get all taxons with parent_id
    parents = src.execute("""
        SELECT id, parent_id, rank FROM taxonomic_ranks
        WHERE parent_id IS NOT NULL
    """).fetchall()

    # Determine reference: hierarchy nodes → Adrain 2011, genera → JA2002
    hierarchy_ranks = {"Order", "Suborder", "Superfamily", "Family"}
    count = 0
    for taxon_id, parent_id, rank in parents:
        if taxon_id in existing:
            continue
        ref_id = ADRAIN_2011_BIB_ID if rank in hierarchy_ranks else JA2002_REF_ID
        dst.execute("""
            INSERT INTO assertion (subject_taxon_id, predicate, object_taxon_id,
                                   reference_id, assertion_status, curation_confidence,
                                   is_accepted)
            VALUES (?,?,?,?,?,?,?)
        """, (taxon_id, "PLACED_IN", parent_id, ref_id, "asserted", "high", 1))
        count += 1

    return count


def create_profiles(dst: sqlite3.Connection) -> None:
    """Create default classification profiles."""
    dst.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "default",
        "All accepted PLACED_IN assertions",
        '{"predicate": "PLACED_IN", "is_accepted": 1}',
    ))
    dst.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "ja2002_strict",
        "Only Jell & Adrain (2002) PLACED_IN assertions",
        '{"predicate": "PLACED_IN", "is_accepted": 1, "reference_id": 0}',
    ))


def build_edge_cache(dst: sqlite3.Connection) -> int:
    """Build edge cache for the default profile (profile_id=1)."""
    edges = dst.execute("""
        SELECT subject_taxon_id, object_taxon_id
        FROM assertion
        WHERE predicate = 'PLACED_IN' AND is_accepted = 1
    """).fetchall()
    dst.executemany("""
        INSERT INTO classification_edge_cache (profile_id, child_id, parent_id)
        VALUES (1, ?, ?)
    """, edges)
    return len(edges)


def copy_junction_tables(src: sqlite3.Connection, dst: sqlite3.Connection) -> dict:
    """Copy junction tables from canonical DB."""
    counts = {}

    # genus_formations
    rows = src.execute("""
        SELECT id, genus_id, formation_id, is_type_locality, notes, created_at
        FROM genus_formations
    """).fetchall()
    dst.executemany("""
        INSERT INTO genus_formations (id, genus_id, formation_id, is_type_locality, notes, created_at)
        VALUES (?,?,?,?,?,?)
    """, rows)
    counts["genus_formations"] = len(rows)

    # genus_locations
    rows = src.execute("""
        SELECT id, genus_id, country_id, region, is_type_locality, notes, created_at, region_id
        FROM genus_locations
    """).fetchall()
    dst.executemany("""
        INSERT INTO genus_locations (id, genus_id, country_id, region, is_type_locality, notes, created_at, region_id)
        VALUES (?,?,?,?,?,?,?,?)
    """, rows)
    counts["genus_locations"] = len(rows)

    # taxon_bibliography (src) → taxon_reference (dst): bibliography_id → reference_id
    rows = src.execute("""
        SELECT id, taxon_id, bibliography_id, relationship_type, opinion_id,
               match_confidence, match_method, notes, created_at
        FROM taxon_bibliography
    """).fetchall()
    dst.executemany("""
        INSERT INTO taxon_reference (id, taxon_id, reference_id, relationship_type, opinion_id,
                                     match_confidence, match_method, notes, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, rows)
    counts["taxon_reference"] = len(rows)

    return counts


def create_scoda_metadata(dst: sqlite3.Connection, version: str = ASSERTION_VERSION) -> None:
    """Create SCODA metadata tables for .scoda packaging."""
    cur = dst.cursor()

    # --- DDL ---
    cur.executescript("""
    CREATE TABLE artifact_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE provenance (id INTEGER PRIMARY KEY, source_type TEXT, citation TEXT,
                             description TEXT, year INTEGER, url TEXT);
    CREATE TABLE schema_descriptions (table_name TEXT NOT NULL, column_name TEXT,
                                      description TEXT NOT NULL);
    CREATE TABLE ui_display_intent (id INTEGER PRIMARY KEY, entity TEXT, default_view TEXT,
                                    description TEXT, source_query TEXT, priority INTEGER DEFAULT 0);
    CREATE TABLE ui_queries (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT,
                             sql TEXT NOT NULL, params_json TEXT,
                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE ui_manifest (name TEXT PRIMARY KEY, description TEXT, manifest_json TEXT NOT NULL,
                              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    """)

    # --- artifact_metadata ---
    cur.executemany("INSERT INTO artifact_metadata VALUES (?,?)", [
        ("artifact_id", "trilobase-assertion"),
        ("name", "Trilobase (Assertion-Centric)"),
        ("version", version),
        ("schema_version", "1.0"),
        ("created_at", "2026-02-28"),
        ("description", "Assertion-centric trilobite taxonomy — experimental P74 model"),
        ("license", "CC-BY-4.0"),
    ])

    # --- provenance ---
    cur.executemany("INSERT INTO provenance VALUES (?,?,?,?,?,?)", [
        (1, "primary",
         "Jell, P.A., and Adrain, J.M., 2002, Available Generic Names for Trilobites: "
         "Memoirs of the Queensland Museum, v. 48, p. 331-553.",
         "Primary source for genus-level taxonomy, synonymy, and type species", 2002, None),
        (2, "supplementary",
         "Adrain, J.M., 2011, Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) "
         "Animal biodiversity: An outline of higher-level classification and survey "
         "of taxonomic richness: Zootaxa, v. 3148, p. 104.",
         "Suprafamilial classification (Order, Suborder, Superfamily)", 2011, None),
        (3, "build",
         "Trilobase assertion-centric pipeline (2026). Script: create_assertion_db.py",
         "P74b assertion-centric model with full UI parity", 2026, None),
    ])

    # --- schema_descriptions ---
    cur.executemany("INSERT INTO schema_descriptions VALUES (?,?,?)", [
        ("taxon", None, "Taxonomic names (Class to Genus) without parent_id — hierarchy derived from assertions"),
        ("taxon", "id", "Primary key"),
        ("taxon", "name", "Taxon name"),
        ("taxon", "rank", "Taxonomic rank (Class, Order, Suborder, Superfamily, Family, Subfamily, Genus)"),
        ("reference", None, "Literature references (bibliography + Jell & Adrain 2002)"),
        ("assertion", None, "Taxonomic assertions: subject taxon + predicate + object taxon"),
        ("assertion", "predicate", "PLACED_IN, SYNONYM_OF, SPELLING_OF, RANK_AS, VALID_AS"),
        ("assertion", "is_accepted", "1 = currently accepted assertion for this subject+predicate"),
        ("classification_profile", None, "Named classification profiles for building different trees"),
        ("classification_edge_cache", None, "Materialized parent-child edges for a given profile"),
        ("genus_formations", None, "Genus-Formation many-to-many junction table"),
        ("genus_locations", None, "Genus-Country/Region many-to-many junction table"),
        ("taxon_reference", None, "Taxon-Reference FK links (renamed from taxon_bibliography)"),
        ("taxon_reference", "reference_id", "FK to reference(id) — renamed from bibliography_id"),
    ])

    # --- ui_display_intent ---
    cur.executemany(
        "INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority) "
        "VALUES (?,?,?,?,?,?)", [
            (1, "genera", "tree", "Taxonomy tree view", "taxonomy_tree", 0),
            (2, "genera", "table", "Genera flat table", "genera_list", 1),
            (3, "references", "table", "References table", "reference_list", 0),
            (4, "formations", "table", "Formations table", "formations_list", 0),
            (5, "countries", "table", "Countries table", "countries_list", 0),
            (6, "profiles", "table", "Classification profiles", "profile_list", 0),
        ])

    # --- ui_queries ---
    queries = _build_queries()
    for name, desc, sql, params in queries:
        cur.execute(
            "INSERT INTO ui_queries (name, description, sql, params_json) VALUES (?,?,?,?)",
            (name, desc, sql, params))

    # --- ui_manifest ---
    manifest = _build_manifest()
    cur.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json) VALUES (?,?,?)",
        ("default", "Assertion-centric taxonomy views (P74b — full UI parity)",
         json.dumps(manifest, ensure_ascii=False)))

    dst.commit()


# ---------------------------------------------------------------------------
# UI Queries
# ---------------------------------------------------------------------------

def _build_queries():
    """Return list of (name, description, sql, params_json) tuples."""
    return [
        # --- Tree / Genera ---
        ("taxonomy_tree", "Hierarchical tree from Class to Family",
         "SELECT id, name, rank, parent_id, author, genera_count\n"
         "FROM v_taxonomic_ranks\n"
         "WHERE rank != 'Genus'\n"
         "ORDER BY rank, name", None),

        ("family_genera", "Genera belonging to a specific family",
         "SELECT t.id, t.name, t.author, t.year, t.type_species, t.location, t.is_valid\n"
         "FROM taxon t\n"
         "JOIN assertion a ON a.subject_taxon_id = t.id\n"
         "  AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1\n"
         "WHERE a.object_taxon_id = :family_id AND t.rank = 'Genus'\n"
         "ORDER BY t.name",
         '{"family_id": "integer"}'),

        ("genera_list", "All genera with family and validity",
         "SELECT t.id, t.name, t.author, t.year, t.family, t.temporal_code,\n"
         "       t.is_valid, t.location\n"
         "FROM taxon t WHERE t.rank = 'Genus'\n"
         "ORDER BY t.name", None),

        ("valid_genera_list", "Valid genera only",
         "SELECT t.id, t.name, t.author, t.year, t.family, t.temporal_code, t.location\n"
         "FROM taxon t\n"
         "WHERE t.rank = 'Genus' AND t.is_valid = 1\n"
         "ORDER BY t.name", None),

        # --- Taxon detail ---
        ("taxon_detail", "Full detail for a taxon with parent info",
         "SELECT t.*,\n"
         "       parent.name as parent_name, parent.rank as parent_rank,\n"
         "       a.object_taxon_id as parent_id\n"
         "FROM taxon t\n"
         "LEFT JOIN assertion a ON a.subject_taxon_id = t.id\n"
         "  AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1\n"
         "LEFT JOIN taxon parent ON a.object_taxon_id = parent.id\n"
         "WHERE t.id = :taxon_id",
         '{"taxon_id": "integer"}'),

        ("taxon_assertions", "All assertions for a specific taxon",
         "SELECT a.id, a.predicate, a.object_taxon_id,\n"
         "       ot.name as object_name, ot.rank as object_rank,\n"
         "       a.reference_id, r.authors as ref_authors, r.year as ref_year,\n"
         "       a.assertion_status, a.curation_confidence,\n"
         "       a.is_accepted, a.synonym_type, a.notes\n"
         "FROM assertion a\n"
         "LEFT JOIN taxon ot ON a.object_taxon_id = ot.id\n"
         "LEFT JOIN reference r ON a.reference_id = r.id\n"
         "WHERE a.subject_taxon_id = :taxon_id\n"
         "ORDER BY a.predicate, a.is_accepted DESC",
         '{"taxon_id": "integer"}'),

        ("taxon_children", "Children of a taxon via assertions",
         "SELECT t.id, t.name, t.rank, t.author, t.genera_count\n"
         "FROM taxon t\n"
         "JOIN assertion a ON a.subject_taxon_id = t.id\n"
         "  AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1\n"
         "WHERE a.object_taxon_id = :taxon_id\n"
         "ORDER BY t.rank, t.name",
         '{"taxon_id": "integer"}'),

        ("taxon_children_counts", "Child rank counts",
         "SELECT t.rank, COUNT(*) as count\n"
         "FROM taxon t\n"
         "JOIN assertion a ON a.subject_taxon_id = t.id\n"
         "  AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1\n"
         "WHERE a.object_taxon_id = :taxon_id\n"
         "GROUP BY t.rank",
         '{"taxon_id": "integer"}'),

        # --- Genus-specific ---
        ("genus_hierarchy", "Ancestor chain for a taxon via assertions",
         "WITH RECURSIVE ancestors AS (\n"
         "  SELECT t.id, t.name, t.rank, t.author, 0 as depth\n"
         "  FROM assertion a\n"
         "  JOIN taxon t ON a.object_taxon_id = t.id\n"
         "  WHERE a.subject_taxon_id = :taxon_id\n"
         "    AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1\n"
         "  UNION ALL\n"
         "  SELECT t.id, t.name, t.rank, t.author, anc.depth + 1\n"
         "  FROM ancestors anc\n"
         "  JOIN assertion a ON a.subject_taxon_id = anc.id\n"
         "    AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1\n"
         "  JOIN taxon t ON a.object_taxon_id = t.id\n"
         ")\n"
         "SELECT id, name, rank, author FROM ancestors ORDER BY depth DESC",
         '{"taxon_id": "integer"}'),

        ("genus_synonyms", "Synonyms for a genus",
         "SELECT s.*, senior.name as senior_name\n"
         "FROM synonyms s\n"
         "LEFT JOIN taxon senior ON s.senior_taxon_id = senior.id\n"
         "WHERE s.junior_taxon_id = :taxon_id",
         '{"taxon_id": "integer"}'),

        ("genus_ics_mapping", "Temporal code → ICS mapping",
         "SELECT ic.id, ic.name, ic.rank, m.mapping_type\n"
         "FROM pc.temporal_ics_mapping m\n"
         "JOIN pc.ics_chronostrat ic ON m.ics_id = ic.id\n"
         "WHERE m.temporal_code = :temporal_code",
         '{"temporal_code": "text"}'),

        ("genus_formations", "Formations for a genus",
         "SELECT f.id, f.name, f.formation_type, f.country, f.period\n"
         "FROM genus_formations gf\n"
         "JOIN pc.formations f ON gf.formation_id = f.id\n"
         "WHERE gf.genus_id = :taxon_id",
         '{"taxon_id": "integer"}'),

        ("genus_locations", "Countries/regions for a genus",
         "SELECT CASE WHEN r.level = 'country' THEN r.id ELSE parent.id END as country_id,\n"
         "       CASE WHEN r.level = 'country' THEN r.name ELSE parent.name END as country_name,\n"
         "       CASE WHEN r.level = 'region' THEN r.id ELSE NULL END as region_id,\n"
         "       CASE WHEN r.level = 'region' THEN r.name ELSE NULL END as region_name\n"
         "FROM genus_locations gl\n"
         "JOIN pc.geographic_regions r ON gl.region_id = r.id\n"
         "LEFT JOIN pc.geographic_regions parent ON r.parent_id = parent.id\n"
         "WHERE gl.genus_id = :taxon_id",
         '{"taxon_id": "integer"}'),

        ("genus_bibliography", "References for a genus via taxon_reference",
         "SELECT ref.id, ref.authors, ref.year, ref.title, ref.journal, tr.relationship_type\n"
         "FROM taxon_reference tr\n"
         "JOIN reference ref ON ref.id = tr.reference_id\n"
         "WHERE tr.taxon_id = :taxon_id\n"
         "ORDER BY ref.year, ref.authors",
         '{"taxon_id": "integer"}'),

        ("taxon_bibliography", "Reference entries for a taxon",
         "SELECT ref.id, ref.authors, ref.year, ref.year_suffix, ref.title, ref.reference_type,\n"
         "       tr.relationship_type, tr.match_confidence\n"
         "FROM taxon_reference tr\n"
         "JOIN reference ref ON tr.reference_id = ref.id\n"
         "WHERE tr.taxon_id = :taxon_id\n"
         "ORDER BY tr.relationship_type, ref.year, ref.authors",
         '{"taxon_id": "integer"}'),

        # --- References ---
        ("reference_list", "All references sorted by author/year",
         "SELECT id, authors, year, year_suffix, title, journal, volume, pages,\n"
         "       reference_type\n"
         "FROM reference ORDER BY authors, year", None),

        ("reference_detail", "Detail for a single reference",
         "SELECT * FROM reference WHERE id = :ref_id",
         '{"ref_id": "integer"}'),

        ("reference_assertions", "Assertions citing a specific reference",
         "SELECT a.id, a.predicate, a.subject_taxon_id,\n"
         "       st.name as subject_name, st.rank as subject_rank,\n"
         "       a.object_taxon_id, ot.name as object_name,\n"
         "       a.assertion_status, a.is_accepted\n"
         "FROM assertion a\n"
         "JOIN taxon st ON a.subject_taxon_id = st.id\n"
         "LEFT JOIN taxon ot ON a.object_taxon_id = ot.id\n"
         "WHERE a.reference_id = :ref_id\n"
         "ORDER BY a.predicate, st.name",
         '{"ref_id": "integer"}'),

        ("reference_genera", "Genera linked to a reference",
         "SELECT t.id, t.name, t.author, t.year, t.is_valid\n"
         "FROM taxon_reference tr\n"
         "JOIN taxon t ON t.id = tr.taxon_id\n"
         "WHERE tr.reference_id = :ref_id AND t.rank = 'Genus'\n"
         "ORDER BY t.name",
         '{"ref_id": "integer"}'),

        # --- Assertions ---
        ("assertion_list", "All assertions with taxon and reference names",
         "SELECT a.id, a.predicate,\n"
         "       st.name as subject_name, st.rank as subject_rank,\n"
         "       ot.name as object_name,\n"
         "       r.authors as ref_authors, r.year as ref_year,\n"
         "       a.assertion_status, a.is_accepted\n"
         "FROM assertion a\n"
         "JOIN taxon st ON a.subject_taxon_id = st.id\n"
         "LEFT JOIN taxon ot ON a.object_taxon_id = ot.id\n"
         "LEFT JOIN reference r ON a.reference_id = r.id\n"
         "ORDER BY a.predicate, st.name", None),

        # --- Formations (pc.*) ---
        ("formations_list", "All formations with taxa count",
         "SELECT f.id, f.name, f.formation_type, f.country, f.period,\n"
         "       (SELECT COUNT(*) FROM genus_formations gf WHERE gf.formation_id = f.id) as taxa_count\n"
         "FROM pc.formations f ORDER BY f.name", None),

        ("formation_detail", "Formation detail with taxa count",
         "SELECT f.id, f.name, f.normalized_name, f.formation_type, f.country, f.region, f.period,\n"
         "       COUNT(DISTINCT gf.genus_id) as taxa_count\n"
         "FROM pc.formations f\n"
         "LEFT JOIN genus_formations gf ON gf.formation_id = f.id\n"
         "WHERE f.id = :formation_id\n"
         "GROUP BY f.id",
         '{"formation_id": "integer"}'),

        ("formation_genera", "Genera for a formation",
         "SELECT t.id, t.name, t.author, t.year, t.is_valid\n"
         "FROM genus_formations gf\n"
         "JOIN taxon t ON gf.genus_id = t.id\n"
         "WHERE gf.formation_id = :formation_id\n"
         "ORDER BY t.name",
         '{"formation_id": "integer"}'),

        # --- Countries / Regions (pc.*) ---
        ("countries_list", "Countries with trilobite occurrences",
         "SELECT gr.id, gr.name, gr.cow_ccode as code,\n"
         "       (SELECT COUNT(DISTINCT gl.genus_id) FROM genus_locations gl\n"
         "        WHERE gl.country_id = gr.id\n"
         "           OR gl.region_id IN (SELECT id FROM pc.geographic_regions WHERE parent_id = gr.id)\n"
         "       ) as taxa_count\n"
         "FROM pc.geographic_regions gr\n"
         "WHERE gr.parent_id IS NULL AND gr.level = 'country'\n"
         "ORDER BY gr.name", None),

        ("country_detail", "Country detail with taxa count",
         "SELECT gr.id, gr.name, gr.cow_ccode,\n"
         "       (SELECT COUNT(DISTINCT gl.genus_id) FROM genus_locations gl\n"
         "        WHERE gl.country_id = gr.id\n"
         "           OR gl.region_id IN (SELECT id FROM pc.geographic_regions WHERE parent_id = gr.id)\n"
         "       ) as taxa_count\n"
         "FROM pc.geographic_regions gr\n"
         "WHERE gr.id = :country_id AND gr.parent_id IS NULL",
         '{"country_id": "integer"}'),

        ("country_regions", "Regions of a country",
         "SELECT gr.id, gr.name, COUNT(DISTINCT gl.genus_id) as taxa_count\n"
         "FROM pc.geographic_regions gr\n"
         "LEFT JOIN genus_locations gl ON gl.region_id = gr.id\n"
         "WHERE gr.parent_id = :country_id AND gr.level = 'region'\n"
         "GROUP BY gr.id ORDER BY taxa_count DESC, gr.name",
         '{"country_id": "integer"}'),

        ("country_genera", "Genera for a country",
         "SELECT DISTINCT t.id, t.name, t.author, t.year, t.is_valid,\n"
         "       gr.name as region, gr.id as region_id\n"
         "FROM genus_locations gl\n"
         "JOIN taxon t ON gl.genus_id = t.id\n"
         "JOIN pc.geographic_regions gr ON gl.region_id = gr.id\n"
         "WHERE gl.region_id = :country_id\n"
         "   OR gl.region_id IN (SELECT id FROM pc.geographic_regions WHERE parent_id = :country_id)\n"
         "ORDER BY t.name",
         '{"country_id": "integer"}'),

        ("regions_list", "All regions with country and taxa count",
         "SELECT gr.id, gr.name, parent.name as country_name, parent.id as country_id,\n"
         "       (SELECT COUNT(DISTINCT gl.genus_id) FROM genus_locations gl\n"
         "        WHERE gl.region_id = gr.id) as taxa_count\n"
         "FROM pc.geographic_regions gr\n"
         "LEFT JOIN pc.geographic_regions parent ON gr.parent_id = parent.id\n"
         "WHERE gr.level = 'region'\n"
         "ORDER BY parent.name, gr.name", None),

        ("region_detail", "Region detail with taxa count",
         "SELECT gr.id, gr.name, gr.level, COUNT(DISTINCT gl.genus_id) as taxa_count,\n"
         "       parent.id as country_id, parent.name as country_name\n"
         "FROM pc.geographic_regions gr\n"
         "LEFT JOIN pc.geographic_regions parent ON gr.parent_id = parent.id\n"
         "LEFT JOIN genus_locations gl ON gl.region_id = gr.id\n"
         "WHERE gr.id = :region_id AND gr.level = 'region'\n"
         "GROUP BY gr.id",
         '{"region_id": "integer"}'),

        ("region_genera", "Genera for a region",
         "SELECT t.id, t.name, t.author, t.year, t.is_valid\n"
         "FROM genus_locations gl\n"
         "JOIN taxon t ON gl.genus_id = t.id\n"
         "WHERE gl.region_id = :region_id\n"
         "ORDER BY t.name",
         '{"region_id": "integer"}'),

        # --- ICS Chronostratigraphy (pc.*) ---
        ("ics_chronostrat_list", "ICS chart",
         "SELECT id, name, rank, parent_id, start_mya, end_mya, color, display_order\n"
         "FROM pc.ics_chronostrat ORDER BY display_order", None),

        ("chronostrat_detail", "Chronostrat unit detail",
         "SELECT ics.id, ics.name, ics.rank, ics.parent_id,\n"
         "       ics.start_mya, ics.start_uncertainty, ics.end_mya, ics.end_uncertainty,\n"
         "       ics.short_code, ics.color, ics.ratified_gssp,\n"
         "       p.id as parent_detail_id, p.name as parent_name, p.rank as parent_rank\n"
         "FROM pc.ics_chronostrat ics\n"
         "LEFT JOIN pc.ics_chronostrat p ON ics.parent_id = p.id\n"
         "WHERE ics.id = :chronostrat_id",
         '{"chronostrat_id": "integer"}'),

        ("chronostrat_children", "Children of a chronostrat unit",
         "SELECT id, name, rank, start_mya, end_mya, color\n"
         "FROM pc.ics_chronostrat WHERE parent_id = :chronostrat_id\n"
         "ORDER BY display_order",
         '{"chronostrat_id": "integer"}'),

        ("chronostrat_mappings", "Temporal code mappings for a chronostrat unit",
         "SELECT temporal_code, mapping_type\n"
         "FROM pc.temporal_ics_mapping WHERE ics_id = :chronostrat_id\n"
         "ORDER BY temporal_code",
         '{"chronostrat_id": "integer"}'),

        ("chronostrat_genera", "Genera mapped to a chronostrat unit",
         "SELECT DISTINCT t.id, t.name, t.author, t.year, t.is_valid, t.temporal_code\n"
         "FROM pc.temporal_ics_mapping m\n"
         "JOIN taxon t ON t.temporal_code = m.temporal_code\n"
         "WHERE m.ics_id = :chronostrat_id AND t.rank = 'Genus'\n"
         "ORDER BY t.name",
         '{"chronostrat_id": "integer"}'),

        # --- Cross-cutting ---
        ("genera_by_country", "Genera by country name",
         "SELECT t.id, t.name, t.author, t.year, gl.region\n"
         "FROM taxon t\n"
         "JOIN genus_locations gl ON t.id = gl.genus_id\n"
         "JOIN pc.geographic_regions c ON gl.country_id = c.id\n"
         "WHERE c.name = :country_name\n"
         "ORDER BY t.name",
         '{"country_name": "text"}'),

        ("genera_by_period", "Genera by temporal code",
         "SELECT id, name, author, year, family, location\n"
         "FROM taxon\n"
         "WHERE rank = 'Genus' AND temporal_code = :temporal_code AND is_valid = 1\n"
         "ORDER BY name",
         '{"temporal_code": "text"}'),

        # --- Classification Profiles ---
        ("profile_list", "All classification profiles",
         "SELECT cp.id, cp.name, cp.description, cp.rule_json,\n"
         "       (SELECT COUNT(*) FROM classification_edge_cache ec WHERE ec.profile_id = cp.id) as edge_count,\n"
         "       cp.created_at\n"
         "FROM classification_profile cp ORDER BY cp.id", None),

        ("profile_detail", "Profile detail with edge statistics",
         "SELECT cp.*,\n"
         "       (SELECT COUNT(*) FROM classification_edge_cache ec WHERE ec.profile_id = cp.id) as edge_count,\n"
         "       (SELECT COUNT(DISTINCT ec.child_id) FROM classification_edge_cache ec\n"
         "        JOIN taxon t ON ec.child_id = t.id\n"
         "        WHERE ec.profile_id = cp.id AND t.rank = 'Order') as order_count,\n"
         "       (SELECT COUNT(DISTINCT ec.child_id) FROM classification_edge_cache ec\n"
         "        JOIN taxon t ON ec.child_id = t.id\n"
         "        WHERE ec.profile_id = cp.id AND t.rank = 'Family') as family_count,\n"
         "       (SELECT COUNT(DISTINCT ec.child_id) FROM classification_edge_cache ec\n"
         "        JOIN taxon t ON ec.child_id = t.id\n"
         "        WHERE ec.profile_id = cp.id AND t.rank = 'Genus') as genus_count\n"
         "FROM classification_profile cp WHERE cp.id = :profile_id",
         '{"profile_id": "integer"}'),

        ("profile_edges", "Edges for a specific profile",
         "SELECT ec.child_id, child.name as child_name, child.rank as child_rank,\n"
         "       ec.parent_id, parent.name as parent_name, parent.rank as parent_rank\n"
         "FROM classification_edge_cache ec\n"
         "JOIN taxon child ON ec.child_id = child.id\n"
         "LEFT JOIN taxon parent ON ec.parent_id = parent.id\n"
         "WHERE ec.profile_id = :profile_id\n"
         "ORDER BY parent.rank, parent.name, child.rank, child.name",
         '{"profile_id": "integer"}'),

        # --- P75: Radial Tree ---
        ("radial_tree_nodes", "Valid taxon nodes for radial tree visualization",
         "SELECT id, name, rank, genera_count, is_valid,\n"
         "       temporal_code, author, year\n"
         "FROM taxon\n"
         "WHERE is_valid = 1 OR rank <> 'Genus'\n"
         "ORDER BY rank, name",
         None),

        ("radial_tree_edges", "Parent-child edges for radial tree (by profile)",
         "SELECT child_id, parent_id\n"
         "FROM classification_edge_cache\n"
         "WHERE profile_id = :profile_id",
         '{"profile_id": "integer"}'),
    ]


# ---------------------------------------------------------------------------
# UI Manifest
# ---------------------------------------------------------------------------

def _build_manifest():
    """Build the full UI manifest dict."""
    return {
        "default_view": "taxonomy_tree",
        "views": {
            # === Tab views ===
            "taxonomy_tree": {
                "type": "hierarchy",
                "display": "tree",
                "title": "Taxonomy Tree",
                "description": "Hierarchical classification derived from assertions (Profile: default)",
                "source_query": "taxonomy_tree",
                "icon": "bi-diagram-3",
                "hierarchy_options": {
                    "id_key": "id", "parent_key": "parent_id", "label_key": "name",
                    "rank_key": "rank", "sort_by": "label", "order_key": "id",
                    "skip_ranks": [],
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
                        {"key": "location", "label": "Location", "truncate": 30},
                    ],
                    "on_item_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    "item_valid_filter": {"key": "is_valid", "label": "Valid only", "default": True},
                },
            },
            "genera_table": {
                "type": "table",
                "title": "All Genera",
                "description": "Flat list of all trilobite genera",
                "source_query": "genera_list",
                "icon": "bi-table",
                "columns": [
                    {"key": "name", "label": "Genus", "sortable": True, "searchable": True, "italic": True},
                    {"key": "author", "label": "Author", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "family", "label": "Family", "sortable": True, "searchable": True},
                    {"key": "temporal_code", "label": "Period", "sortable": True, "searchable": True},
                    {"key": "is_valid", "label": "Valid", "sortable": True, "searchable": False,
                     "type": "boolean", "true_label": "Yes", "false_label": "No"},
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
            },
            "assertion_table": {
                "type": "table",
                "title": "All Assertions",
                "description": "Complete list of taxonomic assertions",
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
                    {"key": "is_accepted", "label": "Accepted", "sortable": True,
                     "type": "boolean", "true_label": "Yes", "false_label": "No"},
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
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "title", "label": "Title", "sortable": False, "searchable": True},
                    {"key": "journal", "label": "Journal", "sortable": True, "searchable": True},
                    {"key": "volume", "label": "Volume", "sortable": False, "searchable": False},
                    {"key": "pages", "label": "Pages", "sortable": False, "searchable": False},
                    {"key": "reference_type", "label": "Type", "sortable": True, "searchable": False},
                ],
                "default_sort": {"key": "authors", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "reference_detail_view", "id_key": "id"},
            },
            "formations_table": {
                "type": "table",
                "title": "Formations",
                "description": "Geological formations where trilobites were found",
                "source_query": "formations_list",
                "icon": "bi-layers",
                "columns": [
                    {"key": "name", "label": "Formation", "sortable": True, "searchable": True},
                    {"key": "formation_type", "label": "Type", "sortable": True, "searchable": False},
                    {"key": "country", "label": "Country", "sortable": True, "searchable": True},
                    {"key": "period", "label": "Period", "sortable": True, "searchable": True},
                    {"key": "taxa_count", "label": "Taxa", "sortable": True, "searchable": False, "type": "number"},
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "formation_detail", "id_key": "id"},
            },
            "countries_table": {
                "type": "table",
                "title": "Countries",
                "description": "Countries with trilobite occurrences",
                "source_query": "countries_list",
                "icon": "bi-globe",
                "columns": [
                    {"key": "name", "label": "Country", "sortable": True, "searchable": True},
                    {"key": "code", "label": "Code", "sortable": True, "searchable": False},
                    {"key": "taxa_count", "label": "Taxa", "sortable": True, "searchable": False, "type": "number"},
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "country_detail", "id_key": "id"},
            },
            "chronostratigraphy_table": {
                "type": "hierarchy",
                "display": "nested_table",
                "title": "Chronostratigraphy",
                "description": "ICS International Chronostratigraphic Chart (GTS 2020)",
                "source_query": "ics_chronostrat_list",
                "icon": "bi-clock-history",
                "columns": [
                    {"key": "name", "label": "Name", "sortable": True, "searchable": True},
                    {"key": "rank", "label": "Rank", "sortable": True, "searchable": True},
                    {"key": "start_mya", "label": "Start (Ma)", "sortable": True, "type": "number"},
                    {"key": "end_mya", "label": "End (Ma)", "sortable": True, "type": "number"},
                    {"key": "color", "label": "Color", "sortable": False, "type": "color"},
                ],
                "default_sort": {"key": "display_order", "direction": "asc"},
                "searchable": True,
                "hierarchy_options": {
                    "id_key": "id", "parent_key": "parent_id", "label_key": "name",
                    "rank_key": "rank", "sort_by": "order_key", "order_key": "display_order",
                    "skip_ranks": ["Super-Eon"],
                },
                "nested_table_display": {
                    "color_key": "color",
                    "rank_columns": [
                        {"rank": "Eon", "label": "Eon"},
                        {"rank": "Era", "label": "Era"},
                        {"rank": "Period", "label": "System / Period"},
                        {"rank": "Sub-Period", "label": "Sub-Period"},
                        {"rank": "Epoch", "label": "Series / Epoch"},
                        {"rank": "Age", "label": "Stage / Age"},
                    ],
                    "value_column": {"key": "start_mya", "label": "Age (Ma)"},
                    "cell_click": {"detail_view": "chronostrat_detail", "id_key": "id"},
                },
            },
            "profiles_table": {
                "type": "table",
                "title": "Classification Profiles",
                "description": "Named classification profiles for building different taxonomy trees",
                "source_query": "profile_list",
                "icon": "bi-sliders",
                "columns": [
                    {"key": "name", "label": "Profile", "sortable": True, "searchable": True},
                    {"key": "description", "label": "Description", "sortable": False, "searchable": True},
                    {"key": "edge_count", "label": "Edges", "sortable": True, "type": "number"},
                    {"key": "created_at", "label": "Created", "sortable": True},
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "on_row_click": {"detail_view": "profile_detail_view", "id_key": "id"},
            },

            # === Detail views ===
            "taxon_detail_view": {
                "type": "detail",
                "title": "Taxon Detail",
                "source_query": "taxon_detail",
                "source_param": "taxon_id",
                "redirect": {
                    "key": "rank",
                    "map": {"Genus": "genus_detail"},
                },
                "sub_queries": {
                    "children_counts": {"query": "taxon_children_counts", "params": {"taxon_id": "id"}},
                    "children": {"query": "taxon_children", "params": {"taxon_id": "id"}},
                    "assertions": {"query": "taxon_assertions", "params": {"taxon_id": "id"}},
                },
                "title_template": {"format": '<span class="badge bg-secondary me-2">{rank}</span> {name}'},
                "sections": [
                    {
                        "title": "Basic Information",
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
                        ],
                    },
                    {"title": "Statistics", "type": "rank_statistics"},
                    {
                        "title": "Children ({count})",
                        "type": "linked_table",
                        "data_key": "children",
                        "condition": "children",
                        "columns": [
                            {"key": "name", "label": "Name"},
                            {"key": "rank", "label": "Rank"},
                            {"key": "author", "label": "Author"},
                            {"key": "genera_count", "label": "Genera", "condition": "genera_count"},
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
                            {"key": "object_name", "label": "Object",
                             "label_map": {"key": "predicate", "map": {
                                 "PLACED_IN": "Parent", "SYNONYM_OF": "Valid Name",
                                 "SPELLING_OF": "Correct Spelling"}}},
                            {"key": "ref_authors", "label": "Reference"},
                            {"key": "ref_year", "label": "Year"},
                            {"key": "assertion_status", "label": "Status"},
                            {"key": "is_accepted", "label": "Accepted", "format": "boolean"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "object_taxon_id"},
                    },
                    {"title": "Notes", "type": "raw_text", "data_key": "notes",
                     "condition": "notes", "format": "paragraph"},
                    {"title": "My Notes", "type": "annotations", "entity_type_from": "rank"},
                ],
            },
            "genus_detail": {
                "type": "detail",
                "title": "Genus Detail",
                "source_query": "taxon_detail",
                "source_param": "taxon_id",
                "title_template": {"format": "<i>{name}</i> {author}, {year}"},
                "sub_queries": {
                    "hierarchy": {"query": "genus_hierarchy", "params": {"taxon_id": "id"}},
                    "locations": {"query": "genus_locations", "params": {"taxon_id": "id"}},
                    "formations": {"query": "genus_formations", "params": {"taxon_id": "id"}},
                    "bibliography": {"query": "genus_bibliography", "params": {"taxon_id": "id"}},
                    "ics_mapping": {"query": "genus_ics_mapping", "params": {"temporal_code": "temporal_code"}},
                    "synonyms": {"query": "genus_synonyms", "params": {"taxon_id": "id"}},
                    "assertions": {"query": "taxon_assertions", "params": {"taxon_id": "id"}},
                },
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name", "format": "italic"},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year", "suffix_key": "year_suffix"},
                            {"key": "hierarchy", "label": "Classification", "format": "hierarchy",
                             "data_key": "hierarchy",
                             "link": {"detail_view": "taxon_detail_view"}},
                            {"key": "is_valid", "label": "Status", "format": "boolean",
                             "true_label": "Valid", "false_label": "Invalid", "false_class": "invalid"},
                            {"key": "temporal_code", "label": "Temporal Range",
                             "format": "temporal_range", "mapping_key": "ics_mapping",
                             "link": {"detail_view": "chronostrat_detail"}},
                        ],
                    },
                    {
                        "title": "Type Species",
                        "type": "field_grid",
                        "condition": "type_species",
                        "fields": [
                            {"key": "type_species", "label": "Species", "format": "italic"},
                            {"key": "type_species_author", "label": "Author"},
                        ],
                    },
                    {
                        "title": "Locations ({count})",
                        "type": "linked_table",
                        "data_key": "locations",
                        "condition": "locations",
                        "columns": [
                            {"key": "country_name", "label": "Country",
                             "link": {"detail_view": "country_detail", "id_key": "country_id"}},
                            {"key": "region_name", "label": "Region",
                             "link": {"detail_view": "region_detail", "id_key": "region_id"}},
                        ],
                    },
                    {
                        "title": "Formations ({count})",
                        "type": "linked_table",
                        "data_key": "formations",
                        "condition": "formations",
                        "columns": [
                            {"key": "name", "label": "Formation",
                             "link": {"detail_view": "formation_detail", "id_key": "id"}},
                            {"key": "period", "label": "Period"},
                        ],
                    },
                    {
                        "title": "Bibliography ({count})",
                        "type": "linked_table",
                        "data_key": "bibliography",
                        "condition": "bibliography",
                        "columns": [
                            {"key": "authors", "label": "Authors"},
                            {"key": "year", "label": "Year"},
                            {"key": "title", "label": "Title", "truncate": 60},
                            {"key": "relationship_type", "label": "Relation"},
                        ],
                        "on_row_click": {"detail_view": "reference_detail_view", "id_key": "id"},
                    },
                    {
                        "title": "Synonymy",
                        "type": "linked_table",
                        "data_key": "synonyms",
                        "condition": "synonyms",
                        "columns": [
                            {"key": "synonym_type", "label": "Type"},
                            {"key": "senior_name", "label": "Senior Synonym",
                             "link": {"detail_view": "genus_detail", "id_key": "senior_taxon_id"}},
                            {"key": "fide_author", "label": "Fide"},
                            {"key": "fide_year", "label": "Year"},
                        ],
                    },
                    {
                        "title": "Assertions ({count})",
                        "type": "linked_table",
                        "data_key": "assertions",
                        "condition": "assertions",
                        "columns": [
                            {"key": "predicate", "label": "Type"},
                            {"key": "object_name", "label": "Object",
                             "label_map": {"key": "predicate", "map": {
                                 "PLACED_IN": "Parent", "SYNONYM_OF": "Valid Name",
                                 "SPELLING_OF": "Correct Spelling"}}},
                            {"key": "ref_authors", "label": "Reference"},
                            {"key": "ref_year", "label": "Year"},
                            {"key": "assertion_status", "label": "Status"},
                            {"key": "is_accepted", "label": "Accepted", "format": "boolean"},
                        ],
                    },
                    {"title": "Notes", "type": "raw_text", "data_key": "notes",
                     "condition": "notes", "format": "paragraph"},
                    {"title": "Original Entry", "type": "raw_text", "data_key": "raw_entry",
                     "condition": "raw_entry"},
                    {"title": "My Notes", "type": "annotations", "entity_type": "genus"},
                ],
            },
            "reference_detail_view": {
                "type": "detail",
                "title": "Reference Detail",
                "source_query": "reference_detail",
                "source_param": "ref_id",
                "sub_queries": {
                    "assertions": {"query": "reference_assertions", "params": {"ref_id": "id"}},
                    "genera": {"query": "reference_genera", "params": {"ref_id": "id"}},
                },
                "icon": "bi-book",
                "title_template": {"format": "{icon} {authors}, {year}", "icon": "bi-book"},
                "sections": [
                    {
                        "title": "Reference Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "authors", "label": "Authors"},
                            {"key": "year", "label": "Year", "suffix_key": "year_suffix"},
                            {"key": "title", "label": "Title"},
                            {"key": "journal", "label": "Journal"},
                            {"key": "volume", "label": "Volume"},
                            {"key": "pages", "label": "Pages"},
                            {"key": "reference_type", "label": "Type"},
                            {"key": "publisher", "label": "Publisher", "condition": "publisher"},
                            {"key": "city", "label": "City", "condition": "city"},
                            {"key": "editors", "label": "Editors", "condition": "editors"},
                            {"key": "book_title", "label": "Book Title", "condition": "book_title"},
                        ],
                    },
                    {"title": "Original Entry", "type": "raw_text",
                     "data_key": "raw_entry", "condition": "raw_entry"},
                    {
                        "title": "Related Genera ({count})",
                        "type": "linked_table",
                        "data_key": "genera",
                        "show_empty": True,
                        "empty_message": "No matching genera found.",
                        "columns": [
                            {"key": "name", "label": "Genus", "italic": True},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "is_valid", "label": "Valid", "format": "boolean",
                             "true_label": "Yes", "false_label": "No"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                    {
                        "title": "Citing Assertions ({count})",
                        "type": "linked_table",
                        "data_key": "assertions",
                        "condition": "assertions",
                        "columns": [
                            {"key": "predicate", "label": "Type"},
                            {"key": "subject_name", "label": "Subject"},
                            {"key": "subject_rank", "label": "Rank"},
                            {"key": "object_name", "label": "Object"},
                            {"key": "assertion_status", "label": "Status"},
                            {"key": "is_accepted", "label": "Accepted", "format": "boolean"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "subject_taxon_id"},
                    },
                ],
            },
            "formation_detail": {
                "type": "detail",
                "title": "Formation Detail",
                "source_query": "formation_detail",
                "source_param": "formation_id",
                "sub_queries": {
                    "genera": {"query": "formation_genera", "params": {"formation_id": "id"}},
                },
                "icon": "bi-layers",
                "title_template": {"format": "{icon} {name}", "icon": "bi-layers"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "formation_type", "label": "Type"},
                            {"key": "country", "label": "Country"},
                            {"key": "region", "label": "Region"},
                            {"key": "period", "label": "Period"},
                            {"key": "taxa_count", "label": "Taxa Count"},
                        ],
                    },
                    {
                        "title": "Genera ({count})",
                        "type": "linked_table",
                        "data_key": "genera",
                        "columns": [
                            {"key": "name", "label": "Genus", "italic": True},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "is_valid", "label": "Valid", "format": "boolean",
                             "true_label": "Yes", "false_label": "No"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                ],
            },
            "country_detail": {
                "type": "detail",
                "title": "Country Detail",
                "source_query": "country_detail",
                "source_param": "country_id",
                "sub_queries": {
                    "regions": {"query": "country_regions", "params": {"country_id": "id"}},
                    "genera": {"query": "country_genera", "params": {"country_id": "id"}},
                },
                "icon": "bi-geo-alt",
                "title_template": {"format": "{icon} {name}", "icon": "bi-geo-alt"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "cow_ccode", "label": "COW Code"},
                            {"key": "taxa_count", "label": "Taxa Count"},
                        ],
                    },
                    {
                        "title": "Regions ({count})",
                        "type": "linked_table",
                        "data_key": "regions",
                        "condition": "regions",
                        "columns": [
                            {"key": "name", "label": "Region"},
                            {"key": "taxa_count", "label": "Taxa Count"},
                        ],
                        "on_row_click": {"detail_view": "region_detail", "id_key": "id"},
                    },
                    {
                        "title": "Genera ({count})",
                        "type": "linked_table",
                        "data_key": "genera",
                        "condition": "genera",
                        "columns": [
                            {"key": "name", "label": "Genus", "italic": True},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "region", "label": "Region",
                             "link": {"detail_view": "region_detail", "id_key": "region_id"}},
                            {"key": "is_valid", "label": "Valid", "format": "boolean",
                             "true_label": "Yes", "false_label": "No"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                ],
            },
            "region_detail": {
                "type": "detail",
                "title": "Region Detail",
                "source_query": "region_detail",
                "source_param": "region_id",
                "sub_queries": {
                    "genera": {"query": "region_genera", "params": {"region_id": "id"}},
                },
                "icon": "bi-geo-alt",
                "title_template": {"format": "{icon} {name}", "icon": "bi-geo-alt"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "country_name", "label": "Country", "format": "link",
                             "link": {"detail_view": "country_detail", "id_path": "country_id"}},
                            {"key": "taxa_count", "label": "Taxa Count"},
                        ],
                    },
                    {
                        "title": "Genera ({count})",
                        "type": "linked_table",
                        "data_key": "genera",
                        "condition": "genera",
                        "columns": [
                            {"key": "name", "label": "Genus", "italic": True},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "is_valid", "label": "Valid", "format": "boolean",
                             "true_label": "Yes", "false_label": "No"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                ],
            },
            "chronostrat_detail": {
                "type": "detail",
                "title": "Chronostratigraphy Detail",
                "source_query": "chronostrat_detail",
                "source_param": "chronostrat_id",
                "sub_queries": {
                    "children": {"query": "chronostrat_children", "params": {"chronostrat_id": "id"}},
                    "mappings": {"query": "chronostrat_mappings", "params": {"chronostrat_id": "id"}},
                    "genera": {"query": "chronostrat_genera", "params": {"chronostrat_id": "id"}},
                },
                "icon": "bi-clock-history",
                "title_template": {"format": "{icon} {name}", "icon": "bi-clock-history"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "rank", "label": "Rank"},
                            {"key": "_time_range", "label": "Time Range",
                             "format": "computed", "compute": "time_range"},
                            {"key": "short_code", "label": "Short Code"},
                            {"key": "color", "label": "Color", "format": "color_chip"},
                            {"key": "ratified_gssp", "label": "Ratified GSSP", "format": "boolean"},
                        ],
                    },
                    {
                        "title": "Hierarchy",
                        "type": "field_grid",
                        "condition": "parent_name",
                        "fields": [
                            {"key": "parent_name", "label": "Parent", "format": "link",
                             "link": {"detail_view": "chronostrat_detail", "id_path": "parent_detail_id"},
                             "suffix_key": "parent_rank", "suffix_format": "({value})"},
                        ],
                    },
                    {
                        "title": "Children ({count})",
                        "type": "linked_table",
                        "data_key": "children",
                        "condition": "children",
                        "columns": [
                            {"key": "name", "label": "Name"},
                            {"key": "rank", "label": "Rank"},
                            {"key": "_time_range", "label": "Time Range",
                             "format": "computed", "compute": "time_range"},
                            {"key": "color", "label": "Color", "format": "color_chip"},
                        ],
                        "on_row_click": {"detail_view": "chronostrat_detail", "id_key": "id"},
                    },
                    {
                        "title": "Mapped Temporal Codes",
                        "type": "tagged_list",
                        "data_key": "mappings",
                        "condition": "mappings",
                        "badge_key": "temporal_code",
                        "badge_format": "code",
                        "text_key": "mapping_type",
                    },
                    {
                        "title": "Related Genera ({count})",
                        "type": "linked_table",
                        "data_key": "genera",
                        "condition": "genera",
                        "columns": [
                            {"key": "name", "label": "Genus", "italic": True},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "temporal_code", "label": "Temporal Code", "format": "code"},
                            {"key": "is_valid", "label": "Valid", "format": "boolean",
                             "true_label": "Yes", "false_label": "No"},
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    },
                ],
            },
            "profile_detail_view": {
                "type": "detail",
                "title": "Profile Detail",
                "source_query": "profile_detail",
                "source_param": "profile_id",
                "sub_queries": {
                    "edges": {"query": "profile_edges", "params": {"profile_id": "id"}},
                },
                "icon": "bi-sliders",
                "title_template": {"format": "{icon} Profile: {name}", "icon": "bi-sliders"},
                "sections": [
                    {
                        "title": "Profile Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "description", "label": "Description"},
                            {"key": "rule_json", "label": "Rule (JSON)", "format": "code"},
                            {"key": "edge_count", "label": "Total Edges"},
                            {"key": "order_count", "label": "Orders"},
                            {"key": "family_count", "label": "Families"},
                            {"key": "genus_count", "label": "Genera"},
                        ],
                    },
                    {
                        "title": "Edges ({count})",
                        "type": "linked_table",
                        "data_key": "edges",
                        "condition": "edges",
                        "columns": [
                            {"key": "child_name", "label": "Child"},
                            {"key": "child_rank", "label": "Rank"},
                            {"key": "parent_name", "label": "Parent"},
                            {"key": "parent_rank", "label": "Parent Rank"},
                        ],
                    },
                ],
            },
            # === P75: Radial Tree ===
            "radial_tree": {
                "type": "hierarchy",
                "display": "radial",
                "title": "Radial Tree",
                "description": "Radial taxonomy visualization — Class at center, genera at periphery",
                "icon": "bi-bullseye",
                "source_query": "radial_tree_nodes",
                "hierarchy_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "rank_key": "rank",
                },
                "radial_display": {
                    "edge_query": "radial_tree_edges",
                    "edge_params": {"profile_id": 1},
                    "color_key": "rank",
                    "count_key": "genera_count",
                    "depth_toggle": True,
                    "leaf_rank": "Genus",
                    "on_node_click": {"detail_view": "taxon_detail_view", "id_key": "id"},
                    "rank_radius": {
                        "_root": 0,
                        "Class": 0.08,
                        "Order": 0.20,
                        "Suborder": 0.32,
                        "Superfamily": 0.44,
                        "Family": 0.56,
                        "Subfamily": 0.70,
                        "Genus": 1.0,
                    },
                },
            },
        },
    }


def create_views(cur: sqlite3.Cursor) -> None:
    """Create compatibility views."""
    cur.executescript("""
    -- Full tree derived from assertions
    CREATE VIEW v_taxonomy_tree AS
    WITH RECURSIVE tree AS (
        SELECT t.id, t.name, t.rank, NULL AS parent_id, 0 AS depth
        FROM taxon t
        WHERE t.rank = 'Class'
        UNION ALL
        SELECT t.id, t.name, t.rank, a.object_taxon_id, tree.depth + 1
        FROM taxon t
        JOIN assertion a ON a.subject_taxon_id = t.id
            AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1
        JOIN tree ON a.object_taxon_id = tree.id
    )
    SELECT * FROM tree;

    -- taxonomic_ranks compatibility view
    CREATE VIEW v_taxonomic_ranks AS
    SELECT t.*,
           (SELECT a.object_taxon_id FROM assertion a
            WHERE a.subject_taxon_id = t.id
              AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1
            LIMIT 1) AS parent_id
    FROM taxon t;

    -- synonyms compatibility view
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


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_hub_manifest(db_path: Path, version: str) -> Path:
    """Generate Hub Manifest JSON alongside the assertion DB."""
    manifest = {
        "hub_manifest_version": "1.0",
        "package_id": "trilobase-assertion",
        "version": version,
        "title": "Trilobase (Assertion-Centric) — experimental P74 model",
        "description": "Assertion-centric trilobite taxonomy database",
        "license": "CC-BY-4.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": [
            "Jell, P.A., and Adrain, J.M., 2002, Available Generic Names for Trilobites",
            "Adrain, J.M., 2011, Class Trilobita Walch, 1771",
        ],
        "filename": db_path.name,
        "sha256": _sha256_file(db_path),
        "size_bytes": db_path.stat().st_size,
    }

    out_path = db_path.parent / f"trilobase-assertion-{version}.manifest.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"  Hub Manifest: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="P74 — Assertion-centric test DB builder")
    parser.add_argument(
        "--version", default=ASSERTION_VERSION,
        help=f"Version string (default: {ASSERTION_VERSION})")
    args = parser.parse_args()

    version = args.version

    if not SRC_DB.exists():
        print(f"ERROR: Source DB not found: {SRC_DB}", file=sys.stderr)
        sys.exit(1)

    DST_DIR.mkdir(parents=True, exist_ok=True)
    dst_db = DST_DIR / f"trilobase-assertion-{version}.db"
    if dst_db.exists():
        dst_db.unlink()

    src = sqlite3.connect(str(SRC_DB))
    dst = sqlite3.connect(str(dst_db))
    dst.execute("PRAGMA journal_mode=WAL")
    dst.execute("PRAGMA foreign_keys=ON")

    print(f"=== P74: Assertion-Centric Test DB Builder (v{version}) ===\n")

    # 1. Schema
    print("1. Creating schema...")
    create_schema(dst.cursor())
    dst.commit()

    # 2. Copy taxon
    print("2. Copying taxon data...")
    n_taxon = copy_taxon(src, dst)
    dst.commit()
    print(f"   → {n_taxon} taxon records")

    # 3. Copy reference
    print("3. Copying reference data...")
    n_ref = copy_reference(src, dst)
    dst.commit()
    print(f"   → {n_ref} reference records (incl. JA2002)")

    # 4. Convert existing opinions
    print("4. Converting existing opinions → assertions...")
    opinion_counts = convert_opinions(src, dst)
    dst.commit()
    for k, v in opinion_counts.items():
        print(f"   → {k}: {v}")

    # 5. Generate PLACED_IN from parent_id
    print("5. Generating PLACED_IN assertions from parent_id...")
    n_placed = generate_placed_in(src, dst)
    dst.commit()
    print(f"   → {n_placed} new PLACED_IN assertions")

    # 6. Classification profiles
    print("6. Creating classification profiles...")
    create_profiles(dst)
    dst.commit()

    # 7. Edge cache
    print("7. Building edge cache (default profile)...")
    n_edges = build_edge_cache(dst)
    dst.commit()
    print(f"   → {n_edges} edges cached")

    # 8. Junction tables
    print("8. Copying junction tables...")
    jcounts = copy_junction_tables(src, dst)
    dst.commit()
    for tbl, cnt in jcounts.items():
        print(f"   → {tbl}: {cnt}")

    # 9. Views
    print("9. Creating compatibility views...")
    create_views(dst.cursor())
    dst.commit()

    # 10. SCODA metadata
    print("10. Creating SCODA metadata...")
    create_scoda_metadata(dst, version=version)
    n_queries = dst.execute("SELECT COUNT(*) FROM ui_queries").fetchone()[0]
    print(f"   → {n_queries} ui_queries, 1 ui_manifest, 3 provenance")

    # Summary
    total_assertions = dst.execute("SELECT COUNT(*) FROM assertion").fetchone()[0]
    accepted_placed = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='PLACED_IN' AND is_accepted=1"
    ).fetchone()[0]

    print(f"\n=== Summary ===")
    print(f"  taxon:          {n_taxon}")
    print(f"  reference:      {n_ref}")
    print(f"  assertion:      {total_assertions}")
    print(f"    PLACED_IN(accepted): {accepted_placed}")
    print(f"    SYNONYM_OF:  {opinion_counts.get('SYNONYM_OF', 0)}")
    print(f"    SPELLING_OF: {opinion_counts.get('SPELLING_OF', 0)}")
    print(f"  edge_cache:     {n_edges}")
    print(f"\nOutput: {dst_db}")

    src.close()
    dst.close()

    # 11. Hub Manifest
    print("\n11. Generating Hub Manifest...")
    generate_hub_manifest(dst_db, version)


if __name__ == "__main__":
    main()
