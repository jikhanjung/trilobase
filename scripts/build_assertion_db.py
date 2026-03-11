#!/usr/bin/env python3
"""Build assertion DB 0.2.0 from data/sources/*.txt (R04 extended format).

Single-script replacement for the 3-step pipeline:
  create_assertion_db.py → import_treatise1959.py → import_treatise.py

Reads:
  - data/sources/jell_adrain_2002.txt      → genera, families, synonyms (default profile)
  - data/sources/adrain_2011.txt           → suprafamilial hierarchy (default profile)
  - data/sources/treatise_1959.txt         → full hierarchy (treatise1959 profile)
  - data/sources/treatise_2004_ch4.txt     → Agnostida (treatise2004 profile)
  - data/sources/treatise_2004_ch5.txt     → Redlichiida (treatise2004 profile)

Still copies from canonical DB:
  - taxon metadata (formation, location, temporal_code, type_species, etc.)
  - reference/bibliography
  - genus_formations, genus_locations, taxon_reference

Usage:
    python scripts/build_assertion_db.py [--version 0.2.0]
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

from db_path import find_trilobase_db

ASSERTION_VERSION = "0.2.0"

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"
SRC_DB = Path(find_trilobase_db())
DST_DIR = ROOT / "db"

# Well-known IDs — set at runtime
ADRAIN_2011_BIB_ID = 2131  # bibliography id in canonical DB
JA2002_REF_ID = None  # set after insert
TREATISE_1959_REF_ID = None
TREATISE_2004_CH4_REF_ID = None
TREATISE_2004_CH5_REF_ID = None


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
RANK_ORDER = {"Class": 0, "Order": 1, "Suborder": 2, "Superfamily": 3,
              "Family": 4, "Subfamily": 5, "Genus": 6}


def parse_hierarchy_body(body: str, default_leaf_rank="Genus"):
    """Parse indented hierarchy body into list of placement records.

    Returns list of dicts:
      {"name", "rank", "author", "year", "parent_name", "parent_rank",
       "status", "synonyms": [...]}
    """
    placements = []
    # Stack: [(indent_level, name, rank)]
    stack = []

    for raw_line in body.splitlines():
        # Skip empty lines and comments
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Measure indent (number of leading spaces / 2)
        indent = len(raw_line) - len(raw_line.lstrip())
        indent_level = indent // 2  # 2-space indent

        # Handle synonym lines (= or ~)
        syn_match = re.match(r'^\s+(=|~)\s+(.+)$', raw_line)
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
        for kw in RANK_KEYWORDS:
            if line.startswith(kw + " "):
                rank = kw
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

        # Pop stack to find parent at correct level
        while stack and stack[-1][0] >= indent_level:
            stack.pop()

        parent_name = stack[-1][1] if stack else None
        parent_rank = stack[-1][2] if stack else None

        stack.append((indent_level, name, rank))

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
# Schema (same as create_assertion_db.py)
# ---------------------------------------------------------------------------

def create_schema(cur):
    cur.executescript("""
    CREATE TABLE taxon (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rank TEXT NOT NULL
            CHECK(rank IN ('Class','Order','Suborder','Superfamily','Family','Subfamily','Genus')),
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
        is_accepted INTEGER DEFAULT 0,
        synonym_type TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_assertion_subject ON assertion(subject_taxon_id);
    CREATE INDEX idx_assertion_predicate ON assertion(predicate);
    CREATE UNIQUE INDEX idx_unique_accepted
        ON assertion(subject_taxon_id, predicate) WHERE is_accepted = 1;

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


# ---------------------------------------------------------------------------
# Phase 2: Copy references + insert source references
# ---------------------------------------------------------------------------

def copy_references(src, dst):
    """Copy bibliography from canonical DB and insert source-specific references."""
    global JA2002_REF_ID, TREATISE_1959_REF_ID
    global TREATISE_2004_CH4_REF_ID, TREATISE_2004_CH5_REF_ID

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

    # Insert Treatise 2004 ch4
    cur = dst.execute("""
        INSERT INTO reference (authors, year, title, editors, book_title,
                               reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "SHERGOLD, J.H., LAURIE, J.R. & SUN, X.", 2004,
        "Classification of the Agnostida",
        "Kaesler, R.L.",
        "Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1",
        "incollection",
        "Shergold, J.H., Laurie, J.R. & Sun, X., 2004, Classification of the Agnostida. "
        "In: Kaesler, R.L. (Ed.), Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1, Ch. 4.",
    ))
    TREATISE_2004_CH4_REF_ID = cur.lastrowid

    # Insert Treatise 2004 ch5
    cur = dst.execute("""
        INSERT INTO reference (authors, year, title, editors, book_title,
                               reference_type, raw_entry)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "PALMER, A.R. & REPINA, L.N.", 2004,
        "Classification of the Redlichiida",
        "Kaesler, R.L.",
        "Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1",
        "incollection",
        "Palmer, A.R. & Repina, L.N., 2004, Classification of the Redlichiida. "
        "In: Kaesler, R.L. (Ed.), Treatise on Invertebrate Paleontology, Part O, Revised, Vol. 1, Ch. 5.",
    ))
    TREATISE_2004_CH5_REF_ID = cur.lastrowid

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

    Returns counts dict.
    """
    counts = {"PLACED_IN": 0, "SYNONYM_OF": 0, "SPELLING_OF": 0}

    # --- Adrain 2011: suprafamilial hierarchy ---
    adrain_text = (SOURCES / "adrain_2011.txt").read_text(encoding="utf-8")
    _, adrain_body = parse_source_header(adrain_text)
    adrain_placements = parse_hierarchy_body(adrain_body, default_leaf_rank="Family")

    # Resolve Trilobita (Class) as root for Orders
    trilobita_id = resolve_taxon(
        "Trilobita", "Class", dst, taxon_index, name_index, new_taxa_cache)

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

        # Check if this child already has an accepted PLACED_IN
        existing = dst.execute(
            "SELECT id FROM assertion WHERE subject_taxon_id = ? "
            "AND predicate = 'PLACED_IN' AND is_accepted = 1",
            (child_id,)
        ).fetchone()
        if not existing:
            try:
                dst.execute("""
                    INSERT INTO assertion
                        (subject_taxon_id, predicate, object_taxon_id,
                         reference_id, assertion_status, curation_confidence, is_accepted)
                    VALUES (?, 'PLACED_IN', ?, ?, ?, 'high', 1)
                """, (child_id, parent_id, ADRAIN_2011_BIB_ID, p["status"]))
                counts["PLACED_IN"] += 1
            except sqlite3.IntegrityError:
                print(f"     WARN: duplicate PLACED_IN for {p['name']} ({p['rank']}) id={child_id}")
                pass

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

            # Check if this child already has an accepted PLACED_IN
            existing = dst.execute(
                "SELECT id FROM assertion WHERE subject_taxon_id = ? "
                "AND predicate = 'PLACED_IN' AND is_accepted = 1",
                (child_id,)
            ).fetchone()
            if not existing:
                dst.execute("""
                    INSERT INTO assertion
                        (subject_taxon_id, predicate, object_taxon_id,
                         reference_id, assertion_status, curation_confidence, is_accepted)
                    VALUES (?, 'PLACED_IN', ?, ?, ?, 'high', 1)
                """, (child_id, parent_id, JA2002_REF_ID, p["status"]))
                counts["PLACED_IN"] += 1

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
                     is_accepted, synonym_type, notes)
                VALUES (?, ?, ?, ?, 'asserted', 'high', 0, ?, ?)
            """, (child_id, pred, target_id, JA2002_REF_ID,
                  syn_type, syn["detail"]))
            counts[pred] = counts.get(pred, 0) + 1

    return counts


def fallback_canonical_parent_id(src, dst, taxon_index, name_index, new_taxa_cache):
    """Fix 3: For taxa without accepted PLACED_IN, fall back to canonical parent_id.

    Some taxa in canonical DB have parent_id but are not covered by source files
    (e.g., families not in Adrain 2011, genera without family in JA2002).
    """
    # Find all taxa without accepted PLACED_IN (excluding Class which is root)
    unplaced = dst.execute("""
        SELECT t.id, t.name, t.rank FROM taxon t
        WHERE t.rank != 'Class'
        AND NOT EXISTS (
            SELECT 1 FROM assertion a
            WHERE a.subject_taxon_id = t.id
            AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1
        )
    """).fetchall()

    count = 0
    for genus_id, genus_name, genus_rank in unplaced:
        # Check canonical DB for parent_id
        row = src.execute(
            "SELECT parent_id FROM taxonomic_ranks WHERE id = ?", (genus_id,)
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
                     reference_id, assertion_status, curation_confidence, is_accepted)
                VALUES (?, 'PLACED_IN', ?, ?, 'asserted', 'high', 1)
            """, (genus_id, parent_canonical_id, JA2002_REF_ID))
            count += 1
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
               assertion_status, curation_confidence, is_accepted,
               synonym_type, notes
        FROM taxonomic_opinions
        WHERE opinion_type IN ('SYNONYM_OF', 'SPELLING_OF')
        AND related_taxon_id IS NOT NULL
    """).fetchall()

    count = 0
    for (taxon_id, opinion_type, related_id, bib_id,
         status, confidence, accepted, syn_type, notes) in opinions:
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
                     is_accepted, synonym_type, notes)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
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

    # Resolve Trilobita for root-level Orders
    trilobita_id = resolve_taxon(
        "Trilobita", "Class", dst, taxon_index, name_index, new_taxa_cache)

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
                 reference_id, assertion_status, curation_confidence, is_accepted)
            VALUES (?, 'PLACED_IN', ?, ?, ?, 'high', 0)
        """, (child_id, parent_id, ref_id, p["status"]))
        edges.append((child_id, parent_id))
        asserted_children.add(child_id)

    return edges


# ---------------------------------------------------------------------------
# Phase 4: Build classification profiles
# ---------------------------------------------------------------------------

def build_profiles(dst, t1959_edges, t2004_ch4_edges, t2004_ch5_edges):
    """Create profiles and edge caches."""

    # Profile 1: default (JA2002 + Adrain 2011)
    dst.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "Jell & Adrain 2002 + Adrain 2011",
        "Genus taxonomy from Jell & Adrain (2002) with family hierarchy from Adrain (2011)",
        '{"predicate": "PLACED_IN", "is_accepted": 1}',
    ))
    default_edges = dst.execute("""
        SELECT subject_taxon_id, object_taxon_id
        FROM assertion
        WHERE predicate = 'PLACED_IN' AND is_accepted = 1
    """).fetchall()
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

    # Profile 3: treatise2004 (hybrid: treatise1959 base + 2004 replacements)
    dst.execute("""
        INSERT INTO classification_profile (name, description, rule_json)
        VALUES (?, ?, ?)
    """, (
        "treatise2004",
        "Treatise 1959 base + Treatise 2004 Agnostida (ch4) & Redlichiida (ch5)",
        json.dumps({
            "source": ["treatise_1959.txt", "treatise_2004_ch4.txt", "treatise_2004_ch5.txt"],
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
    for child_id, parent_id in t2004_ch4_edges + t2004_ch5_edges:
        scope_taxa.add(child_id)

    # Find all taxa in the scope subtrees (Agnostida + Redlichiida)
    # by looking at the 2004 edges' root taxa
    scope_roots = set()
    ch4_taxa = {c for c, p in t2004_ch4_edges}
    ch5_taxa = {c for c, p in t2004_ch5_edges}
    # Root taxa of ch4/ch5 are those that appear as children but whose parents
    # are NOT themselves children in the same set
    ch4_parents = {p for c, p in t2004_ch4_edges}
    ch5_parents = {p for c, p in t2004_ch5_edges}
    ch4_root_parents = ch4_parents - ch4_taxa  # parents outside the ch4 scope
    ch5_root_parents = ch5_parents - ch5_taxa

    # Replace: delete 1959 edges for taxa in scope, then insert 2004 edges
    # For comprehensive scope: remove all 1959 edges whose child is in the scope
    for child_id in ch4_taxa | ch5_taxa:
        dst.execute("""
            DELETE FROM classification_edge_cache
            WHERE profile_id = 3 AND child_id = ?
        """, (child_id,))

    # Also remove 1959-only taxa that were children under the scope subtrees
    # (comprehensive removal: taxa in 1959 under Agnostida/Redlichiida but not in 2004)
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

    # Insert 2004 edges
    dst.executemany("""
        INSERT OR IGNORE INTO classification_edge_cache (profile_id, child_id, parent_id)
        VALUES (3, ?, ?)
    """, t2004_ch4_edges + t2004_ch5_edges)

    # Handle Eodiscida → Eodiscina reorganization
    # In 1959 Eodiscida was an Order; in 2004 it might be a Suborder
    eodiscida = dst.execute(
        "SELECT id FROM taxon WHERE name = 'Eodiscida'"
    ).fetchone()
    eodiscina = dst.execute(
        "SELECT id FROM taxon WHERE name = 'Eodiscina'"
    ).fetchone()
    if eodiscida and eodiscina:
        # Move Eodiscida children to Eodiscina if Eodiscina exists in 2004
        eodiscina_in_2004 = eodiscina[0] in ch4_taxa
        if eodiscina_in_2004:
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

    actual_2004 = dst.execute(
        "SELECT COUNT(*) FROM classification_edge_cache WHERE profile_id = 3"
    ).fetchone()[0]
    print(f"   Profile 3 (treatise2004): {actual_2004} edges")

    return {
        "default": len(default_edges),
        "treatise1959": actual_1959,
        "treatise2004": actual_2004,
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
        SELECT t.id, t.name, t.rank, a.object_taxon_id, tree.depth + 1
        FROM taxon t
        JOIN assertion a ON a.subject_taxon_id = t.id
            AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1
        JOIN tree ON a.object_taxon_id = tree.id
    )
    SELECT * FROM tree;

    CREATE VIEW v_taxonomic_ranks AS
    SELECT t.*,
           (SELECT a.object_taxon_id FROM assertion a
            WHERE a.subject_taxon_id = t.id
              AND a.predicate = 'PLACED_IN' AND a.is_accepted = 1
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
# Phase 7: SCODA metadata (reuse from create_assertion_db.py)
# ---------------------------------------------------------------------------

def create_scoda_metadata(dst, version):
    """Create SCODA metadata — imports from create_assertion_db.py."""
    # Import the metadata functions from the existing script
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "create_assertion_db",
        ROOT / "scripts" / "create_assertion_db.py"
    )
    mod = importlib.util.module_from_spec(spec)

    # We need to handle the import of db_path in the module
    import sys as _sys
    old_path = _sys.path[:]
    if str(ROOT / "scripts") not in _sys.path:
        _sys.path.insert(0, str(ROOT / "scripts"))
    try:
        spec.loader.exec_module(mod)
    finally:
        _sys.path[:] = old_path

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
        ("artifact_id", "trilobase-assertion"),
        ("name", "Trilobase (Assertion-Centric)"),
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
         "Kaesler, R.L. (Ed.), 2004, Treatise on Invertebrate Paleontology, "
         "Part O, Revised, Vol. 1.",
         "Treatise 2004 classification profile (Agnostida + Redlichiida)", 2004, None),
        (5, "build",
         "Trilobase assertion-centric pipeline (2026). Script: build_assertion_db.py",
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
        ("assertion", "is_accepted", "1 = currently accepted assertion for this subject+predicate"),
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

    # ui_queries — reuse from create_assertion_db
    queries = mod._build_queries()
    for name, desc, sql, params in queries:
        cur.execute(
            "INSERT INTO ui_queries (name, description, sql, params_json) VALUES (?,?,?,?)",
            (name, desc, sql, params))

    # ui_manifest — reuse from create_assertion_db
    manifest = mod._build_manifest()
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
        "package_id": "trilobase-assertion",
        "version": version,
        "title": "Trilobase (Assertion-Centric) — source-driven build",
        "description": "Assertion-centric trilobite taxonomy database, "
                       "built from canonical source data (R04 extended format)",
        "license": "CC-BY-4.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": [
            "Jell, P.A., and Adrain, J.M., 2002, Available Generic Names for Trilobites",
            "Adrain, J.M., 2011, Class Trilobita Walch, 1771",
            "Moore, R.C. (Ed.), 1959, Treatise on Invertebrate Paleontology, Part O",
            "Kaesler, R.L. (Ed.), 2004, Treatise on Invertebrate Paleontology, Part O, Revised",
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
        "treatise_2004_ch4.txt", "treatise_2004_ch5.txt",
    ]
    for f in required:
        if not (SOURCES / f).exists():
            print(f"ERROR: Source file not found: {SOURCES / f}", file=sys.stderr)
            sys.exit(1)

    DST_DIR.mkdir(parents=True, exist_ok=True)
    dst_db = DST_DIR / f"trilobase-assertion-{version}.db"
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
    print(f"     Treatise 2004 ch4 ref_id={TREATISE_2004_CH4_REF_ID}")
    print(f"     Treatise 2004 ch5 ref_id={TREATISE_2004_CH5_REF_ID}")

    # 4. Build taxon index
    print("4. Building taxon index...")
    taxon_index, name_index = build_taxon_index(dst)
    new_taxa_cache = {}
    print(f"   → {len(taxon_index)} indexed taxa")

    # 5. Process default profile sources (JA2002 + Adrain 2011)
    print("5. Processing default profile sources...")
    default_counts = process_source_default(
        dst, taxon_index, name_index, new_taxa_cache)
    dst.commit()
    for k, v in default_counts.items():
        print(f"   → {k}: {v}")

    # 5b. Fallback: canonical parent_id for genera without PLACED_IN
    print("   Fallback: canonical parent_id for unplaced genera...")
    n_fallback = fallback_canonical_parent_id(
        src, dst, taxon_index, name_index, new_taxa_cache)
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

    print("   Processing Treatise 2004 ch4 (Agnostida)...")
    t2004_ch4_edges = process_source_treatise(
        dst, SOURCES / "treatise_2004_ch4.txt", TREATISE_2004_CH4_REF_ID,
        taxon_index, name_index, new_taxa_cache)
    dst.commit()
    print(f"   → {len(t2004_ch4_edges)} edges")

    print("   Processing Treatise 2004 ch5 (Redlichiida)...")
    t2004_ch5_edges = process_source_treatise(
        dst, SOURCES / "treatise_2004_ch5.txt", TREATISE_2004_CH5_REF_ID,
        taxon_index, name_index, new_taxa_cache)
    dst.commit()
    print(f"   → {len(t2004_ch5_edges)} edges")

    # 7. New taxa summary
    if new_taxa_cache:
        print(f"\n   New taxa created: {len(new_taxa_cache)}")

    # 8. Build profiles
    print("\n7. Building classification profiles...")
    profile_counts = build_profiles(dst, t1959_edges,
                                    t2004_ch4_edges, t2004_ch5_edges)
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
    placed_in_accepted = dst.execute(
        "SELECT COUNT(*) FROM assertion WHERE predicate='PLACED_IN' AND is_accepted=1"
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
    print(f"    PLACED_IN:          {placed_in} (accepted: {placed_in_accepted})")
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
