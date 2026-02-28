"""Step 5: PaleoCore DB creation.

Creates paleocore.db with all reference tables:
  - countries, formations, temporal_ranges
  - cow_states, country_cow_mapping
  - geographic_regions
  - ics_chronostrat, temporal_ics_mapping
  - SCODA metadata tables
"""
from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

from .parse_genera import GenusRecord

# ---------------------------------------------------------------------------
# COW manual mapping (from import_cow.py)
# ---------------------------------------------------------------------------

MANUAL_MAPPING = {
    'England': (200, 'England → United Kingdom'),
    'Scotland': (200, 'Scotland → United Kingdom'),
    'Wales': (200, 'Wales → United Kingdom'),
    'N Ireland': (200, 'N Ireland → United Kingdom'),
    'N Wales': (200, 'N Wales → United Kingdom'),
    'S Wales': (200, 'S Wales → United Kingdom'),
    'SW Wales': (200, 'SW Wales → United Kingdom'),
    'NW Scotland': (200, 'NW Scotland → United Kingdom'),
    'Devon': (200, 'Devon → United Kingdom'),
    'Alaska': (2, 'Alaska → United States of America'),
    'E Alaska': (2, 'E Alaska → United States of America'),
    'Iowa': (2, 'Iowa → United States of America'),
    'Massachusetts': (2, 'Massachusetts → United States of America'),
    'Missouri': (2, 'Missouri → United States of America'),
    'Pennsylvania': (2, 'Pennsylvania → United States of America'),
    'Tennessee': (2, 'Tennessee → United States of America'),
    'Texas': (2, 'Texas → United States of America'),
    'South Australia': (900, 'South Australia → Australia'),
    'Western Australia': (900, 'Western Australia → Australia'),
    'Australian Capital Territory': (900, 'Australian Capital Territory → Australia'),
    'New Brunswick': (20, 'New Brunswick → Canada'),
    'Ontario': (20, 'Ontario → Canada'),
    'NW Canada': (20, 'NW Canada → Canada'),
    'Sichuan': (710, 'Sichuan → China'),
    'Guangxi': (710, 'Guangxi → China'),
    'Henan': (710, 'Henan → China'),
    'Yakutia': (365, 'Yakutia → Russia'),
    'E Yakutia': (365, 'E Yakutia → Russia'),
    'NE Yakutia': (365, 'NE Yakutia → Russia'),
    'Gorny Altay': (365, 'Gorny Altay → Russia'),
    'Novaya Zemlya': (365, 'Novaya Zemlya → Russia'),
    'Arctic Russia': (365, 'Arctic Russia → Russia'),
    'NW Russian Platform': (365, 'NW Russian Platform → Russia'),
    'N Russia': (365, 'N Russia → Russia'),
    'NE Russia': (365, 'NE Russia → Russia'),
    'E Urals': (365, 'E Urals → Russia'),
    'Bavaria': (255, 'Bavaria → Germany'),
    'Eifel Germany': (255, 'Eifel Germany → Germany'),
    'Montagne Noire': (220, 'Montagne Noire → France'),
    'Gotland': (380, 'Gotland → Sweden'),
    'Spitsbergen': (385, 'Spitsbergen → Norway'),
    'Sumatra': (850, 'Sumatra → Indonesia'),
    'Timor': (850, 'Timor → Indonesia'),
    'W Malaysia': (820, 'W Malaysia → Malaysia'),
    'NW Malaya': (820, 'NW Malaya → Malaysia'),
    'USA': (2, 'USA → United States of America'),
    'Burma': (775, 'Burma → Myanmar'),
    'North Vietnam': (816, 'North Vietnam → Vietnam (DRV)'),
    'Luxemburg': (212, 'Luxemburg → Luxembourg'),
    'Tadzikhistan': (702, 'Tadzikhistan → Tajikistan'),
    'Greenland': (390, 'Greenland → Denmark'),
    'E Greenland': (390, 'E Greenland → Denmark'),
    'N Greenland': (390, 'N Greenland → Denmark'),
    'NW Greenland': (390, 'NW Greenland → Denmark'),
    'Central Asia': (None, 'Historical region, no single COW state'),
    'Turkestan': (None, 'Historical region, no single COW state'),
    'Tien-Shan': (None, 'Mountain range spanning multiple states'),
    'Kashmir': (None, 'Disputed territory (India/Pakistan)'),
    'Antarctica': (None, 'No sovereign state'),
}

DIRECTION_PREFIXES = [
    'NW ', 'NE ', 'SW ', 'SE ',
    'N ', 'S ', 'E ', 'W ',
    'Central ', 'Eastern ', 'Western ', 'Northern ', 'Southern ',
]

# Country aliases for geographic_regions
COUNTRY_ALIASES = {
    'USA': 2,
    'Luxemburg': 212,
    'Burma': 775,
    'Tadzikhistan': 702,
}

# Formation type classification suffixes
FORMATION_TYPE_MAP = [
    ('Fm', 'Formation'), ('Lst', 'Limestone'), ('Sh', 'Shale'),
    ('Gp', 'Group'), ('Group', 'Group'), ('Beds', 'Beds'),
    ('Zone', 'Zone'), ('Suite', 'Suite'), ('Horizon', 'Horizon'),
    ('Series', 'Series'), ('Stage', 'Stage'), ('Marl', 'Marl'),
    ('Sst', 'Sandstone'), ('Sandstone', 'Sandstone'), ('Limestone', 'Limestone'),
    ('Shale', 'Shale'), ('Member', 'Member'), ('Mbr', 'Member'),
    ('Congl', 'Conglomerate'), ('Conglomerate', 'Conglomerate'),
    ('Volcanics', 'Volcanics'), ('Quartzite', 'Quartzite'),
    ('Argillite', 'Argillite'), ('Chert', 'Chert'),
    ('Mdst', 'Mudstone'), ('Schiefer', 'Schist'), ('Schicten', 'Formation'),
    ('Schichten', 'Formation'), ('Cgte', 'Conglomerate'), ('Calc', 'Limestone'),
    ('Flags', 'Formation'), ('Grits', 'Formation'), ('Slates', 'Formation'),
]

# Temporal ranges (same as load_data)
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

# ICS temporal mapping
TEMPORAL_MAPPING = {
    'LCAM': [('Terreneuvian', 'partial'), ('CambrianSeries2', 'partial')],
    'MCAM': [('Miaolingian', 'exact')],
    'UCAM': [('Furongian', 'exact')],
    'MUCAM': [('Miaolingian', 'aggregate'), ('Furongian', 'aggregate')],
    'LMCAM': [('Terreneuvian', 'aggregate'), ('CambrianSeries2', 'aggregate'),
              ('Miaolingian', 'aggregate')],
    'CAM': [('Cambrian', 'exact')],
    'LORD': [('LowerOrdovician', 'exact')],
    'MORD': [('MiddleOrdovician', 'exact')],
    'UORD': [('UpperOrdovician', 'exact')],
    'LMORD': [('LowerOrdovician', 'aggregate'), ('MiddleOrdovician', 'aggregate')],
    'MUORD': [('MiddleOrdovician', 'aggregate'), ('UpperOrdovician', 'aggregate')],
    'ORD': [('Ordovician', 'exact')],
    'LSIL': [('Llandovery', 'exact')],
    'USIL': [('Wenlock', 'partial'), ('Ludlow', 'partial'), ('Pridoli', 'partial')],
    'LUSIL': [('Llandovery', 'aggregate'), ('Wenlock', 'aggregate'),
              ('Ludlow', 'aggregate'), ('Pridoli', 'aggregate')],
    'SIL': [('Silurian', 'exact')],
    'LDEV': [('LowerDevonian', 'exact')],
    'MDEV': [('MiddleDevonian', 'exact')],
    'UDEV': [('UpperDevonian', 'exact')],
    'EDEV': [('LowerDevonian', 'exact')],
    'LMDEV': [('LowerDevonian', 'aggregate'), ('MiddleDevonian', 'aggregate')],
    'MUDEV': [('MiddleDevonian', 'aggregate'), ('UpperDevonian', 'aggregate')],
    'MISS': [('Mississippian', 'exact')],
    'PENN': [('Pennsylvanian', 'exact')],
    'LPERM': [('Cisuralian', 'exact')],
    'PERM': [('Permian', 'exact')],
    'UPERM': [('Lopingian', 'exact')],
    'INDET': [],
}


# ---------------------------------------------------------------------------
# Schema DDL for PaleoCore
# ---------------------------------------------------------------------------

PALEOCORE_SCHEMA = """
CREATE TABLE countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT,
    uid TEXT,
    uid_method TEXT,
    uid_confidence TEXT,
    same_as_uid TEXT
);
CREATE UNIQUE INDEX idx_countries_uid ON countries(uid);

CREATE TABLE geographic_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    level TEXT NOT NULL,
    parent_id INTEGER,
    cow_ccode INTEGER,
    uid TEXT,
    uid_method TEXT,
    uid_confidence TEXT,
    same_as_uid TEXT,
    FOREIGN KEY (parent_id) REFERENCES geographic_regions(id)
);
CREATE INDEX idx_geo_parent ON geographic_regions(parent_id);
CREATE INDEX idx_geo_level ON geographic_regions(level);
CREATE UNIQUE INDEX idx_geo_name_parent ON geographic_regions(name, parent_id);
CREATE UNIQUE INDEX idx_geographic_regions_uid ON geographic_regions(uid);

CREATE TABLE cow_states (
    cow_ccode INTEGER NOT NULL,
    abbrev TEXT NOT NULL,
    name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 2024,
    PRIMARY KEY (cow_ccode, start_date)
);

CREATE TABLE country_cow_mapping (
    country_id INTEGER NOT NULL,
    cow_ccode INTEGER,
    parent_name TEXT,
    notes TEXT,
    FOREIGN KEY (country_id) REFERENCES countries(id),
    PRIMARY KEY (country_id)
);

CREATE TABLE formations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    normalized_name TEXT,
    formation_type TEXT,
    country TEXT,
    region TEXT,
    period TEXT,
    uid TEXT,
    uid_method TEXT,
    uid_confidence TEXT,
    same_as_uid TEXT
);
CREATE UNIQUE INDEX idx_formations_uid ON formations(uid);

CREATE TABLE temporal_ranges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT,
    period TEXT,
    epoch TEXT,
    start_mya REAL,
    end_mya REAL,
    uid TEXT,
    uid_method TEXT,
    uid_confidence TEXT,
    same_as_uid TEXT
);
CREATE UNIQUE INDEX idx_temporal_ranges_uid ON temporal_ranges(uid);

CREATE TABLE ics_chronostrat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ics_uri TEXT UNIQUE,
    name TEXT NOT NULL,
    rank TEXT,
    parent_id INTEGER,
    start_mya REAL,
    start_uncertainty REAL,
    end_mya REAL,
    end_uncertainty REAL,
    short_code TEXT,
    color TEXT,
    display_order INTEGER,
    ratified_gssp INTEGER DEFAULT 0,
    uid TEXT,
    uid_method TEXT,
    uid_confidence TEXT,
    same_as_uid TEXT,
    FOREIGN KEY (parent_id) REFERENCES ics_chronostrat(id)
);
CREATE UNIQUE INDEX idx_ics_chronostrat_uid ON ics_chronostrat(uid);

CREATE TABLE temporal_ics_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    temporal_code TEXT NOT NULL,
    ics_id INTEGER NOT NULL,
    mapping_type TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (temporal_code) REFERENCES temporal_ranges(code),
    FOREIGN KEY (ics_id) REFERENCES ics_chronostrat(id)
);
"""


# ---------------------------------------------------------------------------
# Countries
# ---------------------------------------------------------------------------

def _load_countries(conn: sqlite3.Connection,
                    genera: list[GenusRecord]) -> dict[str, int]:
    """Extract unique country names from genera and insert into countries table.

    Returns country_name → id map.
    """
    cur = conn.cursor()
    country_names: set[str] = set()

    for rec in genera:
        if rec.country:
            country_names.add(rec.country)

    for name in sorted(country_names):
        cur.execute("INSERT OR IGNORE INTO countries (name) VALUES (?)", (name,))

    conn.commit()

    cur.execute("SELECT id, name FROM countries")
    return {row[1]: row[0] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# Formations
# ---------------------------------------------------------------------------

def _classify_formation_type(name: str) -> tuple[str | None, str | None]:
    """Classify formation type and extract normalized name."""
    for suffix, ftype in FORMATION_TYPE_MAP:
        if f' {suffix}' in name or name.endswith(suffix):
            normalized = name.replace(f' {suffix}', '').strip()
            return ftype, normalized
    return None, name


def _load_formations(conn: sqlite3.Connection,
                     genera: list[GenusRecord]) -> dict[str, int]:
    """Extract unique formation names and insert into formations table.

    Returns formation_name → id map.
    """
    cur = conn.cursor()
    formations: set[str] = set()

    for rec in genera:
        if rec.formation:
            formations.add(rec.formation)

    for name in sorted(formations):
        fm_type, normalized = _classify_formation_type(name)
        cur.execute("""
            INSERT OR IGNORE INTO formations (name, normalized_name, formation_type)
            VALUES (?, ?, ?)
        """, (name, normalized, fm_type))

    conn.commit()

    cur.execute("SELECT id, name FROM formations")
    return {row[1]: row[0] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# COW States + Country-COW Mapping
# ---------------------------------------------------------------------------

def _load_cow_states(conn: sqlite3.Connection, cow_csv_path: Path):
    """Import COW state system from CSV."""
    cur = conn.cursor()
    records = []

    with open(cow_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ccode = int(row['ccode'])
            st_month = max(int(row['stmonth']), 1)
            st_day = max(int(row['stday']), 1)
            end_month = max(int(row['endmonth']), 1)
            end_day = max(int(row['endday']), 1)
            start_date = f"{int(row['styear']):04d}-{st_month:02d}-{st_day:02d}"
            end_date = f"{int(row['endyear']):04d}-{end_month:02d}-{end_day:02d}"
            records.append({
                'cow_ccode': ccode, 'abbrev': row['stateabb'],
                'name': row['statenme'],
                'start_date': start_date, 'end_date': end_date,
                'version': int(row['version']),
            })

    cur.executemany("""
        INSERT INTO cow_states (cow_ccode, abbrev, name, start_date, end_date, version)
        VALUES (:cow_ccode, :abbrev, :name, :start_date, :end_date, :version)
    """, records)
    conn.commit()

    # Build name index
    index = {}
    by_ccode: dict[int, dict] = {}
    for r in records:
        cc = r['cow_ccode']
        if cc not in by_ccode or r['end_date'] > by_ccode[cc]['end_date']:
            by_ccode[cc] = r
    for cc, r in by_ccode.items():
        index[r['name'].lower()] = cc

    return records, index


def _strip_direction_prefix(name: str) -> tuple[str | None, str | None]:
    for prefix in DIRECTION_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):], prefix.strip()
    return None, None


def _create_country_cow_mapping(conn: sqlite3.Connection,
                                cow_name_index: dict[str, int]):
    """Create country_cow_mapping entries."""
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM countries ORDER BY id")
    countries = cur.fetchall()

    for country_id, country_name in countries:
        ccode = None
        parent_name = None
        notes = None

        if country_name in MANUAL_MAPPING:
            ccode, parent_name = MANUAL_MAPPING[country_name]
            notes = 'unmappable' if ccode is None else 'manual'
        else:
            cow_match = cow_name_index.get(country_name.lower())
            if cow_match:
                ccode = cow_match
                notes = 'exact'
            else:
                base_name, prefix = _strip_direction_prefix(country_name)
                if base_name:
                    cow_match = cow_name_index.get(base_name.lower())
                    if cow_match:
                        ccode = cow_match
                        parent_name = f"{country_name} → {base_name}"
                        notes = 'prefix'
                    elif base_name in MANUAL_MAPPING:
                        ccode, pn = MANUAL_MAPPING[base_name]
                        parent_name = f"{country_name} → {pn}" if pn else None
                        notes = 'prefix+manual'
                    else:
                        notes = 'unmapped'
                else:
                    notes = 'unmapped'

        cur.execute("""
            INSERT INTO country_cow_mapping (country_id, cow_ccode, parent_name, notes)
            VALUES (?, ?, ?, ?)
        """, (country_id, ccode, parent_name, notes))

    conn.commit()


# ---------------------------------------------------------------------------
# Geographic Regions
# ---------------------------------------------------------------------------

def _build_geographic_regions(conn: sqlite3.Connection,
                              genera: list[GenusRecord],
                              country_map: dict[str, int]):
    """Build hierarchical geographic_regions table."""
    cur = conn.cursor()

    # Step 1: Create country-level entries from COW sovereign states
    cur.execute("""
        SELECT DISTINCT cm.cow_ccode, cs.name
        FROM country_cow_mapping cm
        JOIN cow_states cs ON cm.cow_ccode = cs.cow_ccode
        WHERE cm.cow_ccode IS NOT NULL
        GROUP BY cm.cow_ccode
        HAVING cs.end_date = MAX(cs.end_date)
    """)
    sovereign_states = cur.fetchall()

    ccode_to_geo_id: dict[int, int] = {}
    for cow_ccode, cow_name in sovereign_states:
        cur.execute("""
            INSERT OR IGNORE INTO geographic_regions (name, level, cow_ccode)
            VALUES (?, 'country', ?)
        """, (cow_name, cow_ccode))
        if cur.lastrowid:
            ccode_to_geo_id[cow_ccode] = cur.lastrowid
        else:
            cur.execute("SELECT id FROM geographic_regions WHERE name = ? AND level = 'country'",
                        (cow_name,))
            row = cur.fetchone()
            if row:
                ccode_to_geo_id[cow_ccode] = row[0]

    # Unmappable "countries" (no COW ccode) as independent entries
    cur.execute("""
        SELECT c.id, c.name FROM countries c
        JOIN country_cow_mapping cm ON cm.country_id = c.id
        WHERE cm.cow_ccode IS NULL
    """)
    unmappable_map: dict[int, int] = {}
    for c_id, c_name in cur.fetchall():
        cur.execute("""
            INSERT OR IGNORE INTO geographic_regions (name, level)
            VALUES (?, 'country')
        """, (c_name,))
        geo_id = cur.lastrowid
        if not geo_id:
            cur.execute("SELECT id FROM geographic_regions WHERE name = ? AND level = 'country'",
                        (c_name,))
            row = cur.fetchone()
            geo_id = row[0] if row else None
        if geo_id:
            unmappable_map[c_id] = geo_id

    conn.commit()

    # Step 2: Create region-level entries from countries table
    # (countries that map to sub-regions of sovereign states)
    alias_country_ids = set()
    country_to_region: dict[int, int] = {}

    cur.execute("""
        SELECT c.id, c.name, cm.cow_ccode, cm.notes
        FROM countries c
        JOIN country_cow_mapping cm ON cm.country_id = c.id
        WHERE cm.cow_ccode IS NOT NULL
    """)
    for c_id, c_name, cow_ccode, notes in cur.fetchall():
        # Skip if this is an exact match (it's the sovereign state itself)
        if notes == 'exact':
            continue
        # Check if it's an alias (USA, Burma, etc.)
        if c_name in COUNTRY_ALIASES:
            alias_country_ids.add(c_id)
            continue

        parent_geo_id = ccode_to_geo_id.get(cow_ccode)
        if parent_geo_id:
            cur.execute("""
                INSERT OR IGNORE INTO geographic_regions (name, level, parent_id, cow_ccode)
                VALUES (?, 'region', ?, ?)
            """, (c_name, parent_geo_id, cow_ccode))
            geo_id = cur.lastrowid
            if not geo_id:
                cur.execute("""
                    SELECT id FROM geographic_regions
                    WHERE name = ? AND parent_id = ?
                """, (c_name, parent_geo_id))
                row = cur.fetchone()
                geo_id = row[0] if row else None
            if geo_id:
                country_to_region[c_id] = geo_id

    conn.commit()

    # Step 3: Create region-level entries from genus_locations.region text
    # This will be done in the junctions step since we need genus_locations data
    # For now, collect unique (region, country) pairs from genera

    region_lookup: dict[tuple[str, int], int] = {}

    for rec in genera:
        if rec.region and rec.country:
            c_id = country_map.get(rec.country)
            if not c_id:
                continue

            # Determine parent geo_id for this country
            parent_geo_id = None
            if c_id in unmappable_map:
                parent_geo_id = unmappable_map[c_id]
            elif c_id in alias_country_ids:
                cow_ccode = COUNTRY_ALIASES.get(rec.country)
                parent_geo_id = ccode_to_geo_id.get(cow_ccode)
            elif c_id in country_to_region:
                # The country itself is a region — use its parent
                cur.execute("SELECT parent_id FROM geographic_regions WHERE id = ?",
                            (country_to_region[c_id],))
                row = cur.fetchone()
                parent_geo_id = row[0] if row else None
            else:
                # Exact match country — find geo_id
                cur.execute("""
                    SELECT cm.cow_ccode FROM country_cow_mapping cm
                    WHERE cm.country_id = ?
                """, (c_id,))
                row = cur.fetchone()
                if row and row[0]:
                    parent_geo_id = ccode_to_geo_id.get(row[0])

            if parent_geo_id:
                key = (rec.region, parent_geo_id)
                if key not in region_lookup:
                    cur.execute("""
                        INSERT OR IGNORE INTO geographic_regions
                            (name, level, parent_id)
                        VALUES (?, 'region', ?)
                    """, (rec.region, parent_geo_id))
                    geo_id = cur.lastrowid
                    if not geo_id:
                        cur.execute("""
                            SELECT id FROM geographic_regions
                            WHERE name = ? AND parent_id = ?
                        """, (rec.region, parent_geo_id))
                        row = cur.fetchone()
                        geo_id = row[0] if row else None
                    if geo_id:
                        region_lookup[key] = geo_id

    conn.commit()

    return ccode_to_geo_id, unmappable_map, country_to_region, alias_country_ids, region_lookup


# ---------------------------------------------------------------------------
# ICS Chronostratigraphy
# ---------------------------------------------------------------------------

def _load_ics(conn: sqlite3.Connection, ttl_path: Path):
    """Import ICS chronostratigraphic chart from RDF/Turtle file.

    Uses rdflib for parsing.
    """
    cur = conn.cursor()

    try:
        from rdflib import Graph, Namespace, URIRef, Literal
        from rdflib.namespace import SKOS, RDF
    except ImportError:
        print('  [paleocore] rdflib not available, skipping ICS import')
        return

    GTS = Namespace('http://resource.geosciml.org/ontology/timescale/gts#')
    RANK = Namespace('http://resource.geosciml.org/ontology/timescale/rank/')
    ISCHART = Namespace('http://resource.geosciml.org/classifier/ics/ischart/')
    TIME = Namespace('http://www.w3.org/2006/time#')
    SDO = Namespace('https://schema.org/')
    SH = Namespace('http://www.w3.org/ns/shacl#')

    RANK_MAP = {
        str(RANK['Super-Eon']): 'Super-Eon',
        str(RANK['Eon']): 'Eon',
        str(RANK['Era']): 'Era',
        str(RANK['Period']): 'Period',
        str(RANK['Sub-Period']): 'Sub-Period',
        str(RANK['Epoch']): 'Epoch',
        str(RANK['Age']): 'Age',
    }

    g = Graph()
    g.parse(str(ttl_path), format='turtle')

    concepts = []
    for s in g.subjects(RDF.type, SKOS.Concept):
        uri = str(s)
        if not uri.startswith(str(ISCHART)):
            continue

        name = None
        for label in g.objects(s, SKOS.prefLabel):
            if hasattr(label, 'language') and label.language == 'en':
                name = str(label)
                break
            if name is None:
                name = str(label)
        if not name:
            name = uri.split('/')[-1]

        rank = None
        for r in g.objects(s, GTS.rank):
            rank = RANK_MAP.get(str(r))

        parent_uri = None
        for broader in g.objects(s, SKOS.broader):
            parent_uri = str(broader)

        start_mya = end_mya = None
        start_unc = end_unc = None

        for begin in g.objects(s, TIME.hasBeginning):
            for mya in g.objects(begin, URIRef(str(ISCHART) + 'inMYA')):
                try:
                    start_mya = float(str(mya))
                except ValueError:
                    pass
            for unc in g.objects(begin, SDO.marginOfError):
                try:
                    start_unc = float(str(unc))
                except ValueError:
                    pass

        for end in g.objects(s, TIME.hasEnd):
            for mya in g.objects(end, URIRef(str(ISCHART) + 'inMYA')):
                try:
                    end_mya = float(str(mya))
                except ValueError:
                    pass
            for unc in g.objects(end, SDO.marginOfError):
                try:
                    end_unc = float(str(unc))
                except ValueError:
                    pass

        short_code = None
        for notation in g.objects(s, SKOS.notation):
            if hasattr(notation, 'datatype') and 'ccgmShortCode' in str(notation.datatype):
                short_code = str(notation)

        color = None
        for c in g.objects(s, SDO.color):
            color = str(c)

        display_order = None
        for o in g.objects(s, SH.order):
            try:
                display_order = int(str(o))
            except ValueError:
                pass

        ratified_gssp = 0
        for gssp in g.objects(s, GTS.ratifiedGSSP):
            ratified_gssp = 1

        concepts.append({
            'uri': uri, 'name': name, 'rank': rank,
            'parent_uri': parent_uri,
            'start_mya': start_mya, 'start_uncertainty': start_unc,
            'end_mya': end_mya, 'end_uncertainty': end_unc,
            'short_code': short_code, 'color': color,
            'display_order': display_order, 'ratified_gssp': ratified_gssp,
        })

    # Pass 1: Insert without parent_id
    uri_to_id: dict[str, int] = {}
    for c in concepts:
        cur.execute("""
            INSERT INTO ics_chronostrat
                (ics_uri, name, rank, start_mya, start_uncertainty,
                 end_mya, end_uncertainty, short_code, color,
                 display_order, ratified_gssp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c['uri'], c['name'], c['rank'],
            c['start_mya'], c['start_uncertainty'],
            c['end_mya'], c['end_uncertainty'],
            c['short_code'], c['color'],
            c['display_order'], c['ratified_gssp'],
        ))
        uri_to_id[c['uri']] = cur.lastrowid

    # Pass 2: Update parent_id
    for c in concepts:
        if c['parent_uri'] and c['parent_uri'] in uri_to_id:
            parent_id = uri_to_id[c['parent_uri']]
            cur.execute("UPDATE ics_chronostrat SET parent_id = ? WHERE ics_uri = ?",
                        (parent_id, c['uri']))

    conn.commit()

    # Temporal ICS mapping
    name_to_ics_id: dict[str, int] = {}
    cur.execute("SELECT id, ics_uri FROM ics_chronostrat")
    for ics_id, ics_uri in cur.fetchall():
        local_name = ics_uri.split('/')[-1]
        name_to_ics_id[local_name] = ics_id

    for code, mappings in TEMPORAL_MAPPING.items():
        for ics_name, mapping_type in mappings:
            ics_id = name_to_ics_id.get(ics_name)
            if ics_id:
                cur.execute("""
                    INSERT INTO temporal_ics_mapping
                        (temporal_code, ics_id, mapping_type)
                    VALUES (?, ?, ?)
                """, (code, ics_id, mapping_type))

    conn.commit()
    print(f'    ics_chronostrat: {len(concepts)} records')


# ---------------------------------------------------------------------------
# SCODA Metadata
# ---------------------------------------------------------------------------

def _load_metadata(conn: sqlite3.Connection):
    """Insert SCODA metadata tables for PaleoCore."""
    cur = conn.cursor()

    # artifact_metadata
    cur.execute("""
        CREATE TABLE IF NOT EXISTS artifact_metadata (
            key TEXT PRIMARY KEY, value TEXT
        )
    """)
    metadata = [
        ('artifact_id', 'paleocore'),
        ('name', 'PaleoCore'),
        ('version', '0.1.1'),
        ('schema_version', '1.0'),
        ('created_at', '2026-02-13'),
        ('description', 'Shared paleontological infrastructure: geography, lithostratigraphy, chronostratigraphy'),
        ('license', 'CC-BY-4.0'),
    ]
    cur.executemany("INSERT INTO artifact_metadata (key, value) VALUES (?, ?)",
                    metadata)

    # provenance
    cur.execute("""
        CREATE TABLE IF NOT EXISTS provenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT, citation TEXT, description TEXT,
            year INTEGER, url TEXT
        )
    """)
    provenance = [
        ('reference',
         'Correlates of War Project. State System Membership (v2024).',
         'COW sovereign state master data (cow_states, country_cow_mapping)',
         2024, 'https://correlatesofwar.org/data-sets/state-system-membership/'),
        ('reference',
         'International Commission on Stratigraphy. International Chronostratigraphic Chart (GTS 2020). SKOS/RDF.',
         'ICS chronostratigraphic chart (ics_chronostrat, temporal_ics_mapping)',
         2020, 'https://stratigraphy.org/chart'),
        ('build',
         'PaleoCore build pipeline (2026). Scripts: create_paleocore.py, import_cow.py, create_geographic_regions.py, import_ics.py',
         'Automated extraction, import, and mapping pipeline',
         2026, None),
    ]
    cur.executemany("""
        INSERT INTO provenance (source_type, citation, description, year, url)
        VALUES (?, ?, ?, ?, ?)
    """, provenance)

    # schema_descriptions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_descriptions (
            table_name TEXT, column_name TEXT, description TEXT
        )
    """)
    # Table-level descriptions
    table_descs = [
        ('countries', None, 'Country names used in Trilobase genus locations'),
        ('geographic_regions', None, 'Hierarchical geographic regions (countries + sub-regions)'),
        ('cow_states', None, 'COW State System Membership v2024'),
        ('country_cow_mapping', None, 'Mapping between countries and COW state codes'),
        ('formations', None, 'Geological formations referenced by genera'),
        ('temporal_ranges', None, 'Geological time period codes'),
        ('ics_chronostrat', None, 'ICS International Chronostratigraphic Chart'),
        ('temporal_ics_mapping', None, 'Mapping between temporal codes and ICS units'),
    ]
    cur.executemany("""
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES (?, ?, ?)
    """, table_descs)

    # ui_display_intent
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ui_display_intent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT, default_view TEXT, description TEXT,
            source_query TEXT, priority INTEGER DEFAULT 0
        )
    """)
    intents = [
        ('countries', 'table', 'Countries with trilobite occurrences', 'countries_list', 0),
        ('formations', 'table', 'Geological formations as a searchable list', 'formations_list', 0),
        ('chronostratigraphy', 'chart', 'ICS chronostratigraphic chart', 'ics_chronostrat_list', 0),
        ('temporal_ranges', 'table', 'Temporal range codes', 'temporal_ranges_list', 0),
    ]
    cur.executemany("""
        INSERT INTO ui_display_intent (entity, default_view, description, source_query, priority)
        VALUES (?, ?, ?, ?, ?)
    """, intents)

    # ui_queries (13 queries for PaleoCore)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ui_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL, description TEXT,
            sql TEXT NOT NULL, params_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    queries = [
        ('countries_list', 'All countries sorted by name',
         'SELECT id, name, code FROM countries ORDER BY name', None),
        ('regions_list', 'All regions with parent country',
         "SELECT gr.id, gr.name, parent.name as country_name "
         "FROM geographic_regions gr "
         "LEFT JOIN geographic_regions parent ON gr.parent_id = parent.id "
         "WHERE gr.level = 'region' ORDER BY parent.name, gr.name", None),
        ('formations_list', 'All formations sorted by name',
         'SELECT id, name, normalized_name, formation_type, country, region, period '
         'FROM formations ORDER BY name', None),
        ('temporal_ranges_list', 'All temporal range codes',
         'SELECT id, code, name, period, epoch, start_mya, end_mya '
         'FROM temporal_ranges ORDER BY start_mya DESC', None),
        ('ics_chronostrat_list', 'ICS chart data',
         'SELECT id, name, rank, parent_id, start_mya, end_mya, color, display_order '
         'FROM ics_chronostrat ORDER BY display_order', None),
        ('country_regions', 'Regions for a specific country',
         "SELECT id, name FROM geographic_regions "
         "WHERE parent_id = :country_id AND level = 'region' ORDER BY name",
         '{"country_id": "integer"}'),
        ('country_cow_info', 'COW mapping for a country',
         'SELECT cm.cow_ccode, cs.name, cm.parent_name, cm.notes '
         'FROM country_cow_mapping cm '
         'LEFT JOIN cow_states cs ON cm.cow_ccode = cs.cow_ccode '
         'WHERE cm.country_id = :country_id '
         'GROUP BY cm.country_id HAVING cs.end_date = MAX(cs.end_date)',
         '{"country_id": "integer"}'),
        ('temporal_ics_mapping_list', 'ICS units for a temporal code',
         'SELECT ic.id, ic.name, ic.rank, m.mapping_type '
         'FROM temporal_ics_mapping m '
         'JOIN ics_chronostrat ic ON m.ics_id = ic.id '
         'WHERE m.temporal_code = :temporal_code',
         '{"temporal_code": "string"}'),
        ('country_detail', 'Country detail',
         'SELECT id, name, code FROM countries WHERE id = :id',
         '{"id": "integer"}'),
        ('formation_detail', 'Formation detail',
         'SELECT id, name, normalized_name, formation_type, country, region, period '
         'FROM formations WHERE id = :id',
         '{"id": "integer"}'),
        ('chronostrat_detail', 'Chronostratigraphy unit detail',
         'SELECT ics.*, p.name as parent_name '
         'FROM ics_chronostrat ics '
         'LEFT JOIN ics_chronostrat p ON ics.parent_id = p.id '
         'WHERE ics.id = :id',
         '{"id": "integer"}'),
        ('temporal_range_detail', 'Temporal range detail',
         'SELECT id, code, name, period, epoch, start_mya, end_mya '
         'FROM temporal_ranges WHERE id = :id',
         '{"id": "integer"}'),
        ('temporal_range_ics_mappings', 'ICS mappings for a temporal range',
         'SELECT m.id, m.temporal_code, ic.name, ic.rank, m.mapping_type '
         'FROM temporal_ics_mapping m '
         'JOIN ics_chronostrat ic ON m.ics_id = ic.id '
         'WHERE m.temporal_code = (SELECT code FROM temporal_ranges WHERE id = :id)',
         '{"id": "integer"}'),
    ]
    for name, desc, sql, params in queries:
        cur.execute("""
            INSERT INTO ui_queries (name, description, sql, params_json)
            VALUES (?, ?, ?, ?)
        """, (name, desc, sql, params))

    # ui_manifest
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ui_manifest (
            name TEXT NOT NULL, description TEXT,
            manifest_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    import json
    manifest = {
        "default_view": "countries_table",
        "views": {
            "countries_table": {
                "type": "table", "title": "Countries",
                "source_query": "countries_list",
                "columns": [
                    {"key": "name", "label": "Country", "sortable": True, "searchable": True},
                    {"key": "code", "label": "Code", "sortable": True}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
            },
            "formations_table": {
                "type": "table", "title": "Formations",
                "source_query": "formations_list",
                "columns": [
                    {"key": "name", "label": "Formation", "sortable": True, "searchable": True},
                    {"key": "formation_type", "label": "Type", "sortable": True},
                    {"key": "country", "label": "Country", "sortable": True, "searchable": True},
                    {"key": "period", "label": "Period", "sortable": True}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
            },
            "chronostratigraphy_chart": {
                "type": "hierarchy", "display": "nested_table",
                "title": "Chronostratigraphy",
                "source_query": "ics_chronostrat_list",
                "hierarchy_options": {
                    "id_key": "id", "parent_key": "parent_id",
                    "label_key": "name", "rank_key": "rank",
                    "sort_by": "order_key", "order_key": "display_order",
                    "skip_ranks": ["Super-Eon"]
                }
            },
            "temporal_ranges_table": {
                "type": "table", "title": "Temporal Ranges",
                "source_query": "temporal_ranges_list",
                "columns": [
                    {"key": "code", "label": "Code", "sortable": True},
                    {"key": "name", "label": "Name", "sortable": True, "searchable": True},
                    {"key": "period", "label": "Period", "sortable": True},
                    {"key": "start_mya", "label": "Start (Ma)", "sortable": True, "type": "number"},
                    {"key": "end_mya", "label": "End (Ma)", "sortable": True, "type": "number"}
                ],
                "default_sort": {"key": "start_mya", "direction": "desc"}
            }
        }
    }
    cur.execute("""
        INSERT INTO ui_manifest (name, description, manifest_json)
        VALUES ('default', 'Default UI manifest for PaleoCore viewer', ?)
    """, (json.dumps(manifest),))

    conn.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_paleocore(db_path: Path,
                     genera: list[GenusRecord],
                     cow_csv_path: Path,
                     ics_ttl_path: Path,
                     ) -> tuple[dict[str, int], dict[str, int]]:
    """Create paleocore.db from scratch.

    Returns (country_map, formation_map) for use in junction step.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    # 1. Create schema
    conn.executescript(PALEOCORE_SCHEMA)

    # 2. Countries
    print('  [paleocore] Loading countries...')
    country_map = _load_countries(conn, genera)
    print(f'    {len(country_map)} countries')

    # 3. Formations
    print('  [paleocore] Loading formations...')
    formation_map = _load_formations(conn, genera)
    print(f'    {len(formation_map)} formations')

    # 4. Temporal ranges
    print('  [paleocore] Loading temporal ranges...')
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO temporal_ranges (code, name, period, epoch, start_mya, end_mya)
        VALUES (?, ?, ?, ?, ?, ?)
    """, TEMPORAL_RANGES)
    conn.commit()

    # 5. COW States
    print('  [paleocore] Loading COW states...')
    cow_records, cow_name_index = _load_cow_states(conn, cow_csv_path)
    print(f'    {len(cow_records)} COW records')

    # 6. Country-COW mapping
    print('  [paleocore] Creating country-COW mapping...')
    _create_country_cow_mapping(conn, cow_name_index)

    # 7. Geographic regions
    print('  [paleocore] Building geographic regions...')
    geo_data = _build_geographic_regions(conn, genera, country_map)

    cur.execute("SELECT COUNT(*) FROM geographic_regions")
    print(f'    {cur.fetchone()[0]} geographic regions')

    # 8. ICS Chronostratigraphy
    print('  [paleocore] Loading ICS chart...')
    _load_ics(conn, ics_ttl_path)

    # 9. SCODA Metadata
    print('  [paleocore] Loading metadata...')
    _load_metadata(conn)

    conn.close()
    return country_map, formation_map
