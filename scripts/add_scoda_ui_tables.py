"""
Phase 14: Add SCODA Display Intent and Saved Queries tables

Creates:
  - ui_display_intent: View type hints for SCODA viewers
  - ui_queries: Named, reusable queries as a stable interface layer
"""

import sqlite3
import os
import sys
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trilobase.db')


def create_tables(conn):
    """Create Display Intent and Saved Queries tables."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ui_display_intent (
            id INTEGER PRIMARY KEY,
            entity TEXT NOT NULL,
            default_view TEXT NOT NULL,
            description TEXT,
            source_query TEXT,
            priority INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ui_queries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            sql TEXT NOT NULL,
            params_json TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    print("UI tables created.")


def insert_display_intents(conn):
    """Insert display intent hints for SCODA viewers."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    intents = [
        (1, 'genera', 'tree',
         'Taxonomic hierarchy is the primary organizational structure',
         'taxonomy_tree', 0),
        (2, 'genera', 'table',
         'Flat listing for search and filtering',
         'genera_list', 1),
        (3, 'references', 'table',
         'Literature references as a sortable list',
         'bibliography_list', 0),
        (4, 'synonyms', 'graph',
         'Synonym relationships form a network',
         None, 0),
        (5, 'formations', 'table',
         'Geological formations as a searchable list',
         'formations_list', 0),
        (6, 'countries', 'table',
         'Countries with genera counts',
         'countries_list', 0),
    ]

    for i in intents:
        cursor.execute(
            "INSERT OR REPLACE INTO ui_display_intent "
            "(id, entity, default_view, description, source_query, priority) "
            "VALUES (?, ?, ?, ?, ?, ?)", i
        )

    conn.commit()
    print(f"Inserted {len(intents)} display intents.")


def insert_queries(conn):
    """Insert named queries extracted from app.py and additional useful queries."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    queries = [
        ('taxonomy_tree',
         'Hierarchical tree from Class to Family (excludes Genus)',
         """SELECT id, name, rank, parent_id, author, genera_count
FROM taxonomic_ranks
WHERE rank != 'Genus'
ORDER BY rank, name""",
         None),

        ('family_genera',
         'List of genera belonging to a specific family',
         """SELECT id, name, author, year, type_species, location, is_valid
FROM taxonomic_ranks
WHERE parent_id = :family_id AND rank = 'Genus'
ORDER BY name""",
         '{"family_id": "integer — taxonomic_ranks.id of the Family"}'),

        ('genus_detail',
         'Full detail for a single genus including family name',
         """SELECT tr.*, parent.name as family_name
FROM taxonomic_ranks tr
LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id
WHERE tr.id = :genus_id AND tr.rank = 'Genus'""",
         '{"genus_id": "integer — taxonomic_ranks.id of the Genus"}'),

        ('rank_detail',
         'Detail for any taxonomic rank with parent info',
         """SELECT tr.*, parent.name as parent_name, parent.rank as parent_rank
FROM taxonomic_ranks tr
LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id
WHERE tr.id = :rank_id""",
         '{"rank_id": "integer — taxonomic_ranks.id"}'),

        ('genera_list',
         'Flat list of all genera with family and validity',
         """SELECT g.id, g.name, g.author, g.year, g.family, g.temporal_code,
       g.is_valid, g.location
FROM taxonomic_ranks g
WHERE g.rank = 'Genus'
ORDER BY g.name""",
         None),

        ('valid_genera_list',
         'Flat list of valid genera only',
         """SELECT g.id, g.name, g.author, g.year, g.family, g.temporal_code, g.location
FROM taxonomic_ranks g
WHERE g.rank = 'Genus' AND g.is_valid = 1
ORDER BY g.name""",
         None),

        ('genus_synonyms',
         'Synonyms for a specific genus',
         """SELECT s.*, senior.name as senior_name
FROM synonyms s
LEFT JOIN taxonomic_ranks senior ON s.senior_taxon_id = senior.id
WHERE s.junior_taxon_id = :genus_id""",
         '{"genus_id": "integer — taxonomic_ranks.id of the junior taxon"}'),

        ('genus_formations',
         'Formations where a genus was found',
         """SELECT f.id, f.name, f.formation_type, f.country, f.period
FROM genus_formations gf
JOIN formations f ON gf.formation_id = f.id
WHERE gf.genus_id = :genus_id""",
         '{"genus_id": "integer — taxonomic_ranks.id"}'),

        ('genus_locations',
         'Countries/regions where a genus was found',
         """SELECT c.id, c.name as country, gl.region
FROM genus_locations gl
JOIN countries c ON gl.country_id = c.id
WHERE gl.genus_id = :genus_id""",
         '{"genus_id": "integer — taxonomic_ranks.id"}'),

        ('bibliography_list',
         'All literature references sorted by year',
         """SELECT id, authors, year, year_suffix, title, journal, volume, pages,
       reference_type
FROM bibliography
ORDER BY authors, year""",
         None),

        ('formations_list',
         'All formations with taxa counts',
         """SELECT id, name, formation_type, country, period, taxa_count
FROM formations
ORDER BY name""",
         None),

        ('countries_list',
         'All countries with taxa counts',
         """SELECT id, name, code, taxa_count
FROM countries
ORDER BY name""",
         None),

        ('genera_by_country',
         'Genera found in a specific country',
         """SELECT g.id, g.name, g.author, g.year, gl.region
FROM taxonomic_ranks g
JOIN genus_locations gl ON g.id = gl.genus_id
JOIN countries c ON gl.country_id = c.id
WHERE c.name = :country_name
ORDER BY g.name""",
         '{"country_name": "string — country name (e.g., China)"}'),

        ('genera_by_period',
         'Genera from a specific geological time period',
         """SELECT id, name, author, year, family, location
FROM taxonomic_ranks
WHERE rank = 'Genus' AND temporal_code = :temporal_code AND is_valid = 1
ORDER BY name""",
         '{"temporal_code": "string — e.g., LCAM, UDEV, MISS"}'),
    ]

    for name, desc, sql, params in queries:
        cursor.execute(
            "INSERT OR REPLACE INTO ui_queries (name, description, sql, params_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, desc, sql, params, now)
        )

    conn.commit()
    print(f"Inserted {len(queries)} named queries.")


def insert_schema_descriptions(conn):
    """Add schema descriptions for new tables."""
    cursor = conn.cursor()

    descriptions = [
        ('ui_display_intent', None,
         'SCODA display intent hints: how each entity should be viewed'),
        ('ui_display_intent', 'entity',
         'Data entity name (e.g., genera, references, synonyms)'),
        ('ui_display_intent', 'default_view',
         'View type from vocabulary: tree, table, detail, map, timeline, graph'),
        ('ui_display_intent', 'description',
         'Why this view type is appropriate for this entity'),
        ('ui_display_intent', 'source_query',
         'Name of ui_queries entry to use as data source'),
        ('ui_display_intent', 'priority',
         '0 = primary view, 1+ = alternative views'),

        ('ui_queries', None,
         'Named, reusable SQL queries as a stable interface layer'),
        ('ui_queries', 'name', 'Unique query identifier'),
        ('ui_queries', 'description', 'What this query returns'),
        ('ui_queries', 'sql', 'SQL query text (uses :param_name for parameters)'),
        ('ui_queries', 'params_json',
         'JSON describing parameters: {"param_name": "description"}'),
        ('ui_queries', 'created_at', 'ISO timestamp of creation'),
    ]

    for table_name, column_name, desc in descriptions:
        cursor.execute(
            "INSERT OR REPLACE INTO schema_descriptions (table_name, column_name, description) "
            "VALUES (?, ?, ?)",
            (table_name, column_name, desc)
        )

    conn.commit()
    print(f"Inserted {len(descriptions)} schema descriptions for new tables.")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    print(f"Adding SCODA UI tables to: {db_path}")
    conn = sqlite3.connect(db_path)

    create_tables(conn)
    insert_display_intents(conn)
    insert_queries(conn)
    insert_schema_descriptions(conn)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ui_display_intent")
    print(f"\nVerification:")
    print(f"  ui_display_intent: {cursor.fetchone()[0]} entries")
    cursor.execute("SELECT COUNT(*) FROM ui_queries")
    print(f"  ui_queries: {cursor.fetchone()[0]} entries")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
