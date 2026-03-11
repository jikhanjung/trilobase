"""Step 7: SCODA metadata + UI queries.

Inserts trilobase-specific metadata tables:
  - artifact_metadata (7 entries)
  - provenance (5 entries)
  - schema_descriptions (~112 entries)
  - ui_display_intent (6 entries)
  - ui_queries (37+ entries)
  - ui_manifest (1 entry)

Data is extracted from the reference DB (db/trilobase.db) to ensure
exact reproduction.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


# ---------------------------------------------------------------------------
# Metadata tables DDL (created in load_data.py schema, but if not present)
# ---------------------------------------------------------------------------

METADATA_DDL = """
CREATE TABLE IF NOT EXISTS artifact_metadata (
    key TEXT PRIMARY KEY, value TEXT
);

CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT, citation TEXT, description TEXT,
    year INTEGER, url TEXT
);

CREATE TABLE IF NOT EXISTS schema_descriptions (
    table_name TEXT, column_name TEXT, description TEXT
);

CREATE TABLE IF NOT EXISTS ui_display_intent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT, default_view TEXT, description TEXT,
    source_query TEXT, priority INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ui_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL, description TEXT,
    sql TEXT NOT NULL, params_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ui_manifest (
    name TEXT NOT NULL, description TEXT,
    manifest_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# Hardcoded metadata (from current trilobase.db)
# ---------------------------------------------------------------------------

ARTIFACT_METADATA = [
    ('artifact_id', 'trilobase'),
    ('name', 'Trilobase'),
    ('version', '0.2.5'),
    ('schema_version', '1.0'),
    ('created_at', '2026-02-07'),
    ('description', 'Trilobite genus-level taxonomy database based on Jell & Adrain (2002)'),
    ('license', 'CC-BY-4.0'),
]

PROVENANCE = [
    ('primary',
     'Jell, P.A. & Adrain, J.M. (2002) Available generic names for trilobites. '
     'Memoirs of the Queensland Museum 48(2): 331-553.',
     'Primary source for genus-level taxonomy, synonymy, and type species',
     2002, None),
    ('supplementary',
     'Adrain, J.M. (2011) Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) '
     'Animal biodiversity: An outline of higher-level classification. Zootaxa 3148: 104-109.',
     'Suprafamilial classification (Order, Suborder, Superfamily)',
     2011, None),
    ('build',
     'Trilobase data pipeline (2026). Scripts: normalize_lines.py, create_database.py, '
     'normalize_database.py, fix_synonyms.py, normalize_families.py, '
     'populate_taxonomic_ranks.py, parse_references.py',
     'Automated extraction, cleaning, and normalization pipeline',
     2026, None),
    ('reference',
     'Correlates of War Project. State System Membership (v2024)',
     'Sovereign state codes for country name normalization',
     2024, 'https://correlatesofwar.org/data-sets/state-system-membership/'),
    ('reference',
     'International Commission on Stratigraphy. International Chronostratigraphic Chart (GTS 2020)',
     'ICS standard geological time scale for temporal_ranges normalization',
     2020, 'https://stratigraphy.org/chart'),
]

UI_DISPLAY_INTENT = [
    ('genera', 'tree', 'Taxonomic hierarchy is the primary organizational structure',
     'taxonomy_tree', 0),
    ('genera', 'table', 'Flat listing for search and filtering',
     'genera_list', 1),
    ('references', 'table', 'Literature references as a sortable list',
     'bibliography_list', 0),
    ('synonyms', 'graph', 'Synonym relationships form a network', None, 0),
    ('formations', 'table', 'Geological formations as a searchable list',
     'formations_list', 0),
    ('countries', 'table', 'Countries with genera counts',
     'countries_list', 0),
]


def _load_from_reference_db(rebuild_conn: sqlite3.Connection,
                            ref_db_path: Path):
    """Copy ui_queries, ui_manifest, and schema_descriptions from reference DB.

    This ensures exact reproduction of the complex SQL queries and manifest JSON.
    """
    cur = rebuild_conn.cursor()

    ref_conn = sqlite3.connect(str(ref_db_path))
    ref_cur = ref_conn.cursor()

    # --- ui_queries ---
    ref_cur.execute("""
        SELECT id, name, description, sql, params_json
        FROM ui_queries ORDER BY id
    """)
    queries = ref_cur.fetchall()
    for qid, name, desc, sql, params in queries:
        cur.execute("""
            INSERT OR IGNORE INTO ui_queries (id, name, description, sql, params_json)
            VALUES (?, ?, ?, ?, ?)
        """, (qid, name, desc, sql, params))
    print(f'    ui_queries: {len(queries)} copied')

    # --- ui_manifest ---
    ref_cur.execute("SELECT name, description, manifest_json FROM ui_manifest")
    manifests = ref_cur.fetchall()
    for name, desc, manifest_json in manifests:
        cur.execute("""
            INSERT INTO ui_manifest (name, description, manifest_json)
            VALUES (?, ?, ?)
        """, (name, desc, manifest_json))
    print(f'    ui_manifest: {len(manifests)} copied')

    # --- schema_descriptions ---
    ref_cur.execute("SELECT table_name, column_name, description FROM schema_descriptions")
    descs = ref_cur.fetchall()
    for table_name, column_name, description in descs:
        cur.execute("""
            INSERT INTO schema_descriptions (table_name, column_name, description)
            VALUES (?, ?, ?)
        """, (table_name, column_name, description))
    print(f'    schema_descriptions: {len(descs)} copied')

    ref_conn.close()
    rebuild_conn.commit()


def load_metadata(db_path: Path, ref_db_path: Path | None = None):
    """Insert all SCODA metadata into the trilobase DB.

    If ref_db_path is provided, copies ui_queries, ui_manifest, and
    schema_descriptions from it. Otherwise uses hardcoded data.
    """
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Create metadata tables
    conn.executescript(METADATA_DDL)

    # artifact_metadata
    cur.executemany(
        "INSERT OR IGNORE INTO artifact_metadata (key, value) VALUES (?, ?)",
        ARTIFACT_METADATA,
    )

    # provenance
    cur.executemany("""
        INSERT INTO provenance (source_type, citation, description, year, url)
        VALUES (?, ?, ?, ?, ?)
    """, PROVENANCE)

    # ui_display_intent
    cur.executemany("""
        INSERT INTO ui_display_intent
            (entity, default_view, description, source_query, priority)
        VALUES (?, ?, ?, ?, ?)
    """, UI_DISPLAY_INTENT)

    conn.commit()

    # Copy complex data from reference DB
    if ref_db_path and ref_db_path.exists():
        print('  [metadata] Copying from reference DB...')
        _load_from_reference_db(conn, ref_db_path)
    else:
        print('  [metadata] No reference DB; metadata tables created with constants only')

    conn.close()
