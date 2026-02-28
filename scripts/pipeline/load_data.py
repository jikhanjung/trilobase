"""Step 4: Schema creation + data loading.

Creates the trilobase.db with final schema, then loads:
  - temporal_ranges (28 entries)
  - taxonomic_ranks (hierarchy + genera)
  - taxonomic_opinions (PLACED_IN + SYNONYM_OF + SPELLING_OF)
  - bibliography
  - taxon_bibliography
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from .hierarchy import HierarchyNode
from .parse_genera import GenusRecord

# ---------------------------------------------------------------------------
# Temporal Ranges (28 entries)
# ---------------------------------------------------------------------------

TEMPORAL_RANGES = [
    ('LCAM', 'Lower Cambrian', 'Cambrian', 'Lower', 538.8, 509.0),
    ('MCAM', 'Middle Cambrian', 'Cambrian', 'Middle', 509.0, 497.0),
    ('UCAM', 'Upper Cambrian', 'Cambrian', 'Upper', 497.0, 485.4),
    ('MUCAM', 'Middle-Upper Cambrian', 'Cambrian', 'Middle-Upper', 509.0, 485.4),
    ('LMCAM', 'Lower-Middle Cambrian', 'Cambrian', 'Lower-Middle', 538.8, 497.0),
    ('CAM', 'Cambrian', 'Cambrian', None, 538.8, 485.4),
    ('LORD', 'Lower Ordovician', 'Ordovician', 'Lower', 485.4, 470.0),
    ('MORD', 'Middle Ordovician', 'Ordovician', 'Middle', 470.0, 458.4),
    ('UORD', 'Upper Ordovician', 'Ordovician', 'Upper', 458.4, 443.8),
    ('LMORD', 'Lower-Middle Ordovician', 'Ordovician', 'Lower-Middle', 485.4, 458.4),
    ('MUORD', 'Middle-Upper Ordovician', 'Ordovician', 'Middle-Upper', 470.0, 443.8),
    ('ORD', 'Ordovician', 'Ordovician', None, 485.4, 443.8),
    ('LSIL', 'Lower Silurian', 'Silurian', 'Lower', 443.8, 433.4),
    ('USIL', 'Upper Silurian', 'Silurian', 'Upper', 433.4, 419.2),
    ('LUSIL', 'Lower-Upper Silurian', 'Silurian', 'Lower-Upper', 443.8, 419.2),
    ('SIL', 'Silurian', 'Silurian', None, 443.8, 419.2),
    ('LDEV', 'Lower Devonian', 'Devonian', 'Lower', 419.2, 393.3),
    ('MDEV', 'Middle Devonian', 'Devonian', 'Middle', 393.3, 382.7),
    ('UDEV', 'Upper Devonian', 'Devonian', 'Upper', 382.7, 358.9),
    ('LMDEV', 'Lower-Middle Devonian', 'Devonian', 'Lower-Middle', 419.2, 382.7),
    ('MUDEV', 'Middle-Upper Devonian', 'Devonian', 'Middle-Upper', 393.3, 358.9),
    ('EDEV', 'Early Devonian', 'Devonian', 'Early', 419.2, 393.3),
    ('MISS', 'Mississippian', 'Carboniferous', 'Mississippian', 358.9, 323.2),
    ('PENN', 'Pennsylvanian', 'Carboniferous', 'Pennsylvanian', 323.2, 298.9),
    ('LPERM', 'Lower Permian', 'Permian', 'Lower', 298.9, 272.95),
    ('PERM', 'Permian', 'Permian', None, 298.9, 251.9),
    ('UPERM', 'Upper Permian', 'Permian', 'Upper', 259.51, 251.9),
    ('INDET', 'Indeterminate', None, None, None, None),
]

# Synonym priority for determining is_accepted among duplicates
SYNONYM_PRIORITY = {
    'j.s.s.': 5,
    'j.o.s.': 4,
    'suppressed': 3,
    'replacement': 2,
    'preocc.': 1,
}

# Families that use SPELLING_OF → canonical name mapping
SPELLING_OF_MAP = {
    'Dokimocephalidae': 'Dokimokephalidae',
    'Chengkouaspidae': 'Chengkouaspididae',
}

# Families for ? and ?? placement
QUESTIONABLE_FAMILIES = set()  # populated from genus list data

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

SCHEMA_DDL = """
CREATE TABLE temporal_ranges (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT,
    period TEXT,
    epoch TEXT,
    start_mya REAL,
    end_mya REAL
);

CREATE TABLE taxonomic_ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    rank TEXT NOT NULL,
    parent_id INTEGER,
    author TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    genera_count INTEGER DEFAULT 0,
    year TEXT,
    year_suffix TEXT,
    type_species TEXT,
    type_species_author TEXT,
    formation TEXT,
    location TEXT,
    temporal_code TEXT,
    is_valid INTEGER DEFAULT 1,
    raw_entry TEXT,
    family TEXT,
    uid TEXT,
    uid_method TEXT,
    uid_confidence TEXT,
    same_as_uid TEXT,
    is_placeholder INTEGER DEFAULT 0,
    FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id)
);
CREATE UNIQUE INDEX idx_taxonomic_ranks_uid ON taxonomic_ranks(uid);

CREATE TABLE taxonomic_opinions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
    opinion_type TEXT NOT NULL
        CHECK(opinion_type IN ('PLACED_IN','VALID_AS','SYNONYM_OF','SPELLING_OF')),
    related_taxon_id INTEGER REFERENCES taxonomic_ranks(id),
    proposed_valid INTEGER,
    bibliography_id INTEGER REFERENCES bibliography(id),
    assertion_status TEXT DEFAULT 'asserted'
        CHECK(assertion_status IN ('asserted','incertae_sedis','questionable','indet')),
    curation_confidence TEXT DEFAULT 'high'
        CHECK(curation_confidence IN ('high','medium','low')),
    is_accepted INTEGER DEFAULT 0,
    synonym_type TEXT
        CHECK(synonym_type IS NULL OR synonym_type IN
            ('j.s.s.','j.o.s.','preocc.','replacement','suppressed')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_opinions_taxon ON taxonomic_opinions(taxon_id);
CREATE INDEX idx_opinions_type ON taxonomic_opinions(opinion_type);
CREATE UNIQUE INDEX idx_unique_accepted_opinion
    ON taxonomic_opinions(taxon_id, opinion_type) WHERE is_accepted = 1;

-- Triggers for PLACED_IN parent_id sync
CREATE TRIGGER trg_deactivate_before_insert
BEFORE INSERT ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
BEGIN
    UPDATE taxonomic_opinions SET is_accepted = 0
    WHERE taxon_id = NEW.taxon_id AND opinion_type = 'PLACED_IN' AND is_accepted = 1;
END;

CREATE TRIGGER trg_sync_parent_insert
AFTER INSERT ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
BEGIN
    UPDATE taxonomic_ranks SET parent_id = NEW.related_taxon_id
    WHERE id = NEW.taxon_id;
END;

CREATE TRIGGER trg_deactivate_before_update
BEFORE UPDATE OF is_accepted ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
BEGIN
    UPDATE taxonomic_opinions SET is_accepted = 0
    WHERE taxon_id = NEW.taxon_id AND opinion_type = 'PLACED_IN'
      AND is_accepted = 1 AND id != NEW.id;
END;

CREATE TRIGGER trg_sync_parent_update
AFTER UPDATE OF is_accepted ON taxonomic_opinions
WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
BEGIN
    UPDATE taxonomic_ranks SET parent_id = NEW.related_taxon_id
    WHERE id = NEW.taxon_id;
END;

CREATE TABLE bibliography (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uid TEXT,
    uid_method TEXT,
    uid_confidence TEXT,
    same_as_uid TEXT
);
CREATE INDEX idx_bibliography_authors ON bibliography(authors);
CREATE INDEX idx_bibliography_year ON bibliography(year);
CREATE UNIQUE INDEX idx_bibliography_uid ON bibliography(uid);

CREATE TABLE taxon_bibliography (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    taxon_id INTEGER NOT NULL,
    bibliography_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL DEFAULT 'original_description'
        CHECK(relationship_type IN ('original_description','fide')),
    opinion_id INTEGER,
    match_confidence TEXT NOT NULL DEFAULT 'high'
        CHECK(match_confidence IN ('high','medium','low')),
    match_method TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (taxon_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (bibliography_id) REFERENCES bibliography(id),
    FOREIGN KEY (opinion_id) REFERENCES taxonomic_opinions(id),
    UNIQUE(taxon_id, bibliography_id, relationship_type, opinion_id)
);
CREATE INDEX idx_tb_taxon ON taxon_bibliography(taxon_id);
CREATE INDEX idx_tb_bib ON taxon_bibliography(bibliography_id);
CREATE INDEX idx_tb_type ON taxon_bibliography(relationship_type);

CREATE TABLE genus_formations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genus_id INTEGER NOT NULL,
    formation_id INTEGER NOT NULL,
    is_type_locality INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (formation_id) REFERENCES formations(id),
    UNIQUE(genus_id, formation_id)
);
CREATE INDEX idx_genus_formations_genus ON genus_formations(genus_id);
CREATE INDEX idx_genus_formations_formation ON genus_formations(formation_id);

CREATE TABLE genus_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genus_id INTEGER NOT NULL,
    country_id INTEGER NOT NULL,
    region TEXT,
    is_type_locality INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    region_id INTEGER REFERENCES geographic_regions(id),
    FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
    FOREIGN KEY (country_id) REFERENCES countries(id),
    UNIQUE(genus_id, country_id, region)
);
CREATE INDEX idx_genus_locations_genus ON genus_locations(genus_id);
CREATE INDEX idx_genus_locations_country ON genus_locations(country_id);
CREATE INDEX idx_genus_locations_region ON genus_locations(region_id);

CREATE TABLE user_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    annotation_type TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_annotations_entity ON user_annotations(entity_type, entity_id);

-- Backward-compat views
CREATE VIEW taxa AS SELECT * FROM taxonomic_ranks WHERE rank = 'Genus';

CREATE VIEW synonyms AS
SELECT o.id,
       o.taxon_id AS junior_taxon_id,
       rt.name AS senior_taxon_name,
       o.related_taxon_id AS senior_taxon_id,
       o.synonym_type,
       b.authors AS fide_author,
       CAST(b.year AS TEXT) AS fide_year,
       o.notes
FROM taxonomic_opinions o
LEFT JOIN taxonomic_ranks rt ON o.related_taxon_id = rt.id
LEFT JOIN bibliography b ON o.bibliography_id = b.id
WHERE o.opinion_type = 'SYNONYM_OF';
"""


# ---------------------------------------------------------------------------
# Hierarchy loading
# ---------------------------------------------------------------------------

def _load_hierarchy(conn: sqlite3.Connection,
                    nodes: list[HierarchyNode]) -> dict[str, int]:
    """Insert hierarchy nodes into taxonomic_ranks.

    Returns name → id mapping for family lookup.
    """
    cur = conn.cursor()
    name_to_id: dict[str, int] = {}

    for node in nodes:
        parent_id = name_to_id.get(node.parent_name) if node.parent_name else None

        year_str = str(node.year) if node.year else None
        cur.execute("""
            INSERT INTO taxonomic_ranks
                (name, rank, parent_id, author, year, year_suffix,
                 notes, is_placeholder, genera_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            node.name, node.rank, parent_id, node.author,
            year_str, node.year_suffix,
            node.notes, node.is_placeholder,
        ))
        node_id = cur.lastrowid
        name_to_id[node.name] = node_id

    conn.commit()
    return name_to_id


# ---------------------------------------------------------------------------
# Genus loading
# ---------------------------------------------------------------------------

# Family name typos in the source text
FAMILY_TYPOS = {
    'DORYPGIDAE': 'DORYPYGIDAE',
}


def _build_family_lookup(name_to_id: dict[str, int]) -> dict[str, int]:
    """Build a case-insensitive family lookup from name_to_id.

    Genus records use UPPERCASE family names (e.g., 'PROETIDAE') while
    hierarchy nodes use title case (e.g., 'Proetidae').

    Also redirects SPELLING_OF variant families (e.g., Dokimocephalidae
    → Dokimokephalidae) so genera assigned to the variant family in the
    source text get the canonical family's id.
    """
    lookup: dict[str, int] = {}
    for name, nid in name_to_id.items():
        lookup[name] = nid
        lookup[name.upper()] = nid

    # Redirect SPELLING_OF variants → canonical family id
    for variant, canonical in SPELLING_OF_MAP.items():
        canonical_id = name_to_id.get(canonical)
        if canonical_id:
            lookup[variant] = canonical_id
            lookup[variant.upper()] = canonical_id

    return lookup


def _resolve_family_id(family_text: str | None,
                       family_lookup: dict[str, int],
                       ) -> tuple[int | None, str | None]:
    """Resolve genus family text to (parent_id, assertion_status).

    Returns (parent_id, assertion_status) where assertion_status is:
      None = normal placement
      'questionable' = ?FAMILY or ??FAMILY
      'incertae_sedis' = FAMILY UNCERTAIN
      'indet' = INDET
    """
    if not family_text:
        return None, None

    family = family_text.strip()

    # Apply known typo corrections
    family = FAMILY_TYPOS.get(family, family)

    # ??FAMILY or ?FAMILY or FAMILY? → questionable
    if family.startswith('??') or family.startswith('?'):
        clean_family = FAMILY_TYPOS.get(family.lstrip('?'), family.lstrip('?'))
        fid = family_lookup.get(clean_family)
        return fid, 'questionable'

    if family.endswith('?'):
        clean_family = FAMILY_TYPOS.get(family.rstrip('?'), family.rstrip('?'))
        fid = family_lookup.get(clean_family)
        return fid, 'questionable'

    if family == 'UNCERTAIN':
        fid = family_lookup.get('UNCERTAIN')
        return fid, None  # No opinion, just parent_id

    if family == 'INDET':
        fid = family_lookup.get('INDET')
        return fid, None  # No opinion, just parent_id

    # NEKTASPIDA — special pseudo-family
    if family == 'NEKTASPIDA':
        fid = family_lookup.get('NEKTASPIDA')
        return fid, None

    # Normal family lookup (case-insensitive via prebuilt map)
    fid = family_lookup.get(family)
    return fid, None


def _load_genera(conn: sqlite3.Connection,
                 genera: list[GenusRecord],
                 name_to_id: dict[str, int],
                 ) -> dict[str, int]:
    """Insert genus records into taxonomic_ranks.

    Also creates PLACED_IN opinions for special family assignments.
    Returns genus_name → id mapping.
    """
    cur = conn.cursor()
    genus_name_to_id: dict[str, int] = {}
    trilobita_id = name_to_id.get('Trilobita')
    family_lookup = _build_family_lookup(name_to_id)

    for rec in genera:
        parent_id, assertion = _resolve_family_id(rec.family, family_lookup)

        year_str = str(rec.year) if rec.year else None
        cur.execute("""
            INSERT INTO taxonomic_ranks
                (name, rank, parent_id, author, year, year_suffix,
                 type_species, type_species_author, formation, location,
                 family, temporal_code, is_valid, raw_entry)
            VALUES (?, 'Genus', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec.name, parent_id, rec.author, year_str, rec.year_suffix,
            rec.type_species, rec.type_species_author,
            rec.formation, rec.location,
            rec.family, rec.temporal_code, rec.is_valid, rec.raw_entry,
        ))
        genus_id = cur.lastrowid
        genus_name_to_id[rec.name] = genus_id
        name_to_id[rec.name] = genus_id

        # Create PLACED_IN opinions only for ?FAMILY / ??FAMILY (questionable)
        # Skip for invalid genera (they don't get PLACED_IN in reference DB)
        if assertion == 'questionable' and parent_id and rec.is_valid == 1:
            cur.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id,
                     assertion_status, is_accepted)
                VALUES (?, 'PLACED_IN', ?, 'questionable', 1)
            """, (genus_id, parent_id))

    conn.commit()
    return genus_name_to_id


# ---------------------------------------------------------------------------
# Synonym → Opinions
# ---------------------------------------------------------------------------

def _load_synonym_opinions(conn: sqlite3.Connection,
                           genera: list[GenusRecord],
                           name_to_id: dict[str, int]):
    """Create SYNONYM_OF opinions from parsed synonym data.

    Handles duplicate synonyms per taxon using SYNONYM_PRIORITY.
    """
    cur = conn.cursor()

    # Group synonyms by taxon for duplicate handling
    taxon_synonyms: dict[int, list[tuple[GenusRecord, 'SynonymInfo']]] = {}

    for rec in genera:
        genus_id = name_to_id.get(rec.name)
        if not genus_id or not rec.synonyms:
            continue
        if genus_id not in taxon_synonyms:
            taxon_synonyms[genus_id] = []
        for syn in rec.synonyms:
            taxon_synonyms[genus_id].append((rec, syn))

    for genus_id, syn_list in taxon_synonyms.items():
        # When a genus has both preocc./suppressed (no senior name) AND
        # j.s.s./j.o.s. (with senior name), enrich the preocc./suppressed
        # with the senior name from the informative entry.
        # The reference DB keeps both as separate opinions.
        syn_types = {s.type for _, s in syn_list}
        has_informative = syn_types & {'j.s.s.', 'j.o.s.'}
        if has_informative and len(syn_list) > 1:
            # Find the senior name from the informative entry
            informative_senior = None
            for _, s in syn_list:
                if s.type in ('j.s.s.', 'j.o.s.') and s.senior_name:
                    informative_senior = s.senior_name
                    break
            # Enrich preocc./suppressed entries that lack a senior name
            if informative_senior:
                for _, s in syn_list:
                    if s.type in ('preocc.', 'suppressed') and not s.senior_name:
                        s.senior_name = informative_senior

        # Drop preocc./suppressed without senior_name when another preocc./suppressed
        # already has a senior_name (e.g., Hausmannia: override provides preocc.(Odontochile),
        # so the second entry's "preocc., not replaced" is redundant).
        # But keep multiple preocc. with DIFFERENT senior names (e.g., Boeckia: two homonyms).
        has_preocc_with_senior = any(
            s.type in ('preocc.', 'suppressed') and s.senior_name
            for _, s in syn_list
        )
        if has_preocc_with_senior:
            syn_list = [
                (rec, syn) for rec, syn in syn_list
                if not (syn.type in ('preocc.', 'suppressed') and not syn.senior_name)
            ]

        # Determine which synonym gets is_accepted=1
        # (highest priority per SYNONYM_PRIORITY)
        best_priority = -1
        best_idx = 0
        for i, (rec, syn) in enumerate(syn_list):
            p = SYNONYM_PRIORITY.get(syn.type, 0)
            if p > best_priority:
                best_priority = p
                best_idx = i

        for i, (rec, syn) in enumerate(syn_list):
            # D3: case-insensitive senior name lookup
            related_id = None
            if syn.senior_name:
                related_id = name_to_id.get(syn.senior_name)
                if not related_id:
                    # Try title case (SPHAEREXOCHUS → Sphaerexochus)
                    related_id = name_to_id.get(syn.senior_name.title())
            is_accepted = 1 if i == best_idx else 0

            # Build notes from fide info if not linked to bibliography
            notes = None
            if syn.fide_author and syn.fide_year:
                notes = f'fide {syn.fide_author}, {syn.fide_year}'
            elif syn.fide_author:
                notes = f'fide {syn.fide_author}'

            cur.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id,
                     synonym_type, is_accepted, notes)
                VALUES (?, 'SYNONYM_OF', ?, ?, ?, ?)
            """, (genus_id, related_id, syn.type, is_accepted, notes))

    conn.commit()


# ---------------------------------------------------------------------------
# SPELLING_OF opinions
# ---------------------------------------------------------------------------

def _load_spelling_opinions(conn: sqlite3.Connection,
                            name_to_id: dict[str, int]):
    """Create SPELLING_OF opinions for orthographic variant placeholders."""
    cur = conn.cursor()
    for variant, canonical in SPELLING_OF_MAP.items():
        variant_id = name_to_id.get(variant)
        canonical_id = name_to_id.get(canonical)
        if variant_id and canonical_id:
            cur.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id,
                     is_accepted, assertion_status)
                VALUES (?, 'SPELLING_OF', ?, 1, 'asserted')
            """, (variant_id, canonical_id))
    conn.commit()


# ---------------------------------------------------------------------------
# Agnostida PLACED_IN opinions
# ---------------------------------------------------------------------------

def _load_agnostida_opinions(conn: sqlite3.Connection,
                             name_to_id: dict[str, int],
                             adrain_bib_id: int | None):
    """Create special PLACED_IN opinions for Agnostida Order.

    JA2002 placed Agnostida in Trilobita; A2011 excluded it.
    """
    cur = conn.cursor()
    agnostida_id = name_to_id.get('Agnostida')
    trilobita_id = name_to_id.get('Trilobita')
    if not agnostida_id:
        return

    # JA2002 opinion (not accepted): placed in Trilobita
    cur.execute("""
        INSERT INTO taxonomic_opinions
            (taxon_id, opinion_type, related_taxon_id,
             assertion_status, is_accepted,
             notes)
        VALUES (?, 'PLACED_IN', ?, 'asserted', 0,
                'Jell & Adrain (2002) included Agnostida in Trilobita.')
    """, (agnostida_id, trilobita_id))

    # A2011 opinion (accepted): excluded from Trilobita (parent_id=NULL)
    cur.execute("""
        INSERT INTO taxonomic_opinions
            (taxon_id, opinion_type, related_taxon_id,
             bibliography_id, assertion_status, is_accepted,
             notes)
        VALUES (?, 'PLACED_IN', NULL, ?, 'asserted', 1,
                'Adrain (2011) excluded Agnostida from Trilobita sensu stricto.')
    """, (agnostida_id, adrain_bib_id))

    # Set Agnostida parent_id = NULL (trigger should handle this, but ensure)
    cur.execute("UPDATE taxonomic_ranks SET parent_id = NULL WHERE id = ?",
                (agnostida_id,))

    # Agnostida family PLACED_IN Agnostina (conventional placement)
    agnostina_id = name_to_id.get('Agnostina')
    if agnostina_id:
        from .hierarchy import AGNOSTIDA_FAMILIES
        for fam_name, _ in AGNOSTIDA_FAMILIES:
            fam_id = name_to_id.get(fam_name)
            if fam_id:
                cur.execute("""
                    INSERT INTO taxonomic_opinions
                        (taxon_id, opinion_type, related_taxon_id,
                         assertion_status, is_accepted, notes)
                    VALUES (?, 'PLACED_IN', ?, 'asserted', 1,
                            'Conventional placement; not explicitly stated in Jell & Adrain (2002)')
                """, (fam_id, agnostina_id))

    conn.commit()


# ---------------------------------------------------------------------------
# UNCERTAIN / INDET genus PLACED_IN opinions
# ---------------------------------------------------------------------------

# Suborder → higher taxon mapping for FAMILY UNCERTAIN genera
_SUBORDER_NAMES = {'AGNOSTINA', 'REDLICHIINA', 'OLENELLINA'}


def _load_uncertain_opinions(conn: sqlite3.Connection,
                             genera: list[GenusRecord],
                             name_to_id: dict[str, int]):
    """Create PLACED_IN opinions for SUBORDER FAMILY UNCERTAIN genera.

    Only creates opinions for genera whose family field is a recognized
    suborder (AGNOSTINA, REDLICHIINA, OLENELLINA) with UNCERTAIN qualifier.
    INDET and plain UNCERTAIN genera just have parent_id pointing to their
    pseudo-family nodes (handled by _resolve_family_id), no opinions.
    """
    cur = conn.cursor()
    count = 0

    for rec in genera:
        if rec.is_valid == 0:
            continue
        if rec.family_qualifier != 'UNCERTAIN':
            continue
        if not rec.family or rec.family.upper() not in _SUBORDER_NAMES:
            continue

        genus_id = name_to_id.get(rec.name)
        if not genus_id:
            continue

        # SUBORDER FAMILY UNCERTAIN → incertae_sedis
        parent_id = name_to_id.get(rec.family.title())
        if not parent_id:
            parent_id = name_to_id.get(rec.family)
        if parent_id:
            cur.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id,
                     assertion_status, is_accepted)
                VALUES (?, 'PLACED_IN', ?, 'incertae_sedis', 1)
            """, (genus_id, parent_id))
            count += 1

    conn.commit()
    print(f'    {count} suborder-uncertain PLACED_IN opinions created')


# Manual PLACED_IN opinions from reference DB curation (devlog 088).
# These genera have normal family assignments in the source text but were
# reclassified as indeterminate or questionable in the reference DB.
_MANUAL_PLACED_IN = {
    # genus_name: (related_taxon_name, assertion_status)
    'Apheloides': ('Trilobita', 'indet'),
    'Ceratolithus': ('Trilobita', 'indet'),
    'Dimeropyge': ('Trilobita', 'indet'),
    'Elicicola': ('Trilobita', 'indet'),
    'Emanuelina': ('Trilobita', 'indet'),
    'Glyphaspis': ('Trilobita', 'indet'),
    'Hundwarella': ('Trilobita', 'indet'),
    'Kochina': ('Trilobita', 'indet'),
    'Menevia': ('Trilobita', 'indet'),
    'Mexicella': ('Trilobita', 'indet'),
    'Neimonggolaspis': ('Trilobita', 'indet'),
    'Neopsilocephalina': ('Trilobita', 'indet'),
    'Phaeton': ('Trilobita', 'indet'),
    'Triadaspis': ('Trilobita', 'indet'),
    'Costapyge': ('Trilobita', 'questionable'),
}

_MANUAL_FAMILY_PLACED_IN = [
    # (family_name, related_taxon_name, assertion_status)
    ('Eurekiidae', 'Uncertain', 'incertae_sedis'),
    ('Eurekiidae', 'Asaphida', 'asserted'),
]


def _load_manual_placed_in(conn: sqlite3.Connection,
                           name_to_id: dict[str, int]):
    """Create manually curated PLACED_IN opinions (from devlog 088)."""
    cur = conn.cursor()
    count = 0

    # Genus-level indet/questionable opinions
    for genus_name, (related_name, assertion) in _MANUAL_PLACED_IN.items():
        genus_id = name_to_id.get(genus_name)
        related_id = name_to_id.get(related_name)
        if genus_id and related_id:
            cur.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id,
                     assertion_status, is_accepted)
                VALUES (?, 'PLACED_IN', ?, ?, 1)
            """, (genus_id, related_id, assertion))
            count += 1

    # Family-level opinions (Eurekiidae PoC)
    for fam_name, related_name, assertion in _MANUAL_FAMILY_PLACED_IN:
        fam_id = name_to_id.get(fam_name)
        related_id = name_to_id.get(related_name)
        if fam_id and related_id:
            cur.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id,
                     assertion_status, is_accepted)
                VALUES (?, 'PLACED_IN', ?, ?, 1)
            """, (fam_id, related_id, assertion))
            count += 1

    conn.commit()
    print(f'    {count} manual PLACED_IN opinions created')


# ---------------------------------------------------------------------------
# Bibliography loading
# ---------------------------------------------------------------------------

def _read_and_merge_bibliography(bib_path: Path) -> list[tuple[str, str | None]]:
    """Read Literature Cited file, merge continuation lines.

    Returns list of (raw_text, prev_author).
    """
    lines = bib_path.read_text(encoding='utf-8').splitlines()
    entries: list[tuple[str, str | None]] = []
    current_entry: list[str] = []
    last_author: str | None = None

    for line in lines:
        line = line.rstrip()
        if line.strip() == 'LITERATURE CITED':
            continue
        if not line.strip():
            if current_entry:
                entries.append((' '.join(current_entry), last_author))
                current_entry = []
            continue

        is_new_author = re.match(r'^[A-Z][A-Z]+[,\s]', line)
        is_year_only = re.match(r'^(\d{4})[a-z]?\.?\s', line)
        is_cross_ref = 'see ' in line.lower() and len(line) < 100

        if is_new_author or is_year_only or is_cross_ref:
            if current_entry:
                entries.append((' '.join(current_entry), last_author))
                current_entry = []
            if is_new_author:
                m = re.match(r'^(.+?)\s+\d{4}', line)
                if m:
                    last_author = m.group(1).strip()
            current_entry = [line]
        else:
            current_entry.append(line)

    if current_entry:
        entries.append((' '.join(current_entry), last_author))

    return entries


def _parse_reference(raw_text: str,
                     prev_author: str | None = None) -> dict:
    """Parse a single bibliography reference."""
    result = {
        'authors': None, 'year': None, 'year_suffix': None,
        'title': None, 'journal': None, 'volume': None, 'pages': None,
        'publisher': None, 'city': None, 'editors': None,
        'book_title': None, 'reference_type': 'article',
        'raw_entry': raw_text,
    }
    text = raw_text.strip()

    # Cross-references
    if re.search(r'\bsee\s+[A-Z]', text, re.IGNORECASE):
        result['reference_type'] = 'cross_ref'
        result['authors'] = text
        return result

    # Year-only (same author continuation)
    m = re.match(r'^(\d{4})([a-z])?\.?\s*(.+)$', text)
    if m and prev_author:
        result['authors'] = prev_author
        result['year'] = int(m.group(1))
        result['year_suffix'] = m.group(2)
        remainder = m.group(3)
    else:
        m = re.match(r'^(.+?)\s+(\d{4})([a-z])?\.?\s*(.*)$', text)
        if m:
            result['authors'] = m.group(1).strip()
            result['year'] = int(m.group(2))
            result['year_suffix'] = m.group(3)
            remainder = m.group(4)
        else:
            result['authors'] = text[:100] if len(text) > 100 else text
            return result

    if remainder:
        # Book: (Publisher: City)
        book_match = re.search(r'\(([^:]+):\s*([^)]+)\)', remainder)
        if book_match:
            result['reference_type'] = 'book'
            result['publisher'] = book_match.group(1).strip()
            result['city'] = book_match.group(2).strip()
            result['title'] = remainder[:book_match.start()].strip().rstrip('.')
            pages_match = re.search(r'(\d+p)', remainder[book_match.end():])
            if pages_match:
                result['pages'] = pages_match.group(1)

        # Chapter: Pp. X-Y. In EDITOR (ed.)
        chapter_match = re.search(
            r'[Pp]p?\.?\s*(\d+[-–]\d+).*?In\s+(.+?)\s*\(ed', remainder
        )
        if chapter_match:
            result['reference_type'] = 'chapter'
            result['pages'] = chapter_match.group(1)
            result['editors'] = chapter_match.group(2).strip()
            book_title_match = re.search(
                r'\(eds?\.\)\s*(.+?)(?:\(|$)', remainder
            )
            if book_title_match:
                result['book_title'] = book_title_match.group(1).strip().rstrip('.')

        # Journal article: Journal volume: pages
        if result['reference_type'] == 'article':
            journal_match = re.search(
                r'\.\s*([A-Z][^.]+?)\s+(\d+(?:\([^)]+\))?)\s*:\s*(\d+[-–]\d+)',
                remainder,
            )
            if journal_match:
                result['journal'] = journal_match.group(1).strip()
                result['volume'] = journal_match.group(2)
                result['pages'] = journal_match.group(3)
                title_end = remainder.find(journal_match.group(1))
                if title_end > 0:
                    result['title'] = remainder[:title_end].strip().rstrip('.')
            else:
                title_match = re.match(r'^[\[\(]?(.+?)[\]\)]?\.(?:\s|$)',
                                       remainder)
                if title_match:
                    result['title'] = title_match.group(1).strip()
                else:
                    result['title'] = (remainder[:200]
                                       if len(remainder) > 200 else remainder)

    return result


def _load_bibliography(conn: sqlite3.Connection,
                       bib_path: Path) -> int:
    """Load bibliography from Literature Cited file.

    Returns the bibliography id of Adrain 2011 entry (if found), else None.
    """
    cur = conn.cursor()
    entries = _read_and_merge_bibliography(bib_path)

    last_author = None
    adrain_2011_id = None

    for raw_text, prev_author in entries:
        ref = _parse_reference(raw_text, prev_author or last_author)
        if ref['authors'] and ref['reference_type'] != 'cross_ref':
            last_author = ref['authors']

        cur.execute("""
            INSERT INTO bibliography
                (authors, year, year_suffix, title, journal, volume, pages,
                 publisher, city, editors, book_title, reference_type, raw_entry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ref['authors'], ref['year'], ref['year_suffix'],
            ref['title'], ref['journal'], ref['volume'], ref['pages'],
            ref['publisher'], ref['city'], ref['editors'],
            ref['book_title'], ref['reference_type'], ref['raw_entry'],
        ))

    conn.commit()

    # Also insert the Adrain 2011 entry if not already present
    cur.execute("SELECT id FROM bibliography WHERE authors LIKE '%ADRAIN%' AND year = 2011")
    row = cur.fetchone()
    if row:
        adrain_2011_id = row[0]
    else:
        # Insert manually
        cur.execute("""
            INSERT INTO bibliography (authors, year, title, reference_type, raw_entry)
            VALUES ('ADRAIN, J.M.', 2011,
                    'Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification. Zootaxa 3148: 104-109.',
                    'chapter',
                    'ADRAIN, J.M. 2011. Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification. Zootaxa 3148: 104-109.')
        """)
        adrain_2011_id = cur.lastrowid
        conn.commit()

    return adrain_2011_id


# ---------------------------------------------------------------------------
# taxon_bibliography linking
# ---------------------------------------------------------------------------

def _extract_surnames(author: str) -> set[str]:
    """Extract surname(s) from taxonomic_ranks.author field."""
    if not author:
        return set()

    # Strip "in ..." part
    in_match = re.match(r'^(.+?)\s+in\s+', author, re.IGNORECASE)
    if in_match:
        author = in_match.group(1)

    # Strip "et al."
    author = re.sub(r'\s+et\s+al\.?', '', author, flags=re.IGNORECASE)

    # Split on & or ,
    parts = re.split(r'\s*[&,]\s*', author)
    surnames = set()
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # Remove initials (single uppercase letters followed by .)
        p = re.sub(r'\b[A-Z]\.\s*', '', p).strip()
        # Take last word as surname
        words = p.split()
        if words:
            surnames.add(words[-1].upper())
    return surnames


def _extract_bib_surnames(authors: str) -> set[str]:
    """Extract surname(s) from bibliography.authors field.

    Bibliography format: "SURNAME, INITIALS & SURNAME2, INITIALS2"
    Split on & first for co-authors, then take surname (before comma).
    """
    if not authors:
        return set()
    # Skip cross-refs
    if re.match(r'^.*\bsee\b', authors, re.IGNORECASE):
        return set()

    # Split on & for co-authors
    coauthors = re.split(r'\s*&\s*', authors)
    surnames = set()
    for part in coauthors:
        part = part.strip()
        if not part:
            continue
        # Each co-author is "SURNAME, INITIALS" — take text before first comma
        comma_pos = part.find(',')
        if comma_pos > 0:
            name = part[:comma_pos].strip()
        else:
            # No comma — might be just a surname
            name = part.split()[0] if part.split() else ''
        name = name.rstrip(',').strip()
        if name and len(name) > 2:  # Skip single initials
            surnames.add(name.upper())
    return surnames


def _build_bib_index(conn: sqlite3.Connection,
                     ) -> dict[tuple[frozenset, int], list[dict]]:
    """Build (surname_set, year) → [bib entries] lookup."""
    cur = conn.cursor()
    cur.execute("SELECT id, authors, year, year_suffix, reference_type FROM bibliography")

    index: dict[tuple[frozenset, int], list[dict]] = {}
    for bib_id, authors, year, year_suffix, ref_type in cur.fetchall():
        if ref_type == 'cross_ref':
            continue
        if not year:
            continue
        surnames = _extract_bib_surnames(authors)
        if not surnames:
            continue
        key = (frozenset(surnames), year)
        if key not in index:
            index[key] = []
        index[key].append({
            'id': bib_id, 'year_suffix': year_suffix, 'authors': authors,
        })

    return index


def _match_taxon_to_bib(author: str, year: int, year_suffix: str | None,
                        bib_index: dict,
                        ) -> list[tuple[int, str, str]]:
    """Match taxon author/year to bibliography.

    Returns [(bib_id, confidence, method)].
    """
    if not author or not year:
        return []

    surnames = _extract_surnames(author)
    if not surnames:
        return []

    key = (frozenset(surnames), year)
    candidates = bib_index.get(key, [])
    if not candidates:
        return []

    if len(candidates) == 1:
        return [(candidates[0]['id'], 'high', 'unique_match')]

    # Try year_suffix disambiguation
    if year_suffix:
        exact = [c for c in candidates if c['year_suffix'] == year_suffix]
        if len(exact) == 1:
            return [(exact[0]['id'], 'high', 'suffix_disambiguated')]

    # No suffix, check if only one has no suffix
    no_suffix = [c for c in candidates if not c['year_suffix']]
    if len(no_suffix) == 1 and not year_suffix:
        return [(no_suffix[0]['id'], 'high', 'no_suffix_unique')]

    # Ambiguous — skip
    return []


def _match_fide_to_bib(fide_author: str | None, fide_year: str | None,
                       bib_index: dict,
                       ) -> list[tuple[int, str, str]]:
    """Match fide author/year to bibliography."""
    if not fide_author:
        return []

    # Skip special cases
    lower = fide_author.lower()
    if 'herein' in lower or 'pers. comm' in lower:
        return []

    # Parse fide_author for surnames
    author = fide_author
    author = re.sub(r'\s+et\s+al\.?', '', author, flags=re.IGNORECASE)
    surnames = set()
    parts = re.split(r'\s*[&,]\s*', author)
    for p in parts:
        p = p.strip()
        if p:
            # Remove initials
            p = re.sub(r'\b[A-Z]\.\s*', '', p).strip()
            words = p.split()
            if words:
                surnames.add(words[-1].upper())

    if not surnames or not fide_year:
        return []

    try:
        year = int(fide_year[:4])
    except (ValueError, TypeError):
        return []

    year_suffix = fide_year[4:] if len(fide_year) > 4 else None

    key = (frozenset(surnames), year)
    candidates = bib_index.get(key, [])
    if not candidates:
        return []

    if len(candidates) == 1:
        return [(candidates[0]['id'], 'high', 'unique_match')]

    if year_suffix:
        exact = [c for c in candidates if c['year_suffix'] == year_suffix]
        if len(exact) == 1:
            return [(exact[0]['id'], 'high', 'suffix_disambiguated')]

    return []


def _link_bibliography(conn: sqlite3.Connection,
                       genera: list[GenusRecord],
                       name_to_id: dict[str, int]):
    """Create taxon_bibliography links for original descriptions and fide."""
    cur = conn.cursor()
    bib_index = _build_bib_index(conn)

    # Opinion id lookup for fide links
    opinion_map: dict[int, int] = {}  # genus_id → first SYNONYM_OF opinion id
    cur.execute("""
        SELECT id, taxon_id FROM taxonomic_opinions
        WHERE opinion_type = 'SYNONYM_OF'
        ORDER BY id
    """)
    for op_id, taxon_id in cur.fetchall():
        if taxon_id not in opinion_map:
            opinion_map[taxon_id] = op_id

    for rec in genera:
        genus_id = name_to_id.get(rec.name)
        if not genus_id or not rec.year:
            continue

        # Original description link
        matches = _match_taxon_to_bib(
            rec.author, rec.year, rec.year_suffix, bib_index
        )
        for bib_id, confidence, method in matches:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO taxon_bibliography
                        (taxon_id, bibliography_id, relationship_type,
                         match_confidence, match_method)
                    VALUES (?, ?, 'original_description', ?, ?)
                """, (genus_id, bib_id, confidence, method))
            except sqlite3.IntegrityError:
                pass

        # Fide links
        for syn in rec.synonyms:
            if syn.fide_author:
                fide_matches = _match_fide_to_bib(
                    syn.fide_author, syn.fide_year, bib_index
                )
                op_id = opinion_map.get(genus_id)
                for bib_id, confidence, method in fide_matches:
                    try:
                        cur.execute("""
                            INSERT OR IGNORE INTO taxon_bibliography
                                (taxon_id, bibliography_id, relationship_type,
                                 opinion_id, match_confidence, match_method)
                            VALUES (?, ?, 'fide', ?, ?, ?)
                        """, (genus_id, bib_id, op_id, confidence, method))
                    except sqlite3.IntegrityError:
                        pass

    conn.commit()


# ---------------------------------------------------------------------------
# Genera count update
# ---------------------------------------------------------------------------

def _update_genera_counts(conn: sqlite3.Connection):
    """Update genera_count for all non-Genus ranks."""
    cur = conn.cursor()
    # Direct children count for Families
    cur.execute("""
        UPDATE taxonomic_ranks SET genera_count = (
            SELECT COUNT(*) FROM taxonomic_ranks g
            WHERE g.parent_id = taxonomic_ranks.id AND g.rank = 'Genus'
        ) WHERE rank = 'Family'
    """)
    # For higher ranks, sum of all descendant genera
    # Use iterative approach: Superfamily, Suborder, Order, Class
    for parent_rank in ['Superfamily', 'Suborder', 'Order', 'Class']:
        cur.execute(f"""
            UPDATE taxonomic_ranks SET genera_count = (
                SELECT COALESCE(SUM(child.genera_count), 0)
                FROM taxonomic_ranks child
                WHERE child.parent_id = taxonomic_ranks.id
            ) WHERE rank = ?
        """, (parent_rank,))
    conn.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_all(db_path: Path,
             hierarchy_nodes: list[HierarchyNode],
             genera: list[GenusRecord],
             bib_path: Path) -> dict[str, int]:
    """Create and populate trilobase.db.

    Returns the complete name → id mapping.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")  # Enable after all inserts

    # 1. Create schema
    conn.executescript(SCHEMA_DDL)

    # 2. Temporal ranges
    conn.executemany(
        "INSERT INTO temporal_ranges (code, name, period, epoch, start_mya, end_mya) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        TEMPORAL_RANGES,
    )
    conn.commit()

    # 3. Hierarchy nodes
    print('  [load_data] Loading hierarchy...')
    name_to_id = _load_hierarchy(conn, hierarchy_nodes)
    print(f'    {len(name_to_id)} hierarchy nodes loaded')

    # 4. Genera
    print('  [load_data] Loading genera...')
    genus_map = _load_genera(conn, genera, name_to_id)
    print(f'    {len(genus_map)} genera loaded')

    # 5. SYNONYM_OF opinions
    print('  [load_data] Creating synonym opinions...')
    _load_synonym_opinions(conn, genera, name_to_id)

    # 6. SPELLING_OF opinions
    _load_spelling_opinions(conn, name_to_id)

    # 7. Bibliography
    print('  [load_data] Loading bibliography...')
    adrain_bib_id = _load_bibliography(conn, bib_path)
    print(f'    Adrain 2011 bib id: {adrain_bib_id}')

    # 8. Agnostida opinions (needs bibliography loaded first)
    _load_agnostida_opinions(conn, name_to_id, adrain_bib_id)

    # 8b. UNCERTAIN / INDET genus placement opinions
    print('  [load_data] Creating uncertain/indet placement opinions...')
    _load_uncertain_opinions(conn, genera, name_to_id)

    # 8c. Manual PLACED_IN opinions (devlog 088 curation)
    _load_manual_placed_in(conn, name_to_id)

    # 9. taxon_bibliography links
    print('  [load_data] Linking bibliography...')
    _link_bibliography(conn, genera, name_to_id)

    # 10. Update genera counts
    _update_genera_counts(conn)

    # Stats
    cur = conn.cursor()
    for table in ['taxonomic_ranks', 'taxonomic_opinions', 'bibliography',
                  'taxon_bibliography']:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        print(f'    {table}: {cur.fetchone()[0]}')

    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()
    return name_to_id
