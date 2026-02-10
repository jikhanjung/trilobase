"""
Phase 15: Add SCODA UI Manifest table

Creates:
  - ui_manifest: Declarative view definitions as JSON
    Defines view structure (columns, sort, search) for SCODA viewers
"""

import sqlite3
import os
import sys
import json
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trilobase.db')


def create_table(conn):
    """Create UI Manifest table."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ui_manifest (
            name TEXT PRIMARY KEY,
            description TEXT,
            manifest_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    print("ui_manifest table created.")


def insert_manifest(conn):
    """Insert default manifest with 6 view definitions."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    manifest = {
        "default_view": "taxonomy_tree",
        "views": {
            "taxonomy_tree": {
                "type": "tree",
                "title": "Taxonomy Tree",
                "description": "Hierarchical classification from Class to Family",
                "source_query": "taxonomy_tree",
                "icon": "bi-diagram-3",
                "options": {
                    "root_rank": "Class",
                    "leaf_rank": "Family",
                    "show_genera_count": True
                }
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
                    {"key": "is_valid", "label": "Valid", "sortable": True, "searchable": False, "type": "boolean"}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
            },
            "genus_detail": {
                "type": "detail",
                "title": "Genus Detail",
                "description": "Detailed information for a single genus",
                "source_query": "genus_detail",
                "sections": [
                    {
                        "title": "Basic Information",
                        "fields": [
                            {"key": "name", "label": "Name", "italic": True},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "family_name", "label": "Family"},
                            {"key": "is_valid", "label": "Status", "type": "boolean", "true_label": "Valid", "false_label": "Invalid"},
                            {"key": "temporal_code", "label": "Temporal Range"}
                        ]
                    },
                    {
                        "title": "Type Species",
                        "fields": [
                            {"key": "type_species", "label": "Species", "italic": True},
                            {"key": "type_species_author", "label": "Author"}
                        ]
                    },
                    {
                        "title": "Geography",
                        "fields": [
                            {"key": "formation", "label": "Formation"},
                            {"key": "location", "label": "Location"}
                        ],
                        "related_queries": ["genus_formations", "genus_locations"]
                    }
                ]
            },
            "references_table": {
                "type": "table",
                "title": "Bibliography",
                "description": "Literature references from Jell & Adrain (2002)",
                "source_query": "bibliography_list",
                "icon": "bi-book",
                "columns": [
                    {"key": "authors", "label": "Authors", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "title", "label": "Title", "sortable": False, "searchable": True},
                    {"key": "journal", "label": "Journal", "sortable": True, "searchable": True},
                    {"key": "volume", "label": "Volume", "sortable": False, "searchable": False},
                    {"key": "pages", "label": "Pages", "sortable": False, "searchable": False},
                    {"key": "reference_type", "label": "Type", "sortable": True, "searchable": False}
                ],
                "default_sort": {"key": "authors", "direction": "asc"},
                "searchable": True
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
                    {"key": "taxa_count", "label": "Taxa", "sortable": True, "searchable": False, "type": "number"}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
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
                    {"key": "taxa_count", "label": "Taxa", "sortable": True, "searchable": False, "type": "number"}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
            }
        }
    }

    cursor.execute(
        "INSERT OR REPLACE INTO ui_manifest (name, description, manifest_json, created_at) "
        "VALUES (?, ?, ?, ?)",
        ('default', 'Default UI manifest for Trilobase viewer', json.dumps(manifest), now)
    )

    conn.commit()
    print(f"Inserted default manifest with {len(manifest['views'])} view definitions.")


def insert_schema_descriptions(conn):
    """Add schema descriptions for ui_manifest table."""
    cursor = conn.cursor()

    descriptions = [
        ('ui_manifest', None,
         'SCODA UI manifest: declarative view definitions as JSON'),
        ('ui_manifest', 'name',
         'Manifest identifier (e.g., default)'),
        ('ui_manifest', 'description',
         'Human-readable description of this manifest'),
        ('ui_manifest', 'manifest_json',
         'JSON object defining views, columns, sort, search, and layout'),
        ('ui_manifest', 'created_at',
         'ISO timestamp of manifest creation'),
    ]

    for table_name, column_name, desc in descriptions:
        cursor.execute(
            "INSERT OR REPLACE INTO schema_descriptions (table_name, column_name, description) "
            "VALUES (?, ?, ?)",
            (table_name, column_name, desc)
        )

    conn.commit()
    print(f"Inserted {len(descriptions)} schema descriptions for ui_manifest.")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    print(f"Adding SCODA UI Manifest to: {db_path}")
    conn = sqlite3.connect(db_path)

    create_table(conn)
    insert_manifest(conn)
    insert_schema_descriptions(conn)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ui_manifest")
    print(f"\nVerification:")
    print(f"  ui_manifest: {cursor.fetchone()[0]} entries")

    cursor.execute("SELECT name FROM ui_manifest")
    for row in cursor.fetchall():
        print(f"    - {row[0]}")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
