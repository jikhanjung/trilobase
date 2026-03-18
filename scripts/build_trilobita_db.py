#!/usr/bin/env python3
"""Build trilobita DB from data/sources/*.txt (R04 extended format).

Reads:
  - data/sources/jell_adrain_2002.txt      → genera, families, synonyms (default profile)
  - data/sources/adrain_2011.txt           → suprafamilial hierarchy (default profile)
  - data/sources/treatise_1959.txt         → full hierarchy (treatise1959 profile)
  - data/sources/treatise_1997_ch4.txt     → Agnostida (treatise1997 profile)
  - data/sources/treatise_1997_ch5.txt     → Redlichiida (treatise1997 profile)

Still copies from canonical DB:
  - taxon metadata (formation, location, temporal_code, type_species, etc.)
  - reference/bibliography
  - genus_formations, genus_locations, taxon_reference

Usage:
    python scripts/build_trilobita_db.py [--version 0.3.0]
"""

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from db_path import find_canonical_db, find_paleocore_db

ASSERTION_VERSION = "0.3.3"

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"
SRC_DB = Path(find_canonical_db())
DST_DIR = ROOT / "db"

# Well-known IDs — set at runtime
ADRAIN_2011_BIB_ID = 2131  # bibliography id in canonical DB
JA2002_REF_ID = None  # set after insert
TREATISE_1959_REF_ID = None
TREATISE_1997_CH4_REF_ID = None
TREATISE_1997_CH5_REF_ID = None


# ---------------------------------------------------------------------------
# Source file parser
# ---------------------------------------------------------------------------

def parse_source_header(text: str):
    """Parse YAML-like header from a source file. Returns (header_dict, body_str)."""
    if not text.startswith("---"):
        return {}, text

    end = text.index("---", 3)
    header_text = text[3:end].strip()
    body = text[end + 3:].strip()

    header = {}
    # Parse reference line
    m = re.search(r'^reference:\s*(.+)$', header_text, re.MULTILINE)
    if m:
        header["reference"] = m.group(1).strip()

    # Parse scope blocks
    scopes = []
    for sm in re.finditer(
        r'-\s+taxon:\s*(\S+)\s+coverage:\s*(\S+)', header_text
    ):
        scopes.append({"taxon": sm.group(1), "coverage": sm.group(2)})
    header["scope"] = scopes

    return header, body


RANK_KEYWORDS = {"Order", "Suborder", "Superfamily", "Family", "Subfamily"}
RANK_ORDER = {"Phylum": 0, "Class": 1, "Order": 2, "Suborder": 3, "Superfamily": 4,
              "Family": 5, "Subfamily": 6, "Genus": 7}


def parse_hierarchy_body(body: str, default_leaf_rank="Genus"):
    """Parse hierarchy body into list of placement records.

    Uses a hybrid strategy:
    - For taxa with explicit rank keywords (Order, Family, etc.): parent is
      determined by rank hierarchy (find nearest ancestor with higher rank),
      regardless of indentation.
    - For taxa without rank keywords (default_leaf_rank, typically Genus):
      parent is the most recent taxon with a higher rank on the stack.

    This makes parsing robust against mixed tabs/spaces in source files.

    Returns list of dicts:
      {"name", "rank", "author", "year", "parent_name", "parent_rank",
       "status", "synonyms": [...]}
    """
    placements = []
    # Stack: [(rank_order, name, rank)]  — ordered by nesting depth
    stack = []

    for raw_line in body.splitlines():
        # Skip empty lines and comments
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Handle synonym lines (= or ~)
        syn_match = re.match(r'^\s*(=|~)\s+(.+)$', stripped)
        if syn_match and placements:
            marker = syn_match.group(1)
            syn_text = syn_match.group(2).strip()
            predicate = "SYNONYM_OF" if marker == "=" else "SPELLING_OF"
            # Parse: "Target (j.s.s., fide AUTHOR, YEAR)"
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

        # Determine status from markers
        status = "asserted"
        line = stripped

        # ? prefix = questionable
        if line.startswith("?"):
            status = "questionable"
            line = line[1:].strip()

        # [incertae sedis] suffix
        if "[incertae sedis]" in line:
            status = "incertae_sedis"
            line = line.replace("[incertae sedis]", "").strip()

        # Determine rank from keyword prefix
        rank = None
        has_explicit_rank = False

        # Special case: compound rank headers like "Order and Family UNCERTAIN",
        # "Superfamily and Family UNCERTAIN", "Order, Suborder, and Family UNCERTAIN"
        compound_m = re.match(
            r'^(Order|Suborder|Superfamily|Family|Subfamily)'
            r'(?:,\s*(?:Order|Suborder|Superfamily|Family|Subfamily))*'
            r',?\s+and\s+(?:Order|Suborder|Superfamily|Family|Subfamily)'
            r'\s+UNCERTAIN$',
            line, re.IGNORECASE
        )
        compound_rank_name = None
        if compound_m:
            rank = compound_m.group(1)  # use the highest (first) rank
            has_explicit_rank = True
            # Use entire header as the taxon name (e.g. "Order and family uncertain")
            compound_rank_name = line[0] + line[1:].lower()
        else:
            for kw in RANK_KEYWORDS:
                if line.startswith(kw + " "):
                    rank = kw
                    has_explicit_rank = True
                    line = line[len(kw):].strip()
                    break

        if rank is None:
            rank = default_leaf_rank

        # Parse name and authority: "Agnostus Brongniart, 1822 [type species...]"
        # Remove [...] blocks (type species, notes)
        clean = re.sub(r'\[.*?\]', '', line).strip()
        # Remove | separated fields (JA2002 format)
        clean = clean.split("|")[0].strip()

        # Extract name and authority
        if compound_rank_name:
            name = compound_rank_name
            authority_str = ""
        else:
            parts = clean.split(None, 1)
            if not parts:
                continue
            name = parts[0].strip()
            authority_str = parts[1].strip() if len(parts) > 1 else ""

        # Normalize casing: ALL CAPS family/subfamily names → title case
        # e.g., CYCLOPAGNOSTIDAE → Cyclopagnostidae, OLENELLINAE → Olenellinae
        if rank in ("Family", "Subfamily", "Superfamily", "Suborder") and name == name.upper() and len(name) > 1:
            name = name[0] + name[1:].lower()

        # Parse author, year from authority
        author = ""
        year = ""
        if authority_str:
            # Match "AUTHOR, YEAR" or "AUTHOR & AUTHOR, YEAR" etc.
            ym = re.search(r',?\s*(\d{4}[a-z]?)\s*$', authority_str)
            if ym:
                year = ym.group(1)
                author = authority_str[:ym.start()].strip().rstrip(",")
            else:
                author = authority_str

        # Determine parent using rank hierarchy
        cur_order = RANK_ORDER.get(rank, 6)

        # Pop stack to find parent: nearest ancestor with strictly higher rank
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
            CHECK(rank IN ('Phylum','Class','Order','Suborder','Superfamily','Family','Subfamily','Genus')),
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


# ---------------------------------------------------------------------------
# Phase 1: Copy taxon from canonical DB
# ---------------------------------------------------------------------------

def copy_taxon(src, dst):
    """Copy all taxa from canonical DB, preserving IDs and metadata."""
    rows = src.execute("""
        SELECT id, name, rank, author, year, year_suffix, notes,
               is_placeholder, type_species, type_species_author,
               formation, location, family, temporal_code, is_valid,
               raw_entry, created_at
        FROM taxonomic_ranks
    """).fetchall()
    dst.executemany("""
        INSERT INTO taxon (id, name, rank, author, year, year_suffix, notes,
                           is_placeholder, type_species, type_species_author,
                           formation, location, family, temporal_code, is_valid,
                           raw_entry, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    # Fix UCAMB → UCAM typo (Cyclagnostus)
    dst.execute("UPDATE taxon SET temporal_code = 'UCAM' WHERE temporal_code = 'UCAMB'")
    return len(rows)


# ---------------------------------------------------------------------------
# Phase 2: Copy references + insert source references
# ---------------------------------------------------------------------------

def copy_references(src, dst):
    """Copy bibliography from canonical DB and insert source-specific references."""
    global JA2002_REF_ID, TREATISE_1959_REF_ID
    global TREATISE_1997_CH4_REF_ID, TREATISE_1997_CH5_REF_ID

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

    # Update Adrain 2011 with correct bibliographic details
    dst.execute("""
        UPDATE reference SET
            title = ?, journal = ?, volume = ?, pages = ?,
            editors = ?, book_title = ?, reference_type = ?, raw_entry = ?
        WHERE id = ?
    """, (
        "Class Trilobita Walch, 1771",
        "Zootaxa", "3148", "104",
        "Zhang, Z.-Q.",
        "Animal biodiversity: An outline of higher-level classification "
        "and survey of taxonomic richness",
        "incollection",
        "Adrain, J.M., 2011, Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) "
        "Animal biodiversity: An outline of higher-level classification and survey "
        "of taxonomic richness: Zootaxa, v. 3148, p. 104.",
        ADRAIN_2011_BIB_ID,
    ))

    # Insert Jell & Adrain 2002
    cur = dst.execute("""
        INSERT INTO reference (authors, year, title, journal, volume, pages,
                               reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "JELL, P.A. & ADRAIN, J.M.", 2002,
        "Available Generic Names for Trilobites",
        "Memoirs of the Queensland Museum", "48", "331-553",
        "article",
        "Jell, P.A., and Adrain, J.M., 2002, Available Generic Names for Trilobites: "
        "Memoirs of the Queensland Museum, v. 48, p. 331-553.",
    ))
    JA2002_REF_ID = cur.lastrowid

    # Insert Treatise 1959
    cur = dst.execute("""
        INSERT INTO reference (authors, year, title, publisher,
                               reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "MOORE, R.C. (Ed.)", 1959,
        "Treatise on Invertebrate Paleontology, Part O, Arthropoda 1, Trilobita",
        "Geological Society of America & University of Kansas Press",
        "book",
        "Moore, R.C. (Ed.), 1959, Treatise on Invertebrate Paleontology, "
        "Part O, Arthropoda 1, Trilobita.",
    ))
    TREATISE_1959_REF_ID = cur.lastrowid

    # Insert Treatise 1997 ch4
    cur = dst.execute("""
        INSERT INTO reference (authors, year, title, editors, book_title,
                               reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "SHERGOLD, J.H., LAURIE, J.R. & SUN, X.", 1997,
        "Classification of the Agnostida",
        "Kaesler, R.L.",
        "Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1",
        "incollection",
        "Shergold, J.H., Laurie, J.R. & Sun, X., 1997, Classification of the Agnostida. "
        "In: Kaesler, R.L. (Ed.), Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1, Ch. 4.",
    ))
    TREATISE_1997_CH4_REF_ID = cur.lastrowid

    # Insert Treatise 1997 ch5
    cur = dst.execute("""
        INSERT INTO reference (authors, year, title, editors, book_title,
                               reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "PALMER, A.R. & REPINA, L.N.", 1997,
        "Classification of the Redlichiida",
        "Kaesler, R.L.",
        "Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1",
        "incollection",
        "Palmer, A.R. & Repina, L.N., 1997, Classification of the Redlichiida. "
        "In: Kaesler, R.L. (Ed.), Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1, Ch. 5.",
    ))
    TREATISE_1997_CH5_REF_ID = cur.lastrowid

    return len(rows) + 4  # bibliography + 4 source refs


# ---------------------------------------------------------------------------
# Phase 3: Parse sources and generate assertions
# ---------------------------------------------------------------------------

def build_taxon_index(dst):
    """Build name→id index for existing taxa. Returns {(name_lower, rank_lower): id}."""
    rows = dst.execute("SELECT id, name, rank FROM taxon").fetchall()
    index = {}
    for tid, name, rank in rows:
        index[(name.lower(), rank.lower())] = tid
    # Also index by name only (for genus lookups where rank is implied)
    name_only = {}
    for tid, name, rank in rows:
        key = name.lower()
        if key not in name_only:
            name_only[key] = (tid, rank)
    return index, name_only


def resolve_taxon(name, rank, dst, taxon_index, name_index, new_taxa_cache):
    """Resolve a taxon name+rank to an id, creating if needed."""
    key = (name.lower(), rank.lower())
    if key in taxon_index:
        return taxon_index[key]

    # Check cache of newly created taxa
    if key in new_taxa_cache:
        return new_taxa_cache[key]

    # Try name-only match (different rank — might be a rank change)
    name_key = name.lower()
    if name_key in name_index:
        existing_id, existing_rank = name_index[name_key]
        # If same name exists with a compatible rank, reuse it
        # e.g., "Uncertain" containers
        if existing_rank.lower() == rank.lower():
            taxon_index[key] = existing_id
            return existing_id

    # Create new taxon
    is_placeholder = 1 if name.lower() in ("uncertain", "unrecognizable") else 0
    cur = dst.execute("""
        INSERT INTO taxon (name, rank, is_placeholder, is_valid, created_at)
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
    """, (name, rank, is_placeholder))
    new_id = cur.lastrowid
    taxon_index[key] = new_id
    new_taxa_cache[key] = new_id
    name_index.setdefault(name.lower(), (new_id, rank))
    return new_id


def process_source_default(dst, taxon_index, name_index, new_taxa_cache):
    """Process JA2002 + Adrain 2011 to generate default profile assertions.

    Returns (counts_dict, default_edges) where default_edges is
    list of (child_id, parent_id) for the default profile.
    """
    counts = {"PLACED_IN": 0, "SYNONYM_OF": 0, "SPELLING_OF": 0}
    default_edges = []  # (child_id, parent_id) for default profile
    placed_children = set()  # track which children already have a default placement

    # --- Phylum Arthropoda (root of trilobita hierarchy) ---
    arthropoda_id = resolve_taxon(
        "Arthropoda", "Phylum", dst, taxon_index, name_index, new_taxa_cache)

    # --- Adrain 2011: suprafamilial hierarchy ---
    adrain_text = (SOURCES / "adrain_2011.txt").read_text(encoding="utf-8")
    _, adrain_body = parse_source_header(adrain_text)
    adrain_placements = parse_hierarchy_body(adrain_body, default_leaf_rank="Family")

    # Resolve Trilobita (Class) as root for Orders
    trilobita_id = resolve_taxon(
        "Trilobita", "Class", dst, taxon_index, name_index, new_taxa_cache)

    # Place Trilobita under Arthropoda
    default_edges.append((trilobita_id, arthropoda_id))
    placed_children.add(trilobita_id)

    for p in adrain_placements:
        child_id = resolve_taxon(
            p["name"], p["rank"], dst, taxon_index, name_index, new_taxa_cache)

        # Determine parent: if no parent in hierarchy, connect Orders to Trilobita
        if p["parent_name"]:
            parent_id = resolve_taxon(
                p["parent_name"], p["parent_rank"], dst,
                taxon_index, name_index, new_taxa_cache)
        elif p["rank"] == "Order":
            parent_id = trilobita_id
        else:
            continue

        if child_id not in placed_children:
            try:
                dst.execute("""
                    INSERT INTO assertion
                        (subject_taxon_id, predicate, object_taxon_id,
                         reference_id, assertion_status, curation_confidence)
                    VALUES (?, 'PLACED_IN', ?, ?, ?, 'high')
                """, (child_id, parent_id, ADRAIN_2011_BIB_ID, p["status"]))
                counts["PLACED_IN"] += 1
                default_edges.append((child_id, parent_id))
                placed_children.add(child_id)
            except sqlite3.IntegrityError:
                print(f"     WARN: duplicate PLACED_IN for {p['name']} ({p['rank']}) id={child_id}")

    # --- JA2002: genus → family placements + synonyms ---
    ja_text = (SOURCES / "jell_adrain_2002.txt").read_text(encoding="utf-8")
    _, ja_body = parse_source_header(ja_text)
    ja_placements = parse_hierarchy_body(ja_body, default_leaf_rank="Genus")

    for p in ja_placements:
        if p["rank"] == "Family":
            # Family lines are just grouping headers — JA2002 doesn't assert
            # family hierarchy (that comes from Adrain 2011)
            continue

        child_id = resolve_taxon(
            p["name"], p["rank"], dst, taxon_index, name_index, new_taxa_cache)

        if p["parent_name"] and p["parent_rank"]:
            parent_id = resolve_taxon(
                p["parent_name"], p["parent_rank"], dst,
                taxon_index, name_index, new_taxa_cache)

            if child_id not in placed_children:
                dst.execute("""
                    INSERT INTO assertion
                        (subject_taxon_id, predicate, object_taxon_id,
                         reference_id, assertion_status, curation_confidence)
                    VALUES (?, 'PLACED_IN', ?, ?, ?, 'high')
                """, (child_id, parent_id, JA2002_REF_ID, p["status"]))
                counts["PLACED_IN"] += 1
                default_edges.append((child_id, parent_id))
                placed_children.add(child_id)

        # Synonyms
        for syn in p["synonyms"]:
            target_id = resolve_taxon(
                syn["target"], "Genus", dst, taxon_index, name_index, new_taxa_cache)
            syn_type = ""
            if syn["detail"]:
                # Extract synonym type from detail: "j.s.s., fide AUTHOR, YEAR"
                st_match = re.match(r'(j\.s\.s\.|j\.o\.s\.)', syn["detail"])
                if st_match:
                    syn_type = st_match.group(1)
                elif "unnecessary replacement" in syn["detail"]:
                    syn_type = "unnecessary replacement"
                elif "inappropriate emendation" in syn["detail"]:
                    syn_type = "inappropriate emendation"
                elif "incorrect spelling" in syn["detail"]:
                    syn_type = "incorrect spelling"

            pred = syn["predicate"]
            dst.execute("""
                INSERT INTO assertion
                    (subject_taxon_id, predicate, object_taxon_id,
                     reference_id, assertion_status, curation_confidence,
                     synonym_type, notes)
                VALUES (?, ?, ?, ?, 'asserted', 'high', ?, ?)
            """, (child_id, pred, target_id, JA2002_REF_ID,
                  syn_type, syn["detail"]))
            counts[pred] = counts.get(pred, 0) + 1

    return counts, default_edges, placed_children


def fallback_canonical_parent_id(src, dst, placed_children, default_edges,
                                 taxon_index, name_index, new_taxa_cache):
    """Fix 3: For taxa without default placement, fall back to canonical parent_id.

    Some taxa in canonical DB have parent_id but are not covered by source files
    (e.g., families not in Adrain 2011, genera without family in JA2002).
    """
    # Find all taxa not yet placed in default profile (excluding Class which is root)
    all_taxa = dst.execute(
        "SELECT id, name, rank FROM taxon WHERE rank != 'Class'"
    ).fetchall()

    count = 0
    for taxon_id, taxon_name, taxon_rank in all_taxa:
        if taxon_id in placed_children:
            continue

        # Check canonical DB for parent_id
        row = src.execute(
            "SELECT parent_id FROM taxonomic_ranks WHERE id = ?", (taxon_id,)
        ).fetchone()
        if not row or not row[0]:
            continue

        parent_canonical_id = row[0]
        # Verify the parent exists in assertion DB
        parent_row = dst.execute(
            "SELECT id, name, rank FROM taxon WHERE id = ?",
            (parent_canonical_id,)
        ).fetchone()
        if not parent_row:
            continue

        try:
            dst.execute("""
                INSERT INTO assertion
                    (subject_taxon_id, predicate, object_taxon_id,
                     reference_id, assertion_status, curation_confidence)
                VALUES (?, 'PLACED_IN', ?, ?, 'asserted', 'high')
            """, (taxon_id, parent_canonical_id, JA2002_REF_ID))
            count += 1
            default_edges.append((taxon_id, parent_canonical_id))
            placed_children.add(taxon_id)
        except sqlite3.IntegrityError:
            pass

    return count


def import_canonical_opinions(src, dst):
    """Fix 4: Import SYNONYM_OF/SPELLING_OF from canonical taxonomic_opinions.

    Recovers synonyms that exist in canonical DB but weren't in JA2002 source
    (i.e., synonyms from other sources imported into canonical DB).
    """
    # Get existing synonym assertions (subject_taxon_id set)
    existing = set()
    for row in dst.execute(
        "SELECT subject_taxon_id, predicate, object_taxon_id FROM assertion "
        "WHERE predicate IN ('SYNONYM_OF', 'SPELLING_OF')"
    ).fetchall():
        existing.add((row[0], row[1], row[2]))

    opinions = src.execute("""
        SELECT taxon_id, opinion_type, related_taxon_id, bibliography_id,
               assertion_status, curation_confidence,
               synonym_type, notes
        FROM taxonomic_opinions
        WHERE opinion_type IN ('SYNONYM_OF', 'SPELLING_OF')
        AND related_taxon_id IS NOT NULL
    """).fetchall()

    count = 0
    for (taxon_id, opinion_type, related_id, bib_id,
         status, confidence, syn_type, notes) in opinions:
        # Skip if already exists
        if (taxon_id, opinion_type, related_id) in existing:
            continue

        # Verify both taxa exist in assertion DB
        subj = dst.execute("SELECT id FROM taxon WHERE id = ?", (taxon_id,)).fetchone()
        obj = dst.execute("SELECT id FROM taxon WHERE id = ?", (related_id,)).fetchone()
        if not subj or not obj:
            continue

        # Map bibliography_id → reference_id (same IDs since we copied bibliography)
        ref_id = bib_id if bib_id else None

        try:
            dst.execute("""
                INSERT INTO assertion
                    (subject_taxon_id, predicate, object_taxon_id,
                     reference_id, assertion_status, curation_confidence,
                     synonym_type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (taxon_id, opinion_type, related_id, ref_id,
                  status or 'asserted', confidence or 'high',
                  syn_type, notes))
            count += 1
        except sqlite3.IntegrityError:
            pass

    return count


def process_source_treatise(dst, source_file, ref_id,
                            taxon_index, name_index, new_taxa_cache):
    """Process a Treatise source file, generating non-accepted PLACED_IN assertions.

    Returns list of (child_id, parent_id) edges for profile building.
    """
    text = source_file.read_text(encoding="utf-8")
    _, body = parse_source_header(text)
    placements = parse_hierarchy_body(body, default_leaf_rank="Genus")

    edges = []
    asserted_children = set()

    # Resolve Arthropoda / Trilobita for hierarchy
    arthropoda_id = resolve_taxon(
        "Arthropoda", "Phylum", dst, taxon_index, name_index, new_taxa_cache)
    trilobita_id = resolve_taxon(
        "Trilobita", "Class", dst, taxon_index, name_index, new_taxa_cache)
    edges.append((trilobita_id, arthropoda_id))
    asserted_children.add(trilobita_id)

    for p in placements:
        child_id = resolve_taxon(
            p["name"], p["rank"], dst, taxon_index, name_index, new_taxa_cache)

        if child_id in asserted_children:
            continue

        # Determine parent
        if p["parent_name"]:
            parent_id = resolve_taxon(
                p["parent_name"], p["parent_rank"], dst,
                taxon_index, name_index, new_taxa_cache)
        elif p["rank"] == "Order":
            parent_id = trilobita_id
        else:
            continue

        dst.execute("""
            INSERT OR IGNORE INTO assertion
                (subject_taxon_id, predicate, object_taxon_id,
                 reference_id, assertion_status, curation_confidence)
            VALUES (?, 'PLACED_IN', ?, ?, ?, 'high')
        """, (child_id, parent_id, ref_id, p["status"]))
        edges.append((child_id, parent_id))
        asserted_children.add(child_id)

    return edges


# ---------------------------------------------------------------------------
# Phase 4: Build classification profiles
# ---------------------------------------------------------------------------

def build_profiles(dst, default_edges, t1959_edges,
                    t1997_ch4_edges, t1997_ch5_edges):
    """Create profiles and edge caches."""

    # Profile 1: default (JA2002 + Adrain 2011)
    dst.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "Jell & Adrain 2002 + Adrain 2011",
        "Genus taxonomy from Jell & Adrain (2002) with family hierarchy from Adrain (2011)",
        '{"sources": ["jell_adrain_2002.txt", "adrain_2011.txt"]}',
    ))
    dst.executemany("""
        INSERT INTO classification_edge_cache (profile_id, child_id, parent_id)
        VALUES (1, ?, ?)
    """, default_edges)
    print(f"   Profile 1 (default): {len(default_edges)} edges")

    # Profile 2: treatise1959 (standalone)
    dst.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "treatise1959",
        "Treatise on Invertebrate Paleontology (1959) classification",
        json.dumps({"source": "treatise_1959.txt", "strategy": "standalone"}),
    ))
    dst.executemany("""
        INSERT OR IGNORE INTO classification_edge_cache (profile_id, child_id, parent_id)
        VALUES (2, ?, ?)
    """, t1959_edges)
    actual_1959 = dst.execute(
        "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = 2"
    ).fetchone()[0]
    print(f"   Profile 2 (treatise1959): {actual_1959} edges")

    # Profile 3: treatise1997 (hybrid: treatise1959 base + 1997 replacements)
    dst.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "treatise1997",
        "Treatise 1959 base + Treatise 1997 Agnostida (ch4) & Redlichiida (ch5)",
        json.dumps({
            "source": ["treatise_1959.txt", "treatise_1997_ch4.txt", "treatise_1997_ch5.txt"],
            "strategy": "hybrid",
            "scope": [
                {"taxon": "Agnostida", "coverage": "comprehensive"},
                {"taxon": "Redlichiida", "coverage": "comprehensive"},
            ],
        }),
    ))

    # Start with treatise1959 edges
    dst.executemany("""
        INSERT OR IGNORE INTO classification_edge_cache (profile_id, child_id, parent_id)
        VALUES (3, ?, ?)
    """, t1959_edges)

    # Build scope sets: which taxa are in the comprehensive scope of ch4/ch5
    scope_taxa = set()
    for child_id, parent_id in t1997_ch4_edges + t1997_ch5_edges:
        scope_taxa.add(child_id)

    # Find all taxa in the scope subtrees (Agnostida + Redlichiida)
    # by looking at the 1997 edges' root taxa
    scope_roots = set()
    ch4_taxa = {c for c, p in t1997_ch4_edges}
    ch5_taxa = {c for c, p in t1997_ch5_edges}
    # Root taxa of ch4/ch5 are those that appear as children but whose parents
    # are NOT themselves children in the same set
    ch4_parents = {p for c, p in t1997_ch4_edges}
    ch5_parents = {p for c, p in t1997_ch5_edges}
    ch4_root_parents = ch4_parents - ch4_taxa  # parents outside the ch4 scope
    ch5_root_parents = ch5_parents - ch5_taxa

    # Replace: delete 1959 edges for taxa in scope, then insert 1997 edges
    # For comprehensive scope: remove all 1959 edges whose child is in the scope
    for child_id in ch4_taxa | ch5_taxa:
        dst.execute("""
            DELETE FROM classification_edge_cache
            WHERE profile_id = 3 AND child_id = ?
        """, (child_id,))

    # Also remove 1959-only taxa that were children under the scope subtrees
    # (comprehensive removal: taxa in 1959 under Agnostida/Redlichiida but not in 1997)
    # We need to find the Agnostida and Redlichiida taxon IDs
    agnostida_id = dst.execute(
        "SELECT id FROM taxon WHERE name = 'Agnostida' AND rank = 'Order'"
    ).fetchone()
    redlichiida_id = dst.execute(
        "SELECT id FROM taxon WHERE name = 'Redlichiida' AND rank = 'Order'"
    ).fetchone()

    if agnostida_id:
        # Find all 1959 subtree taxa under Agnostida
        _remove_comprehensive_scope(dst, 3, agnostida_id[0],
                                    ch4_taxa | {agnostida_id[0]})
    if redlichiida_id:
        _remove_comprehensive_scope(dst, 3, redlichiida_id[0],
                                    ch5_taxa | {redlichiida_id[0]})

    # Insert 1997 edges
    dst.executemany("""
        INSERT OR IGNORE INTO classification_edge_cache (profile_id, child_id, parent_id)
        VALUES (3, ?, ?)
    """, t1997_ch4_edges + t1997_ch5_edges)

    # Handle Eodiscida → Eodiscina reorganization
    # In 1959 Eodiscida was an Order; in 1997 it might be a Suborder
    eodiscida = dst.execute(
        "SELECT id FROM taxon WHERE name = 'Eodiscida'"
    ).fetchone()
    eodiscina = dst.execute(
        "SELECT id FROM taxon WHERE name = 'Eodiscina'"
    ).fetchone()
    if eodiscida and eodiscina:
        # Move Eodiscida children to Eodiscina if Eodiscina exists in 1997
        eodiscina_in_1997 = eodiscina[0] in ch4_taxa
        if eodiscina_in_1997:
            # Move any remaining Eodiscida children to Eodiscina
            dst.execute("""
                UPDATE classification_edge_cache
                SET parent_id = ?
                WHERE profile_id = 3 AND parent_id = ?
                AND child_id NOT IN (
                    SELECT child_id FROM classification_edge_cache
                    WHERE profile_id = 3 AND parent_id = ?
                )
            """, (eodiscina[0], eodiscida[0], eodiscina[0]))

    # Ensure Agnostida → Trilobita edge
    trilobita_id = dst.execute(
        "SELECT id FROM taxon WHERE name = 'Trilobita' AND rank = 'Class'"
    ).fetchone()
    if agnostida_id and trilobita_id:
        dst.execute("""
            INSERT OR REPLACE INTO classification_edge_cache
                (profile_id, child_id, parent_id)
            VALUES (3, ?, ?)
        """, (agnostida_id[0], trilobita_id[0]))

    actual_1997 = dst.execute(
        "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = 3"
    ).fetchone()[0]
    print(f"   Profile 3 (treatise1997): {actual_1997} edges")

    return {
        "default": len(default_edges),
        "treatise1959": actual_1959,
        "treatise1997": actual_1997,
    }


def _remove_comprehensive_scope(dst, profile_id, root_id, keep_set):
    """Remove edges in profile whose children are descendants of root_id
    but not in keep_set (comprehensive scope removal)."""
    # Find all descendants of root_id in this profile via recursive query
    descendants = dst.execute("""
        WITH RECURSIVE subtree AS (
            SELECT child_id FROM classification_edge_cache
            WHERE profile_id = ? AND parent_id = ?
            UNION ALL
            SELECT e.child_id FROM classification_edge_cache e
            JOIN subtree s ON e.parent_id = s.child_id
            WHERE e.profile_id = ?
        )
        SELECT child_id FROM subtree
    """, (profile_id, root_id, profile_id)).fetchall()

    removed = 0
    for (child_id,) in descendants:
        if child_id not in keep_set:
            dst.execute("""
                DELETE FROM classification_edge_cache
                WHERE profile_id = ? AND child_id = ?
            """, (profile_id, child_id))
            removed += 1

    if removed:
        root_name = dst.execute(
            "SELECT name FROM taxon WHERE id = ?", (root_id,)
        ).fetchone()[0]
        print(f"     Comprehensive removal under {root_name}: {removed} taxa removed")


# ---------------------------------------------------------------------------
# Phase 5: Copy junction tables from canonical DB
# ---------------------------------------------------------------------------

def copy_junction_tables(src, dst):
    counts = {}

    rows = src.execute("""
        SELECT id, genus_id, formation_id, is_type_locality, notes, created_at
        FROM genus_formations
    """).fetchall()
    dst.executemany("""
        INSERT INTO genus_formations (id, genus_id, formation_id, is_type_locality, notes, created_at)
        VALUES (?,?,?,?,?,?)
    """, rows)
    counts["genus_formations"] = len(rows)

    rows = src.execute("""
        SELECT id, genus_id, country_id, region, is_type_locality, notes, created_at, region_id
        FROM genus_locations
    """).fetchall()
    dst.executemany("""
        INSERT INTO genus_locations (id, genus_id, country_id, region, is_type_locality, notes, created_at, region_id)
        VALUES (?,?,?,?,?,?,?,?)
    """, rows)
    counts["genus_locations"] = len(rows)

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


# ---------------------------------------------------------------------------
# Phase 6: Compatibility views
# ---------------------------------------------------------------------------

def create_views(cur):
    cur.executescript("""
    CREATE VIEW v_taxonomy_tree AS
    WITH RECURSIVE tree AS (
        SELECT t.id, t.name, t.rank, NULL AS parent_id, 0 AS depth
        FROM taxon t WHERE t.rank = 'Class'
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



def _build_queries():
    """Return list of (name, description, sql, params_json) tuples."""
    return [
        # --- Tree / Genera ---
        ("taxonomy_tree", "Hierarchical tree from Class to Family (profile-aware via edge_cache)",
         "SELECT t.id, t.name, t.rank, NULL as parent_id, t.author\n"
         "FROM taxon t WHERE t.rank = 'Class'\n"
         "UNION ALL\n"
         "SELECT t.id, t.name, t.rank, e.parent_id, t.author\n"
         "FROM taxon t\n"
         "JOIN classification_edge_cache e ON e.child_id = t.id\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1) AND t.rank != 'Genus'\n"
         "ORDER BY rank, name",
         '{"profile_id": "integer"}'),

        ("taxonomy_tree_genera_counts", "Count of genera per direct parent (profile-aware)",
         "SELECT e.parent_id, COUNT(*) AS genera_count\n"
         "FROM classification_edge_cache e\n"
         "JOIN taxon g ON g.id = e.child_id AND g.rank = 'Genus'\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         "GROUP BY e.parent_id",
         '{"profile_id": "integer"}'),

        ("family_genera", "Genera under a family/subfamily subtree (profile-aware, recursive)",
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
         "       e.parent_id as parent_id\n"
         "FROM taxon t\n"
         "LEFT JOIN classification_edge_cache e ON e.child_id = t.id\n"
         "  AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "LEFT JOIN taxon parent ON e.parent_id = parent.id\n"
         "WHERE t.id = :taxon_id",
         '{"taxon_id": "integer", "profile_id": "integer"}'),

        ("taxon_assertions", "All assertions for a specific taxon",
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

        ("taxon_children", "Children of a taxon (profile-aware via edge_cache)",
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

        ("taxon_children_counts", "Child rank counts (profile-aware via edge_cache)",
         "SELECT t.rank, COUNT(*) as count\n"
         "FROM taxon t\n"
         "JOIN classification_edge_cache e ON e.child_id = t.id\n"
         "WHERE e.profile_id = COALESCE(:profile_id, 1) AND e.parent_id = :taxon_id\n"
         "GROUP BY t.rank",
         '{"taxon_id": "integer", "profile_id": "integer"}'),

        # --- Genus-specific ---
        ("genus_hierarchy", "Ancestor chain for a taxon via edge_cache",
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
         "       a.assertion_status\n"
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
         "       a.assertion_status\n"
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
         "SELECT id, name, rank, is_valid,\n"
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

        # --- Classification profile selector ---
        ("classification_profiles_selector", "Available classification profiles",
         "SELECT id, name, description FROM classification_profile ORDER BY id",
         None),

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

        # --- Diversity statistics (bar chart) ---
        ("diversity_by_age", "Genus count per temporal code grouped by a parent rank",
         "WITH RECURSIVE ancestors AS (\n"
         "    SELECT e.child_id AS genus_id, e.parent_id AS ancestor_id\n"
         "    FROM classification_edge_cache e\n"
         "    JOIN taxon t ON t.id = e.child_id AND t.rank = 'Genus'\n"
         "    WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         "    UNION ALL\n"
         "    SELECT a.genus_id, e.parent_id\n"
         "    FROM ancestors a\n"
         "    JOIN classification_edge_cache e ON e.child_id = a.ancestor_id\n"
         "    WHERE e.profile_id = COALESCE(:profile_id, 1)\n"
         "),\n"
         "genus_group AS (\n"
         "    SELECT a.genus_id, grp.name AS group_name\n"
         "    FROM ancestors a\n"
         "    JOIN taxon grp ON grp.id = a.ancestor_id AND grp.rank = :grouping_rank\n"
         ")\n"
         "SELECT tcm.code AS age_label, -tcm.fad_mya AS age_order,\n"
         "       COALESCE(gg.group_name, 'Unknown') AS group_name,\n"
         "       COUNT(DISTINCT g.id) AS count\n"
         "FROM taxon g\n"
         "JOIN classification_edge_cache ge ON ge.child_id = g.id\n"
         "  AND ge.profile_id = COALESCE(:profile_id, 1)\n"
         "JOIN temporal_code_mya tcm ON g.temporal_code = tcm.code\n"
         "LEFT JOIN genus_group gg ON gg.genus_id = g.id\n"
         "WHERE g.rank = 'Genus' AND g.is_valid = 1\n"
         "  AND tcm.code IN ('LCAM','MCAM','UCAM','LORD','MORD','UORD',\n"
         "                    'LSIL','USIL','LDEV','MDEV','UDEV',\n"
         "                    'MISS','PENN','LPERM','UPERM')\n"
         "GROUP BY tcm.code, gg.group_name\n"
         "HAVING count > 0\n"
         "ORDER BY age_order, count DESC",
         '{"profile_id": "integer", "grouping_rank": "text"}'),

        # --- Profile diff edges (for Diff Tree rendering) ---
        # --- P87: Timeline ---
        ("timeline_geologic_periods", "Geologic time periods for timeline axis (Mya steps)",
         "SELECT fad_mya AS id, code AS name, -fad_mya AS sort_order\n"
         "FROM temporal_code_mya\n"
         "WHERE code IN ('LCAM','MCAM','UCAM','LORD','MORD','UORD',\n"
         "               'LSIL','USIL','LDEV','MDEV','UDEV',\n"
         "               'MISS','PENN','LPERM','UPERM')\n"
         "UNION ALL\n"
         "SELECT 251.9 AS id, 'End Permian' AS name, -251.9 AS sort_order\n"
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

        ("taxonomy_tree_by_pubyear", "Taxa filtered by naming year (cumulative)",
         "WITH RECURSIVE filtered_genera AS (\n"
         "    SELECT t.id\n"
         "    FROM taxon t\n"
         "    JOIN classification_edge_cache e ON e.child_id = t.id AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "    WHERE t.rank = 'Genus'\n"
         "    AND (:timeline_value IS NULL OR (t.year IS NOT NULL AND CAST(t.year AS INTEGER) <= :timeline_value))\n"
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

        ("tree_edges_by_pubyear", "Edges filtered by naming year (cumulative)",
         "WITH RECURSIVE filtered_genera AS (\n"
         "    SELECT t.id\n"
         "    FROM taxon t\n"
         "    JOIN classification_edge_cache e ON e.child_id = t.id AND e.profile_id = COALESCE(:profile_id, 1)\n"
         "    WHERE t.rank = 'Genus'\n"
         "    AND (:timeline_value IS NULL OR (t.year IS NOT NULL AND CAST(t.year AS INTEGER) <= :timeline_value))\n"
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
    """Build the full UI manifest dict."""
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
            # === Tab views ===
            "taxonomy_tree": {
                "type": "hierarchy",
                "display": "tree",
                "title": "Taxonomy",
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
                "title": "Genera",
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
                "title": "Assertions",
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
                "title": "Profiles",
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

            # === P75/P23: Tree Chart (was Radial Tree) ===
            "tree_chart": {
                "type": "hierarchy",
                "display": "tree_chart",
                "title": "Tree",
                "description": "Taxonomy tree visualization — radial or rectangular layout",
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
                        "default": 3,
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
                                "Class": 0.08,
                                "Order": 0.20,
                                "Suborder": 0.32,
                                "Superfamily": 0.44,
                                "Family": 0.56,
                                "Subfamily": 0.70,
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
                            {"key": "genera_count", "label": "Genera"},
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
                        ],
                        "on_row_click": {"detail_view": "taxon_detail_view", "id_key": "object_taxon_id"},
                        "entity_type": "assertion",
                        "entity_id_key": "assertion_id",
                        "entity_defaults": {"subject_taxon_id": "id"},
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
                        ],
                        "entity_type": "assertion",
                        "entity_id_key": "assertion_id",
                        "entity_defaults": {"subject_taxon_id": "id"},
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

            # === Statistics (compound view) ===
            "statistics": {
                "type": "compound",
                "title": "Statistics",
                "icon": "bi-bar-chart-line",
                "controls": [],
                "default_sub_view": "geologic_timeline",
                "sub_views": {
                    "geologic_timeline": {
                        "title": "Geologic Timeline",
                        "display": "tree_chart_timeline",
                        "description": "Taxonomy tree animated over geologic time",
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
                                "Class": 0.08,
                                "Order": 0.20,
                                "Suborder": 0.32,
                                "Superfamily": 0.44,
                                "Family": 0.56,
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
                            ],
                        },
                    },
                    "pubyear_timeline": {
                        "title": "Publication Timeline",
                        "display": "tree_chart_timeline",
                        "description": "Taxonomy tree animated over publication year",
                        "source_query": "taxonomy_tree_by_pubyear",
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
                                "Class": 0.08,
                                "Order": 0.20,
                                "Suborder": 0.32,
                                "Superfamily": 0.44,
                                "Family": 0.56,
                                "Subfamily": 0.70,
                                "Genus": 1.0,
                            },
                            "edge_query": "tree_edges_by_pubyear",
                            "edge_params": {"profile_id": "$profile_id"},
                            "edge_id_key": "child_id",
                            "edge_parent_key": "parent_id",
                        },
                        "timeline_options": {
                            "param_name": "timeline_value",
                            "default_step_size": 1,
                            "axis_modes": [
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
                    "bar_chart": {
                        "title": "Diversity Chart",
                        "display": "bar_chart",
                        "icon": "bi-bar-chart-fill",
                        "description": "Genus diversity by geologic time, grouped by higher taxonomy",
                        "source_query": "diversity_by_age",
                        "bar_chart_options": {
                            "x_key": "age_label",
                            "x_order_key": "age_order",
                            "group_key": "group_name",
                            "value_key": "count",
                            "grouping_param": "grouping_rank",
                            "grouping_ranks": [
                                {"value": "Order", "label": "Order"},
                                {"value": "Suborder", "label": "Suborder"},
                                {"value": "Superfamily", "label": "Superfamily"},
                                {"value": "Family", "label": "Family"},
                            ],
                            "default_grouping": "Order",
                        },
                    },
                },
            },
        },
        "editable_entities": {
            "taxon": {
                "table": "taxon",
                "pk": "id",
                "operations": ["create", "read", "update", "delete"],
                "fields": {
                    "name": {"type": "text", "required": True, "label": "Name"},
                    "rank": {"type": "text", "required": True,
                             "enum": ["Class", "Order", "Suborder", "Superfamily",
                                      "Family", "Subfamily", "Genus"],
                             "label": "Rank"},
                    "author": {"type": "text", "label": "Author"},
                    "year": {"type": "text", "label": "Year"},
                    "year_suffix": {"type": "text", "label": "Year Suffix"},
                    "notes": {"type": "text", "label": "Notes"},
                    "is_placeholder": {"type": "boolean", "default": 0, "label": "Placeholder"},
                    "type_species": {"type": "text", "label": "Type Species"},
                    "type_species_author": {"type": "text", "label": "Type Species Author"},
                    "formation": {"type": "text", "label": "Formation"},
                    "location": {"type": "text", "label": "Location"},
                    "family": {"type": "text", "label": "Family"},
                    "temporal_code": {"type": "text", "label": "Temporal Code"},
                    "is_valid": {"type": "boolean", "default": 1, "label": "Valid"},
                    "raw_entry": {"type": "text", "label": "Raw Entry"},
                },
                "list_query": "genera_list",
                "detail_query": "taxon_detail",
            },
            "assertion": {
                "table": "assertion",
                "pk": "id",
                "operations": ["create", "read", "update", "delete"],
                "fields": {
                    "subject_taxon_id": {"type": "integer", "required": True,
                                         "fk": "taxon.id", "label": "Subject Taxon",
                                         "readonly_on_edit": True},
                    "predicate": {"type": "text", "required": True,
                                  "enum": ["PLACED_IN", "SYNONYM_OF", "SPELLING_OF",
                                           "RANK_AS", "VALID_AS"],
                                  "label": "Predicate"},
                    "object_taxon_id": {"type": "integer", "fk": "taxon.id",
                                        "label": "Object Taxon"},
                    "value_text": {"type": "text", "label": "Value"},
                    "reference_id": {"type": "integer", "fk": "reference.id",
                                     "label": "Reference"},
                    "assertion_status": {"type": "text", "default": "asserted",
                                         "enum": ["asserted", "incertae_sedis",
                                                  "questionable", "indet"],
                                         "label": "Status"},
                    "curation_confidence": {"type": "text", "default": "high",
                                            "enum": ["high", "medium", "low"],
                                            "label": "Confidence"},
                    "synonym_type": {"type": "text", "label": "Synonym Type"},
                    "notes": {"type": "text", "label": "Notes"},
                },
                "list_query": "assertion_list",
                "hooks": [
                    {
                        "name": "rebuild_edge_cache",
                        "on": ["create", "update", "delete"],
                        "trigger_when": {"field": "predicate", "value": "PLACED_IN"},
                        "sql": "DELETE FROM classification_edge_cache; INSERT INTO classification_edge_cache (profile_id, child_id, parent_id) SELECT p.id, a.subject_taxon_id, a.object_taxon_id FROM assertion a CROSS JOIN classification_profile p WHERE a.predicate = 'PLACED_IN' AND (a.is_accepted = 1 OR (p.id != 1 AND a.reference_id IN (SELECT r.id FROM reference r WHERE r.authors LIKE '%Treatise%')))",
                    },
                ],
            },
            "reference": {
                "table": "reference",
                "pk": "id",
                "operations": ["create", "read", "update"],
                "fields": {
                    "authors": {"type": "text", "required": True, "label": "Authors"},
                    "year": {"type": "integer", "label": "Year"},
                    "year_suffix": {"type": "text", "label": "Year Suffix"},
                    "title": {"type": "text", "label": "Title"},
                    "journal": {"type": "text", "label": "Journal"},
                    "volume": {"type": "text", "label": "Volume"},
                    "pages": {"type": "text", "label": "Pages"},
                    "publisher": {"type": "text", "label": "Publisher"},
                    "city": {"type": "text", "label": "City"},
                    "editors": {"type": "text", "label": "Editors"},
                    "book_title": {"type": "text", "label": "Book Title"},
                    "reference_type": {"type": "text", "default": "article",
                                       "enum": ["article", "book", "chapter",
                                                "thesis", "report", "cross_ref"],
                                       "label": "Type"},
                    "raw_entry": {"type": "text", "required": True, "label": "Raw Entry"},
                },
                "list_query": "reference_list",
            },
            "classification_profile": {
                "table": "classification_profile",
                "pk": "id",
                "operations": ["create", "read", "update", "delete"],
                "fields": {
                    "name": {"type": "text", "required": True, "label": "Name"},
                    "description": {"type": "text", "label": "Description"},
                    "rule_json": {"type": "text", "label": "Rules (JSON)"},
                },
                "list_query": "profile_list",
            },
        },
    }


# ---------------------------------------------------------------------------
# Phase 7: SCODA metadata — ui_queries + ui_manifest
# ---------------------------------------------------------------------------

def create_scoda_metadata(dst, version):
    """Create SCODA metadata tables and insert ui_queries / ui_manifest."""
    cur = dst.cursor()

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

    # artifact_metadata
    cur.executemany("INSERT INTO artifact_metadata VALUES (?,?)", [
        ("artifact_id", "trilobita"),
        ("name", "Trilobita"),
        ("version", version),
        ("schema_version", "1.0"),
        ("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        ("description",
         "Assertion-centric trilobite taxonomy — built from canonical source data (R04)"),
        ("license", "CC-BY-4.0"),
    ])

    # provenance
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
        (3, "supplementary",
         "Moore, R.C. (Ed.), 1959, Treatise on Invertebrate Paleontology, "
         "Part O, Arthropoda 1, Trilobita.",
         "Treatise 1959 classification profile", 1959, None),
        (4, "supplementary",
         "Kaesler, R.L. (Ed.), 1997, Treatise on Invertebrate Paleontology, "
         "Part O, Revised, Vol. 1.",
         "Treatise 1997 classification profile (Agnostida + Redlichiida)", 1997, None),
        (5, "build",
         "Trilobita assertion-centric pipeline (2026). Script: build_trilobita_db.py",
         "Source-driven build from data/sources/*.txt (R04 extended format)", 2026, None),
    ])

    # schema_descriptions
    cur.executemany("INSERT INTO schema_descriptions VALUES (?,?,?)", [
        ("taxon", None, "Taxonomic names (Class to Genus) without parent_id — hierarchy derived from assertions"),
        ("taxon", "id", "Primary key"),
        ("taxon", "name", "Taxon name"),
        ("taxon", "rank", "Taxonomic rank (Class, Order, Suborder, Superfamily, Family, Subfamily, Genus)"),
        ("reference", None, "Literature references (bibliography + source references)"),
        ("assertion", None, "Taxonomic assertions: subject taxon + predicate + object taxon"),
        ("assertion", "predicate", "PLACED_IN, SYNONYM_OF, SPELLING_OF, RANK_AS, VALID_AS"),
        ("assertion", "predicate+reference", "Same subject can have multiple PLACED_IN from different references"),
        ("classification_profile", None, "Named classification profiles for building different trees"),
        ("classification_edge_cache", None, "Materialized parent-child edges for a given profile"),
        ("genus_formations", None, "Genus-Formation many-to-many junction table"),
        ("genus_locations", None, "Genus-Country/Region many-to-many junction table"),
        ("taxon_reference", None, "Taxon-Reference FK links (renamed from taxon_bibliography)"),
        ("taxon_reference", "reference_id", "FK to reference(id) — renamed from bibliography_id"),
    ])

    # ui_display_intent
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

    # ui_queries
    queries = _build_queries()
    for name, desc, sql, params in queries:
        cur.execute(
            "INSERT INTO ui_queries (name, description, sql, params_json) VALUES (?,?,?,?)",
            (name, desc, sql, params))

    # ui_manifest
    manifest = _build_manifest()
    cur.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json) VALUES (?,?,?)",
        ("default",
         "Assertion-centric taxonomy views — source-driven build (R04)",
         json.dumps(manifest, ensure_ascii=False)))

    dst.commit()


# ---------------------------------------------------------------------------
# Hub Manifest
# ---------------------------------------------------------------------------

def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_hub_manifest(db_path, version):
    manifest = {
        "hub_manifest_version": "1.0",
        "package_id": "trilobita",
        "version": version,
        "title": "Trilobita — assertion-centric trilobite taxonomy",
        "description": "Trilobite taxonomy database built from canonical source data",
        "license": "CC-BY-4.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": [
            "Jell, P.A., and Adrain, J.M., 2002, Available Generic Names for Trilobites",
            "Adrain, J.M., 2011, Class Trilobita Walch, 1771",
            "Moore, R.C. (Ed.), 1959, Treatise on Invertebrate Paleontology, Part O",
            "Kaesler, R.L. (Ed.), 1997, Treatise on Invertebrate Paleontology, Part O, Revised",
        ],
        "filename": db_path.name,
        "sha256": _sha256_file(db_path),
        "size_bytes": db_path.stat().st_size,
    }

    out_path = db_path.parent / f"trilobita-{version}.manifest.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  Hub Manifest: {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build assertion DB from data/sources/*.txt (R04)")
    parser.add_argument(
        "--version", default=ASSERTION_VERSION,
        help=f"Version string (default: {ASSERTION_VERSION})")
    args = parser.parse_args()

    version = args.version

    if not SRC_DB.exists():
        print(f"ERROR: Source DB not found: {SRC_DB}", file=sys.stderr)
        sys.exit(1)

    # Verify source files exist
    required = [
        "jell_adrain_2002.txt", "adrain_2011.txt", "treatise_1959.txt",
        "treatise_1997_ch4.txt", "treatise_1997_ch5.txt",
    ]
    for f in required:
        if not (SOURCES / f).exists():
            print(f"ERROR: Source file not found: {SOURCES / f}", file=sys.stderr)
            sys.exit(1)

    DST_DIR.mkdir(parents=True, exist_ok=True)
    dst_db = DST_DIR / f"trilobita-{version}.db"
    if dst_db.exists():
        dst_db.unlink()

    src = sqlite3.connect(str(SRC_DB))
    dst = sqlite3.connect(str(dst_db))
    dst.execute("PRAGMA journal_mode=WAL")
    dst.execute("PRAGMA foreign_keys=ON")

    print(f"=== Build Assertion DB v{version} (from sources) ===\n")

    # 1. Schema
    print("1. Creating schema...")
    create_schema(dst.cursor())
    dst.commit()

    # 2. Copy taxon
    print("2. Copying taxon data from canonical DB...")
    n_taxon = copy_taxon(src, dst)
    dst.commit()
    print(f"   → {n_taxon} taxon records")

    # 3. Copy references
    print("3. Copying references + inserting source references...")
    n_ref = copy_references(src, dst)
    dst.commit()
    print(f"   → {n_ref} reference records")
    print(f"     JA2002 ref_id={JA2002_REF_ID}")
    print(f"     Treatise 1959 ref_id={TREATISE_1959_REF_ID}")
    print(f"     Treatise 1997 ch4 ref_id={TREATISE_1997_CH4_REF_ID}")
    print(f"     Treatise 1997 ch5 ref_id={TREATISE_1997_CH5_REF_ID}")

    # 4. Build taxon index
    print("4. Building taxon index...")
    taxon_index, name_index = build_taxon_index(dst)
    new_taxa_cache = {}
    print(f"   → {len(taxon_index)} indexed taxa")

    # 5. Process default profile sources (JA2002 + Adrain 2011)
    print("5. Processing default profile sources...")
    default_counts, default_edges, placed_children = process_source_default(
        dst, taxon_index, name_index, new_taxa_cache)
    dst.commit()
    for k, v in default_counts.items():
        print(f"   → {k}: {v}")

    # 5b. Fallback: canonical parent_id for genera without PLACED_IN
    print("   Fallback: canonical parent_id for unplaced genera...")
    n_fallback = fallback_canonical_parent_id(
        src, dst, placed_children, default_edges,
        taxon_index, name_index, new_taxa_cache)
    dst.commit()
    print(f"   → {n_fallback} genera placed via canonical parent_id")

    # 5c. Import canonical opinions (SYNONYM_OF/SPELLING_OF)
    print("   Importing canonical DB opinions...")
    n_opinions = import_canonical_opinions(src, dst)
    dst.commit()
    print(f"   → {n_opinions} additional synonym/spelling assertions")

    # 6. Process Treatise sources
    print("6. Processing Treatise 1959...")
    t1959_edges = process_source_treatise(
        dst, SOURCES / "treatise_1959.txt", TREATISE_1959_REF_ID,
        taxon_index, name_index, new_taxa_cache)
    dst.commit()
    print(f"   → {len(t1959_edges)} edges")

    print("   Processing Treatise 1997 ch4 (Agnostida)...")
    t1997_ch4_edges = process_source_treatise(
        dst, SOURCES / "treatise_1997_ch4.txt", TREATISE_1997_CH4_REF_ID,
        taxon_index, name_index, new_taxa_cache)
    dst.commit()
    print(f"   → {len(t1997_ch4_edges)} edges")

    print("   Processing Treatise 1997 ch5 (Redlichiida)...")
    t1997_ch5_edges = process_source_treatise(
        dst, SOURCES / "treatise_1997_ch5.txt", TREATISE_1997_CH5_REF_ID,
        taxon_index, name_index, new_taxa_cache)
    dst.commit()
    print(f"   → {len(t1997_ch5_edges)} edges")

    # 7. New taxa summary
    if new_taxa_cache:
        print(f"\n   New taxa created: {len(new_taxa_cache)}")

    # 8. Build profiles
    print("\n7. Building classification profiles...")
    profile_counts = build_profiles(dst, default_edges, t1959_edges,
                                    t1997_ch4_edges, t1997_ch5_edges)
    dst.commit()

    # 9. Junction tables
    print("\n8. Copying junction tables...")
    jcounts = copy_junction_tables(src, dst)
    dst.commit()
    for tbl, cnt in jcounts.items():
        print(f"   → {tbl}: {cnt}")

    # 10. Views
    print("\n9. Creating compatibility views...")
    create_views(dst.cursor())
    dst.commit()

    # 10b. Build temporal_code_mya mapping table
    print("   Building temporal_code_mya table...")
    pc_db = Path(find_paleocore_db())
    dst.execute(f"ATTACH DATABASE '{pc_db}' AS pc")
    dst.execute("""
        CREATE TABLE temporal_code_mya AS
        SELECT code, start_mya AS fad_mya, end_mya AS lad_mya
        FROM pc.temporal_ranges
        WHERE start_mya IS NOT NULL
        UNION ALL SELECT 'USIL/LDEV', 433.4, 393.3
        UNION ALL SELECT 'UCAM/LORD', 497.0, 470.0
        UNION ALL SELECT 'UORD/LSIL', 458.4, 433.4
        UNION ALL SELECT 'PENN/LPERM', 323.2, 272.95
    """)
    n_tcm = dst.execute("SELECT COUNT(*) FROM temporal_code_mya").fetchone()[0]
    dst.execute("DETACH DATABASE pc")
    dst.commit()
    print(f"   → {n_tcm} temporal_code_mya mappings")

    # 11. SCODA metadata
    print("10. Creating SCODA metadata...")
    create_scoda_metadata(dst, version=version)
    n_queries = dst.execute("SELECT COUNT(*) FROM ui_queries").fetchone()[0]
    print(f"   → {n_queries} ui_queries, 1 ui_manifest")

    # Summary
    total_assertions = dst.execute("SELECT COUNT(*) FROM assertion").fetchone()[0]
    placed_in = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='PLACED_IN'"
    ).fetchone()[0]
    placed_in_default = dst.execute(
        "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id=1"
    ).fetchone()[0]
    synonym_of = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='SYNONYM_OF'"
    ).fetchone()[0]
    spelling_of = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='SPELLING_OF'"
    ).fetchone()[0]
    n_taxon_final = dst.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
    total_edges = dst.execute("SELECT COUNT(*) FROM classification_edge_cache").fetchone()[0]

    print(f"\n{'='*50}")
    print(f"  taxon:                {n_taxon_final}")
    print(f"  reference:            {n_ref}")
    print(f"  assertion:            {total_assertions}")
    print(f"    PLACED_IN:          {placed_in} (default profile: {placed_in_default})")
    print(f"    SYNONYM_OF:         {synonym_of}")
    print(f"    SPELLING_OF:        {spelling_of}")
    print(f"  edge_cache:           {total_edges}")
    for name, count in profile_counts.items():
        print(f"    {name}: {count}")
    print(f"\nOutput: {dst_db}")

    src.close()
    dst.close()

    # 12. Hub Manifest
    print("\n11. Generating Hub Manifest...")
    generate_hub_manifest(dst_db, version)


if __name__ == "__main__":
    main()
