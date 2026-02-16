#!/usr/bin/env python3
"""
Create paleocore.db from trilobase.db

Extracts 8 data tables (geography, lithostratigraphy, chronostratigraphy)
from trilobase.db into a standalone PaleoCore database with SCODA metadata.

Usage:
  python scripts/create_paleocore.py              # create paleocore.db
  python scripts/create_paleocore.py --dry-run    # preview without creating
  python scripts/create_paleocore.py --output path/to/paleocore.db
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timezone


SOURCE_DB = os.path.join(os.path.dirname(__file__), '..', 'trilobase.db')
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'paleocore.db')

# Tables to extract (order matters for FK dependencies)
DATA_TABLES = [
    'countries',
    'geographic_regions',
    'cow_states',
    'country_cow_mapping',
    'formations',
    'temporal_ranges',
    'ics_chronostrat',
    'temporal_ics_mapping',
]

# Columns to drop per table (taxa_count removal)
COLUMNS_TO_DROP = {
    'countries': ['taxa_count'],
    'geographic_regions': ['taxa_count'],
    'formations': ['taxa_count'],
}


# ---------------------------------------------------------------------------
# Data table creation
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = {
    'countries': """
        CREATE TABLE countries (
            id              INTEGER PRIMARY KEY,
            name            TEXT UNIQUE NOT NULL,
            code            TEXT,
            uid             TEXT,
            uid_method      TEXT,
            uid_confidence  TEXT,
            same_as_uid     TEXT
        )
    """,
    'geographic_regions': """
        CREATE TABLE geographic_regions (
            id              INTEGER PRIMARY KEY,
            name            TEXT NOT NULL,
            level           TEXT NOT NULL,
            parent_id       INTEGER,
            cow_ccode       INTEGER,
            uid             TEXT,
            uid_method      TEXT,
            uid_confidence  TEXT,
            same_as_uid     TEXT,
            FOREIGN KEY (parent_id) REFERENCES geographic_regions(id)
        )
    """,
    'cow_states': """
        CREATE TABLE cow_states (
            cow_ccode  INTEGER NOT NULL,
            abbrev     TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            start_date TEXT    NOT NULL,
            end_date   TEXT    NOT NULL,
            version    INTEGER NOT NULL DEFAULT 2024,
            PRIMARY KEY (cow_ccode, start_date)
        )
    """,
    'country_cow_mapping': """
        CREATE TABLE country_cow_mapping (
            country_id  INTEGER NOT NULL,
            cow_ccode   INTEGER,
            parent_name TEXT,
            notes       TEXT,
            FOREIGN KEY (country_id) REFERENCES countries(id),
            PRIMARY KEY (country_id)
        )
    """,
    'formations': """
        CREATE TABLE formations (
            id              INTEGER PRIMARY KEY,
            name            TEXT UNIQUE NOT NULL,
            normalized_name TEXT,
            formation_type  TEXT,
            country         TEXT,
            region          TEXT,
            period          TEXT,
            uid             TEXT,
            uid_method      TEXT,
            uid_confidence  TEXT,
            same_as_uid     TEXT
        )
    """,
    'temporal_ranges': """
        CREATE TABLE temporal_ranges (
            id              INTEGER PRIMARY KEY,
            code            TEXT UNIQUE NOT NULL,
            name            TEXT,
            period          TEXT,
            epoch           TEXT,
            start_mya       REAL,
            end_mya         REAL,
            uid             TEXT,
            uid_method      TEXT,
            uid_confidence  TEXT,
            same_as_uid     TEXT
        )
    """,
    'ics_chronostrat': """
        CREATE TABLE ics_chronostrat (
            id                INTEGER PRIMARY KEY,
            ics_uri           TEXT UNIQUE NOT NULL,
            name              TEXT NOT NULL,
            rank              TEXT NOT NULL,
            parent_id         INTEGER,
            start_mya         REAL,
            start_uncertainty REAL,
            end_mya           REAL,
            end_uncertainty   REAL,
            short_code        TEXT,
            color             TEXT,
            display_order     INTEGER,
            ratified_gssp     INTEGER DEFAULT 0,
            uid               TEXT,
            uid_method        TEXT,
            uid_confidence    TEXT,
            same_as_uid       TEXT,
            FOREIGN KEY (parent_id) REFERENCES ics_chronostrat(id)
        )
    """,
    'temporal_ics_mapping': """
        CREATE TABLE temporal_ics_mapping (
            id            INTEGER PRIMARY KEY,
            temporal_code TEXT NOT NULL,
            ics_id        INTEGER NOT NULL,
            mapping_type  TEXT NOT NULL,
            notes         TEXT,
            FOREIGN KEY (ics_id) REFERENCES ics_chronostrat(id)
        )
    """,
}


def get_source_columns(src_conn, table):
    """Get column names from source table."""
    cursor = src_conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def get_target_columns(table):
    """Get column names for target table (excluding dropped columns)."""
    # Parse from CREATE TABLE SQL
    src_conn = sqlite3.connect(SOURCE_DB)
    all_cols = get_source_columns(src_conn, table)
    src_conn.close()
    drop = COLUMNS_TO_DROP.get(table, [])
    return [c for c in all_cols if c not in drop]


def copy_table_data(src_conn, dst_conn, table):
    """Copy data from source to destination, excluding dropped columns."""
    src_cols = get_source_columns(src_conn, table)
    drop = COLUMNS_TO_DROP.get(table, [])
    keep_cols = [c for c in src_cols if c not in drop]

    cols_str = ', '.join(keep_cols)
    placeholders = ', '.join(['?'] * len(keep_cols))

    rows = src_conn.execute(f"SELECT {cols_str} FROM {table}").fetchall()
    dst_conn.executemany(
        f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})",
        rows
    )
    return len(rows)


# ---------------------------------------------------------------------------
# SCODA metadata
# ---------------------------------------------------------------------------

def create_scoda_tables(conn):
    """Create the 6 SCODA metadata tables."""
    conn.execute("""
        CREATE TABLE artifact_metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE provenance (
            id          INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            citation    TEXT NOT NULL,
            description TEXT,
            year        INTEGER,
            url         TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE schema_descriptions (
            table_name  TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        )
    """)
    conn.execute("""
        CREATE TABLE ui_display_intent (
            id           INTEGER PRIMARY KEY,
            entity       TEXT NOT NULL,
            default_view TEXT NOT NULL,
            description  TEXT,
            source_query TEXT,
            priority     INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE ui_queries (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL UNIQUE,
            description TEXT,
            sql         TEXT NOT NULL,
            params_json TEXT,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE ui_manifest (
            name          TEXT PRIMARY KEY,
            description   TEXT,
            manifest_json TEXT NOT NULL,
            created_at    TEXT NOT NULL
        )
    """)


def insert_artifact_metadata(conn):
    """Insert PaleoCore artifact_metadata (7 entries)."""
    metadata = [
        ('artifact_id', 'paleocore'),
        ('name', 'PaleoCore'),
        ('version', '0.3.0'),
        ('schema_version', '1.0'),
        ('created_at', str(date.today())),
        ('description',
         'Shared paleontological infrastructure: geography, lithostratigraphy, chronostratigraphy'),
        ('license', 'CC-BY-4.0'),
    ]
    for key, value in metadata:
        conn.execute(
            "INSERT INTO artifact_metadata (key, value) VALUES (?, ?)",
            (key, value)
        )
    return len(metadata)


def insert_provenance(conn):
    """Insert PaleoCore provenance (3 entries)."""
    sources = [
        (1, 'reference',
         'Correlates of War Project. State System Membership (v2024).',
         'COW sovereign state master data (cow_states, country_cow_mapping)',
         2024, 'https://correlatesofwar.org/data-sets/state-system-membership/'),
        (2, 'reference',
         'International Commission on Stratigraphy. International Chronostratigraphic Chart (GTS 2020). SKOS/RDF.',
         'ICS chronostratigraphic chart (ics_chronostrat, temporal_ics_mapping)',
         2020, 'https://stratigraphy.org/chart'),
        (3, 'build',
         'PaleoCore build pipeline (2026). Scripts: create_paleocore.py, import_cow.py, create_geographic_regions.py, import_ics.py',
         'Automated extraction, import, and mapping pipeline',
         2026, None),
    ]
    for s in sources:
        conn.execute(
            "INSERT INTO provenance (id, source_type, citation, description, year, url) "
            "VALUES (?, ?, ?, ?, ?, ?)", s
        )
    return len(sources)


def insert_schema_descriptions(conn):
    """Insert PaleoCore schema_descriptions."""
    descriptions = [
        # --- countries ---
        ('countries', None, 'Countries for geographic reference (142 records)'),
        ('countries', 'id', 'Primary key'),
        ('countries', 'name', 'Country name'),
        ('countries', 'code', 'ISO country code'),

        # --- geographic_regions ---
        ('geographic_regions', None,
         'Hierarchical geographic data: countries and sub-regions (562 records)'),
        ('geographic_regions', 'id', 'Primary key'),
        ('geographic_regions', 'name', 'Region or country name'),
        ('geographic_regions', 'level', "Hierarchy level: 'country' or 'region'"),
        ('geographic_regions', 'parent_id',
         'FK to parent geographic_regions.id (self-referencing)'),
        ('geographic_regions', 'cow_ccode', 'COW country code (countries only)'),

        # --- cow_states ---
        ('cow_states', None,
         'Correlates of War State System Membership v2024 (244 records)'),
        ('cow_states', 'cow_ccode', 'COW numeric country code'),
        ('cow_states', 'abbrev', 'COW country abbreviation'),
        ('cow_states', 'name', 'Country name in COW dataset'),
        ('cow_states', 'start_date', 'State system membership start date'),
        ('cow_states', 'end_date', 'State system membership end date'),
        ('cow_states', 'version', 'COW dataset version'),

        # --- country_cow_mapping ---
        ('country_cow_mapping', None,
         'Mapping between countries table and COW state codes (142 records)'),
        ('country_cow_mapping', 'country_id', 'FK to countries.id'),
        ('country_cow_mapping', 'cow_ccode',
         'COW country code (NULL if unmappable)'),
        ('country_cow_mapping', 'parent_name',
         'Parent country name for dependent territories'),
        ('country_cow_mapping', 'notes',
         'Mapping notes (method: exact, manual, prefix, unmappable)'),

        # --- formations ---
        ('formations', None, 'Geological formations (2,004 records)'),
        ('formations', 'id', 'Primary key'),
        ('formations', 'name', 'Formation name as given in source'),
        ('formations', 'normalized_name',
         'Lowercased, normalized form of name'),
        ('formations', 'formation_type',
         'Abbreviation: Fm (Formation), Sh (Shale), Lst (Limestone), Gp (Group), etc.'),
        ('formations', 'country',
         'Country where formation is located (text reference)'),
        ('formations', 'region',
         'Region within country (text reference)'),
        ('formations', 'period', 'Geological period (text reference)'),

        # --- temporal_ranges ---
        ('temporal_ranges', None,
         'Geological time period codes and age ranges (28 records)'),
        ('temporal_ranges', 'id', 'Primary key'),
        ('temporal_ranges', 'code',
         'Short code: LCAM, MCAM, UCAM, LORD, MORD, UORD, etc.'),
        ('temporal_ranges', 'name', 'Full name of the time period'),
        ('temporal_ranges', 'period',
         'Parent period: Cambrian, Ordovician, Silurian, Devonian, Carboniferous, Permian'),
        ('temporal_ranges', 'epoch',
         'Epoch within period: Lower, Middle, Upper'),
        ('temporal_ranges', 'start_mya',
         'Start of range in millions of years ago'),
        ('temporal_ranges', 'end_mya',
         'End of range in millions of years ago'),

        # --- ics_chronostrat ---
        ('ics_chronostrat', None,
         'ICS International Chronostratigraphic Chart, GTS 2020 (178 records)'),
        ('ics_chronostrat', 'id', 'Primary key'),
        ('ics_chronostrat', 'ics_uri', 'ICS SKOS URI (unique identifier)'),
        ('ics_chronostrat', 'name', 'Chronostratigraphic unit name'),
        ('ics_chronostrat', 'rank',
         'Rank: Super-Eon, Eon, Era, Period, Sub-Period, Epoch, Age'),
        ('ics_chronostrat', 'parent_id',
         'FK to parent ics_chronostrat.id (self-referencing hierarchy)'),
        ('ics_chronostrat', 'start_mya',
         'Start age in millions of years ago'),
        ('ics_chronostrat', 'start_uncertainty',
         'Uncertainty of start age (Ma)'),
        ('ics_chronostrat', 'end_mya',
         'End age in millions of years ago'),
        ('ics_chronostrat', 'end_uncertainty',
         'Uncertainty of end age (Ma)'),
        ('ics_chronostrat', 'short_code',
         'Short code for display (e.g., C, O, S)'),
        ('ics_chronostrat', 'color',
         'Hex color for chart display (#RRGGBB)'),
        ('ics_chronostrat', 'display_order',
         'Display ordering for chart rendering'),
        ('ics_chronostrat', 'ratified_gssp',
         'Whether the GSSP has been ratified (1/0)'),

        # --- temporal_ics_mapping ---
        ('temporal_ics_mapping', None,
         'Mapping between temporal_ranges codes and ICS units (40 records)'),
        ('temporal_ics_mapping', 'id', 'Primary key'),
        ('temporal_ics_mapping', 'temporal_code',
         'temporal_ranges.code reference'),
        ('temporal_ics_mapping', 'ics_id', 'FK to ics_chronostrat.id'),
        ('temporal_ics_mapping', 'mapping_type',
         'Mapping type: exact, aggregate, partial, unmappable'),
        ('temporal_ics_mapping', 'notes', 'Mapping notes and rationale'),

        # --- SCODA metadata tables ---
        ('artifact_metadata', None,
         'SCODA artifact identity and metadata (key-value store)'),
        ('artifact_metadata', 'key', 'Metadata key (e.g., version, name)'),
        ('artifact_metadata', 'value', 'Metadata value'),

        ('provenance', None,
         'Data sources and lineage for this artifact'),
        ('provenance', 'source_type', 'Type: reference or build'),
        ('provenance', 'citation', 'Full citation text'),
        ('provenance', 'description',
         'What this source contributed to the dataset'),
        ('provenance', 'year', 'Year of the source'),
        ('provenance', 'url', 'URL if available'),

        ('schema_descriptions', None,
         'Self-describing schema: human-readable descriptions of all tables and columns'),
        ('schema_descriptions', 'table_name',
         'Name of the described table'),
        ('schema_descriptions', 'column_name',
         'Column name (NULL for table-level description)'),
        ('schema_descriptions', 'description', 'Human-readable description'),

        ('ui_display_intent', None,
         'SCODA view type hints for UI rendering'),
        ('ui_display_intent', 'entity', 'Entity name'),
        ('ui_display_intent', 'default_view',
         'Default view type: table, chart'),
        ('ui_display_intent', 'description', 'Entity description'),
        ('ui_display_intent', 'source_query',
         'Name of the default query'),
        ('ui_display_intent', 'priority', 'Display priority (higher = first)'),

        ('ui_queries', None,
         'Named SQL queries for UI and API consumers'),
        ('ui_queries', 'name', 'Unique query name'),
        ('ui_queries', 'description', 'What this query returns'),
        ('ui_queries', 'sql', 'SQL statement'),
        ('ui_queries', 'params_json',
         'JSON array of parameter names (for parameterized queries)'),
        ('ui_queries', 'created_at', 'Creation timestamp'),

        ('ui_manifest', None,
         'Declarative view definitions for UI rendering'),
        ('ui_manifest', 'name', 'Manifest name'),
        ('ui_manifest', 'description', 'Manifest description'),
        ('ui_manifest', 'manifest_json',
         'JSON object defining views, columns, and layout'),
        ('ui_manifest', 'created_at', 'Creation timestamp'),
    ]

    for table_name, column_name, desc in descriptions:
        conn.execute(
            "INSERT INTO schema_descriptions (table_name, column_name, description) "
            "VALUES (?, ?, ?)",
            (table_name, column_name, desc)
        )
    return len(descriptions)


def insert_ui_display_intent(conn):
    """Insert PaleoCore ui_display_intent (4 entries)."""
    intents = [
        (1, 'countries', 'table',
         'Countries for geographic reference', 'countries_list', 0),
        (2, 'formations', 'table',
         'Geological formations', 'formations_list', 0),
        (3, 'chronostratigraphy', 'chart',
         'ICS International Chronostratigraphic Chart', 'ics_chronostrat_list', 0),
        (4, 'temporal_ranges', 'table',
         'Geological time period codes', 'temporal_ranges_list', 0),
    ]
    for i in intents:
        conn.execute(
            "INSERT INTO ui_display_intent "
            "(id, entity, default_view, description, source_query, priority) "
            "VALUES (?, ?, ?, ?, ?, ?)", i
        )
    return len(intents)


def insert_ui_queries(conn):
    """Insert PaleoCore ui_queries (8 entries)."""
    now = datetime.now(timezone.utc).isoformat()
    queries = [
        (1, 'countries_list', 'All countries sorted by name',
         'SELECT id, name, code FROM countries ORDER BY name',
         None, now),
        (2, 'regions_list', 'All regions with parent country',
         'SELECT gr.id, gr.name, p.name AS country_name, p.id AS country_id '
         'FROM geographic_regions gr '
         'LEFT JOIN geographic_regions p ON gr.parent_id = p.id '
         "WHERE gr.level = 'region' ORDER BY p.name, gr.name",
         None, now),
        (3, 'formations_list', 'All formations sorted by name',
         'SELECT id, name, formation_type, country, period '
         'FROM formations ORDER BY name',
         None, now),
        (4, 'temporal_ranges_list', 'All temporal range codes',
         'SELECT id, code, name, period, epoch, start_mya, end_mya '
         'FROM temporal_ranges ORDER BY start_mya DESC',
         None, now),
        (5, 'ics_chronostrat_list', 'ICS chart data',
         'SELECT id, name, rank, parent_id, start_mya, end_mya, color, display_order '
         'FROM ics_chronostrat ORDER BY display_order',
         None, now),
        (6, 'country_regions', 'Regions for a specific country',
         'SELECT id, name FROM geographic_regions '
         "WHERE parent_id = :country_id AND level = 'region' ORDER BY name",
         json.dumps(['country_id']), now),
        (7, 'country_cow_info', 'COW mapping for a country',
         'SELECT ccm.cow_ccode, cs.abbrev, cs.name AS cow_name, '
         'cs.start_date, cs.end_date '
         'FROM country_cow_mapping ccm '
         'LEFT JOIN cow_states cs ON ccm.cow_ccode = cs.cow_ccode '
         'WHERE ccm.country_id = :country_id',
         json.dumps(['country_id']), now),
        (8, 'temporal_ics_mapping_list', 'ICS units for a temporal code',
         'SELECT tim.mapping_type, ic.name, ic.rank, ic.start_mya, '
         'ic.end_mya, ic.color '
         'FROM temporal_ics_mapping tim '
         'JOIN ics_chronostrat ic ON tim.ics_id = ic.id '
         'WHERE tim.temporal_code = :temporal_code',
         json.dumps(['temporal_code']), now),
        (9, 'country_detail', 'Country detail with regions',
         'SELECT c.id, c.name, c.code, '
         '  (SELECT COUNT(*) FROM geographic_regions WHERE parent_id = c.id AND level = \'region\') as region_count '
         'FROM countries c WHERE c.id = :id',
         json.dumps(['id']), now),
        (10, 'formation_detail', 'Formation detail',
         'SELECT id, name, normalized_name, formation_type, country, region, period '
         'FROM formations WHERE id = :id',
         json.dumps(['id']), now),
        (11, 'chronostrat_detail', 'Chronostratigraphy unit detail',
         'SELECT ic.id, ic.name, ic.rank, ic.parent_id, ic.start_mya, ic.end_mya, '
         '  ic.color, p.name as parent_name, p.rank as parent_rank '
         'FROM ics_chronostrat ic LEFT JOIN ics_chronostrat p ON ic.parent_id = p.id '
         'WHERE ic.id = :id',
         json.dumps(['id']), now),
        (12, 'temporal_range_detail', 'Temporal range detail with ICS mappings',
         'SELECT id, code, name, period, epoch, start_mya, end_mya '
         'FROM temporal_ranges WHERE id = :id',
         json.dumps(['id']), now),
        (13, 'temporal_range_ics_mappings', 'ICS mappings for a temporal range',
         'SELECT tim.mapping_type, ic.name, ic.rank, ic.start_mya, ic.end_mya, '
         'ic.color, ic.id as ics_id '
         'FROM temporal_ics_mapping tim '
         'JOIN ics_chronostrat ic ON tim.ics_id = ic.id '
         'JOIN temporal_ranges tr ON tim.temporal_code = tr.code '
         'WHERE tr.id = :id',
         json.dumps(['id']), now),
    ]
    for q in queries:
        conn.execute(
            "INSERT INTO ui_queries "
            "(id, name, description, sql, params_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)", q
        )
    return len(queries)


def insert_ui_manifest(conn):
    """Insert PaleoCore ui_manifest (1 entry)."""
    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "default_view": "countries_table",
        "views": {
            "countries_table": {
                "type": "table",
                "title": "Countries",
                "description": "Countries for geographic reference",
                "source_query": "countries_list",
                "icon": "bi-globe",
                "columns": [
                    {"key": "name", "label": "Country",
                     "sortable": True, "searchable": True},
                    {"key": "code", "label": "Code",
                     "sortable": True, "searchable": False}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "country_detail", "id_key": "id"}
            },
            "formations_table": {
                "type": "table",
                "title": "Formations",
                "description": "Geological formations",
                "source_query": "formations_list",
                "icon": "bi-layers",
                "columns": [
                    {"key": "name", "label": "Formation",
                     "sortable": True, "searchable": True},
                    {"key": "formation_type", "label": "Type",
                     "sortable": True, "searchable": False},
                    {"key": "country", "label": "Country",
                     "sortable": True, "searchable": True},
                    {"key": "period", "label": "Period",
                     "sortable": True, "searchable": True}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "formation_detail", "id_key": "id"}
            },
            "chronostratigraphy_chart": {
                "type": "chart",
                "title": "Chronostratigraphy",
                "description": "ICS International Chronostratigraphic Chart (GTS 2020)",
                "source_query": "ics_chronostrat_list",
                "icon": "bi-clock-history",
                "columns": [
                    {"key": "name", "label": "Name",
                     "sortable": True, "searchable": True},
                    {"key": "rank", "label": "Rank",
                     "sortable": True, "searchable": True},
                    {"key": "start_mya", "label": "Start (Ma)",
                     "sortable": True, "type": "number"},
                    {"key": "end_mya", "label": "End (Ma)",
                     "sortable": True, "type": "number"},
                    {"key": "color", "label": "Color",
                     "sortable": False, "type": "color"}
                ],
                "default_sort": {"key": "display_order", "direction": "asc"},
                "searchable": True,
                "chart_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "color_key": "color",
                    "order_key": "display_order",
                    "rank_key": "rank",
                    "skip_ranks": ["Super-Eon"],
                    "rank_columns": [
                        {"rank": "Eon", "label": "Eon"},
                        {"rank": "Era", "label": "Era"},
                        {"rank": "Period", "label": "System / Period"},
                        {"rank": "Sub-Period", "label": "Sub-Period"},
                        {"rank": "Epoch", "label": "Series / Epoch"},
                        {"rank": "Age", "label": "Stage / Age"}
                    ],
                    "value_column": {"key": "start_mya", "label": "Age (Ma)"},
                    "cell_click": {"detail_view": "chronostrat_detail", "id_key": "id"}
                }
            },
            "temporal_ranges_table": {
                "type": "table",
                "title": "Temporal Ranges",
                "description": "Geological time period codes used in genus records",
                "source_query": "temporal_ranges_list",
                "icon": "bi-hourglass",
                "columns": [
                    {"key": "code", "label": "Code",
                     "sortable": True, "searchable": True},
                    {"key": "name", "label": "Name",
                     "sortable": True, "searchable": True},
                    {"key": "period", "label": "Period",
                     "sortable": True, "searchable": True},
                    {"key": "epoch", "label": "Epoch",
                     "sortable": True, "searchable": False},
                    {"key": "start_mya", "label": "Start (Ma)",
                     "sortable": True, "type": "number"},
                    {"key": "end_mya", "label": "End (Ma)",
                     "sortable": True, "type": "number"}
                ],
                "default_sort": {"key": "start_mya", "direction": "desc"},
                "searchable": True,
                "on_row_click": {"detail_view": "temporal_range_detail", "id_key": "id"}
            },
            "country_detail": {
                "type": "detail",
                "title": "Country Detail",
                "source": "/api/detail/country_detail?id={id}",
                "sections": [
                    {
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Country"},
                            {"key": "code", "label": "Code"},
                            {"key": "region_count", "label": "Regions"}
                        ]
                    }
                ]
            },
            "formation_detail": {
                "type": "detail",
                "title": "Formation Detail",
                "source": "/api/detail/formation_detail?id={id}",
                "sections": [
                    {
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Formation"},
                            {"key": "formation_type", "label": "Type"},
                            {"key": "country", "label": "Country"},
                            {"key": "region", "label": "Region"},
                            {"key": "period", "label": "Period"}
                        ]
                    }
                ]
            },
            "chronostrat_detail": {
                "type": "detail",
                "title": "Chronostratigraphy Detail",
                "source": "/api/detail/chronostrat_detail?id={id}",
                "sections": [
                    {
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "rank", "label": "Rank"},
                            {"key": "start_mya", "label": "Start (Ma)"},
                            {"key": "end_mya", "label": "End (Ma)"},
                            {"key": "color", "label": "Color", "format": "color_chip"},
                            {"key": "parent_name", "label": "Parent"}
                        ]
                    }
                ]
            },
            "temporal_range_detail": {
                "type": "detail",
                "title": "Temporal Range Detail",
                "source_query": "temporal_range_detail",
                "sub_queries": {
                    "ics_mappings": {
                        "query": "temporal_range_ics_mappings",
                        "params": {"id": "id"}
                    }
                },
                "sections": [
                    {
                        "type": "field_grid",
                        "fields": [
                            {"key": "code", "label": "Code"},
                            {"key": "name", "label": "Name"},
                            {"key": "period", "label": "Period"},
                            {"key": "epoch", "label": "Epoch"},
                            {"key": "start_mya", "label": "Start (Ma)"},
                            {"key": "end_mya", "label": "End (Ma)"}
                        ]
                    },
                    {
                        "type": "linked_table",
                        "title": "ICS Mappings ({count})",
                        "data_key": "ics_mappings",
                        "show_empty": True,
                        "empty_message": "No ICS mappings found.",
                        "columns": [
                            {"key": "name", "label": "ICS Unit"},
                            {"key": "rank", "label": "Rank"},
                            {"key": "mapping_type", "label": "Mapping"},
                            {"key": "start_mya", "label": "Start (Ma)"},
                            {"key": "end_mya", "label": "End (Ma)"},
                            {"key": "color", "label": "Color", "format": "color_chip"}
                        ],
                        "on_row_click": {"detail_view": "chronostrat_detail", "id_key": "ics_id"}
                    }
                ]
            }
        }
    }
    conn.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json, created_at) "
        "VALUES (?, ?, ?, ?)",
        ('default', 'Default UI manifest for PaleoCore viewer',
         json.dumps(manifest, indent=2, ensure_ascii=False), now)
    )
    return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def dry_run(source_db):
    """Preview what would be created."""
    missing = check_source_tables(source_db)
    if missing:
        print(f"Error: Source database is missing {len(missing)} required tables:",
              file=sys.stderr)
        for t in missing:
            print(f"  - {t}", file=sys.stderr)
        print(f"\nPhase 34 dropped PaleoCore tables from trilobase.db.", file=sys.stderr)
        print(f"If paleocore.db already exists, use it directly.", file=sys.stderr)
        sys.exit(1)

    src_conn = sqlite3.connect(source_db)

    print("=== DRY RUN (no file will be created) ===\n")
    print(f"Source DB: {os.path.abspath(source_db)}")
    print(f"DB size:   {os.path.getsize(source_db):,} bytes\n")

    print("Data tables to extract:")
    total = 0
    for table in DATA_TABLES:
        count = src_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        drop = COLUMNS_TO_DROP.get(table, [])
        note = f" (dropping: {', '.join(drop)})" if drop else ""
        print(f"  {table}: {count:,} records{note}")
        total += count

    print(f"\n  Total data records: {total:,}")

    print("\nSCODA metadata tables:")
    print("  artifact_metadata: 7 entries")
    print("  provenance: 3 entries")
    print("  schema_descriptions: ~80 entries")
    print("  ui_display_intent: 4 entries")
    print("  ui_queries: 8 entries")
    print("  ui_manifest: 1 entry")

    src_conn.close()


def check_source_tables(source_db):
    """Check if source DB has the required PaleoCore tables."""
    conn = sqlite3.connect(source_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in cursor.fetchall()}
    conn.close()

    missing = [t for t in DATA_TABLES if t not in existing]
    return missing


def create_paleocore(source_db, output_path):
    """Create paleocore.db from source trilobase.db."""
    # Check source tables exist
    missing = check_source_tables(source_db)
    if missing:
        print(f"Error: Source database is missing {len(missing)} required tables:",
              file=sys.stderr)
        for t in missing:
            print(f"  - {t}", file=sys.stderr)
        print(f"\nPhase 34 dropped PaleoCore tables from trilobase.db.", file=sys.stderr)
        print(f"If paleocore.db already exists, use it directly.", file=sys.stderr)
        print(f"To recreate, restore trilobase.db from git or use a backup.", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(output_path):
        os.remove(output_path)

    src_conn = sqlite3.connect(source_db)
    dst_conn = sqlite3.connect(output_path)

    # 1. Create data tables and copy data (FK off during bulk insert)
    dst_conn.execute("PRAGMA foreign_keys = OFF")
    print("Creating data tables...")
    total_records = 0
    for table in DATA_TABLES:
        dst_conn.execute(CREATE_TABLE_SQL[table])
        count = copy_table_data(src_conn, dst_conn, table)
        drop = COLUMNS_TO_DROP.get(table, [])
        note = f" (dropped: {', '.join(drop)})" if drop else ""
        print(f"  {table}: {count:,} records{note}")
        total_records += count
    dst_conn.commit()
    dst_conn.execute("PRAGMA foreign_keys = ON")

    # 2. Create SCODA metadata tables
    print("\nCreating SCODA metadata tables...")
    create_scoda_tables(dst_conn)

    n = insert_artifact_metadata(dst_conn)
    print(f"  artifact_metadata: {n} entries")

    n = insert_provenance(dst_conn)
    print(f"  provenance: {n} entries")

    n = insert_schema_descriptions(dst_conn)
    print(f"  schema_descriptions: {n} entries")

    n = insert_ui_display_intent(dst_conn)
    print(f"  ui_display_intent: {n} entries")

    n = insert_ui_queries(dst_conn)
    print(f"  ui_queries: {n} entries")

    n = insert_ui_manifest(dst_conn)
    print(f"  ui_manifest: {n} entries")

    dst_conn.commit()

    # 3. Verify
    print("\nVerification:")
    for table in DATA_TABLES:
        src_count = src_conn.execute(
            f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        dst_count = dst_conn.execute(
            f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        status = "OK" if src_count == dst_count else "MISMATCH"
        print(f"  {table}: {dst_count:,} ({status})")

    # Verify no taxa_count columns exist
    print("\n  taxa_count column check:")
    for table in COLUMNS_TO_DROP:
        cols = [row[1] for row in dst_conn.execute(
            f"PRAGMA table_info({table})").fetchall()]
        has_taxa = 'taxa_count' in cols
        print(f"    {table}: {'FAIL (taxa_count present)' if has_taxa else 'OK (removed)'}")

    src_conn.close()
    dst_conn.close()

    size = os.path.getsize(output_path)
    print(f"\nCreated: {output_path}")
    print(f"  Size: {size:,} bytes ({size / 1024:.0f} KB)")
    print(f"  Total data records: {total_records:,}")


def main():
    parser = argparse.ArgumentParser(
        description='Create paleocore.db from trilobase.db')
    parser.add_argument(
        '--source', default=SOURCE_DB,
        help='Path to source trilobase.db (default: trilobase.db)')
    parser.add_argument(
        '--output', default=DEFAULT_OUTPUT,
        help='Output paleocore.db path (default: paleocore.db)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview without creating file')
    args = parser.parse_args()

    source_db = os.path.abspath(args.source)
    output_path = os.path.abspath(args.output)

    if not os.path.exists(source_db):
        print(f"Error: Source database not found: {source_db}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        dry_run(source_db)
    else:
        create_paleocore(source_db, output_path)


if __name__ == '__main__':
    main()
