"""
Phase 15/39: SCODA UI Manifest table

Creates/updates:
  - ui_manifest: Declarative view definitions as JSON
    Defines view structure (columns, sort, search, detail views) for SCODA viewers

Phase 39 additions:
  - Detail view definitions for all 7 entity types
  - on_row_click for table views (manifest-driven navigation)
  - chronostratigraphy_table (was missing from script since Phase 30)
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
    """Insert default manifest with 14 view definitions (7 tab + 7 detail)."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    manifest = {
        "default_view": "taxonomy_tree",
        "views": {
            # ── Tab Views (tree, table, chart) ──────────────────────

            "taxonomy_tree": {
                "type": "tree",
                "title": "Taxonomy Tree",
                "description": "Hierarchical classification from Class to Family",
                "source_query": "taxonomy_tree",
                "icon": "bi-diagram-3",
                "tree_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "rank_key": "rank",
                    "leaf_rank": "Family",
                    "count_key": "genera_count",
                    "on_node_info": {"detail_view": "rank_detail", "id_key": "id"},
                    "item_query": "family_genera",
                    "item_param": "family_id",
                    "item_columns": [
                        {"key": "name", "label": "Genus", "italic": True},
                        {"key": "author", "label": "Author"},
                        {"key": "year", "label": "Year"},
                        {"key": "type_species", "label": "Type Species", "truncate": 40},
                        {"key": "location", "label": "Location", "truncate": 30}
                    ],
                    "on_item_click": {"detail_view": "genus_detail", "id_key": "id"},
                    "item_valid_filter": {"key": "is_valid", "label": "Valid only", "default": True}
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
                "searchable": True,
                "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
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
                "searchable": True,
                "on_row_click": {"detail_view": "bibliography_detail", "id_key": "id"}
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
                "searchable": True,
                "on_row_click": {"detail_view": "formation_detail", "id_key": "id"}
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
                "searchable": True,
                "on_row_click": {"detail_view": "country_detail", "id_key": "id"}
            },
            "chronostratigraphy_table": {
                "type": "chart",
                "title": "Chronostratigraphy",
                "description": "ICS International Chronostratigraphic Chart (GTS 2020)",
                "source_query": "ics_chronostrat_list",
                "icon": "bi-clock-history",
                "columns": [
                    {"key": "name", "label": "Name", "sortable": True, "searchable": True},
                    {"key": "rank", "label": "Rank", "sortable": True, "searchable": True},
                    {"key": "start_mya", "label": "Start (Ma)", "sortable": True, "type": "number"},
                    {"key": "end_mya", "label": "End (Ma)", "sortable": True, "type": "number"},
                    {"key": "color", "label": "Color", "sortable": False, "type": "color"}
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

            # ── Detail Views ────────────────────────────────────────

            "formation_detail": {
                "type": "detail",
                "title": "Formation Detail",
                "source": "/api/formation/{id}",
                "icon": "bi-layers",
                "title_template": {"format": "{icon} {name}", "icon": "bi-layers"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "formation_type", "label": "Type"},
                            {"key": "country", "label": "Country",
                             "format": "link",
                             "link": {"detail_view": "country_detail", "id_path": "country_id"}},
                            {"key": "region", "label": "Region"},
                            {"key": "period", "label": "Period"},
                            {"key": "taxa_count", "label": "Taxa Count"}
                        ]
                    },
                    {
                        "title": "Genera ({count})",
                        "type": "linked_table",
                        "data_key": "genera",
                        "columns": [
                            {"key": "name", "label": "Genus", "italic": True},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year"},
                            {"key": "is_valid", "label": "Valid", "format": "boolean"}
                        ],
                        "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
                    }
                ]
            },
            "country_detail": {
                "type": "detail",
                "title": "Country Detail",
                "source": "/api/country/{id}",
                "icon": "bi-geo-alt",
                "title_template": {"format": "{icon} {name}", "icon": "bi-geo-alt"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "cow_ccode", "label": "COW Code"},
                            {"key": "taxa_count", "label": "Taxa Count"}
                        ]
                    },
                    {
                        "title": "Regions ({count})",
                        "type": "linked_table",
                        "data_key": "regions",
                        "condition": "regions",
                        "columns": [
                            {"key": "name", "label": "Region"},
                            {"key": "taxa_count", "label": "Taxa Count"}
                        ],
                        "on_row_click": {"detail_view": "region_detail", "id_key": "id"}
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
                            {"key": "is_valid", "label": "Valid", "format": "boolean"}
                        ],
                        "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
                    }
                ]
            },
            "region_detail": {
                "type": "detail",
                "title": "Region Detail",
                "source": "/api/region/{id}",
                "icon": "bi-geo-alt",
                "title_template": {"format": "{icon} {name}", "icon": "bi-geo-alt"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name"},
                            {"key": "parent.name", "label": "Country",
                             "format": "link",
                             "link": {"detail_view": "country_detail", "id_path": "parent.id"}},
                            {"key": "taxa_count", "label": "Taxa Count"}
                        ]
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
                            {"key": "is_valid", "label": "Valid", "format": "boolean"}
                        ],
                        "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
                    }
                ]
            },
            "bibliography_detail": {
                "type": "detail",
                "title": "Bibliography Detail",
                "source": "/api/composite/bibliography_detail?id={id}",
                "source_query": "bibliography_detail",
                "source_param": "bibliography_id",
                "sub_queries": {
                    "genera": {"query": "bibliography_genera", "params": {"author_name": "result.authors"}}
                },
                "icon": "bi-book",
                "title_template": {"format": "{icon} {authors}, {year}", "icon": "bi-book"},
                "sections": [
                    {
                        "title": "Basic Information",
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
                            {"key": "book_title", "label": "Book Title", "condition": "book_title"}
                        ]
                    },
                    {
                        "title": "Original Entry",
                        "type": "raw_text",
                        "data_key": "raw_entry",
                        "condition": "raw_entry"
                    },
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
                            {"key": "is_valid", "label": "Valid", "format": "boolean"}
                        ],
                        "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
                    }
                ]
            },
            "chronostrat_detail": {
                "type": "detail",
                "title": "Chronostratigraphy Detail",
                "source": "/api/chronostrat/{id}",
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
                            {"key": "ratified_gssp", "label": "Ratified GSSP", "format": "boolean"}
                        ]
                    },
                    {
                        "title": "Hierarchy",
                        "type": "field_grid",
                        "condition": "parent_name",
                        "fields": [
                            {"key": "parent_name", "label": "Parent",
                             "format": "link",
                             "link": {"detail_view": "chronostrat_detail", "id_path": "parent_detail_id"},
                             "suffix_key": "parent_rank", "suffix_format": "({value})"}
                        ]
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
                            {"key": "color", "label": "Color", "format": "color_chip"}
                        ],
                        "on_row_click": {"detail_view": "chronostrat_detail", "id_key": "id"}
                    },
                    {
                        "title": "Mapped Temporal Codes",
                        "type": "tagged_list",
                        "data_key": "mappings",
                        "condition": "mappings",
                        "badge_key": "temporal_code",
                        "badge_format": "code",
                        "text_key": "mapping_type"
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
                            {"key": "is_valid", "label": "Valid", "format": "boolean"}
                        ],
                        "on_row_click": {"detail_view": "genus_detail", "id_key": "id"}
                    }
                ]
            },
            "genus_detail": {
                "type": "detail",
                "title": "Genus Detail",
                "source": "/api/genus/{id}",
                "title_template": {"format": "<i>{name}</i> {author}, {year}"},
                "sections": [
                    {
                        "title": "Basic Information",
                        "type": "field_grid",
                        "fields": [
                            {"key": "name", "label": "Name", "format": "italic"},
                            {"key": "author", "label": "Author"},
                            {"key": "year", "label": "Year", "suffix_key": "year_suffix"},
                            {"key": "hierarchy", "label": "Classification", "format": "hierarchy",
                             "data_key": "hierarchy", "link": {"detail_view": "rank_detail"}},
                            {"key": "is_valid", "label": "Status",
                             "format": "boolean", "true_label": "Valid",
                             "false_label": "Invalid", "false_class": "invalid"},
                            {"key": "temporal_code", "label": "Temporal Range",
                             "format": "temporal_range",
                             "mapping_key": "ics_mapping", "link": {"detail_view": "chronostrat_detail"}}
                        ]
                    },
                    {
                        "title": "Type Species",
                        "type": "field_grid",
                        "condition": "type_species",
                        "fields": [
                            {"key": "type_species", "label": "Species", "format": "italic"},
                            {"key": "type_species_author", "label": "Author"}
                        ]
                    },
                    {
                        "title": "Geographic Information",
                        "type": "genus_geography"
                    },
                    {
                        "title": "Synonymy",
                        "type": "synonym_list",
                        "data_key": "synonyms",
                        "condition": "synonyms"
                    },
                    {
                        "title": "Notes",
                        "type": "raw_text",
                        "data_key": "notes",
                        "condition": "notes",
                        "format": "paragraph"
                    },
                    {
                        "title": "Original Entry",
                        "type": "raw_text",
                        "data_key": "raw_entry",
                        "condition": "raw_entry"
                    },
                    {
                        "title": "My Notes",
                        "type": "annotations",
                        "entity_type": "genus"
                    }
                ]
            },
            "rank_detail": {
                "type": "detail",
                "title": "Rank Detail",
                "source": "/api/rank/{id}",
                "title_template": {
                    "format": "<span class=\"badge bg-secondary me-2\">{rank}</span> {name}"
                },
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
                             "link": {"detail_view": "rank_detail", "id_path": "parent_id"},
                             "suffix_key": "parent_rank", "suffix_format": "({value})"}
                        ]
                    },
                    {
                        "title": "Statistics",
                        "type": "rank_statistics"
                    },
                    {
                        "title": "Children",
                        "type": "rank_children",
                        "data_key": "children",
                        "condition": "children"
                    },
                    {
                        "title": "Notes",
                        "type": "raw_text",
                        "data_key": "notes",
                        "condition": "notes",
                        "format": "paragraph"
                    },
                    {
                        "title": "My Notes",
                        "type": "annotations",
                        "entity_type_from": "rank"
                    }
                ]
            }
        }
    }

    cursor.execute(
        "INSERT OR REPLACE INTO ui_manifest (name, description, manifest_json, created_at) "
        "VALUES (?, ?, ?, ?)",
        ('default', 'Default UI manifest for Trilobase SCODA viewer', json.dumps(manifest), now)
    )

    conn.commit()
    tab_views = sum(1 for v in manifest['views'].values() if v['type'] != 'detail')
    detail_views = sum(1 for v in manifest['views'].values() if v['type'] == 'detail')
    print(f"Inserted default manifest with {len(manifest['views'])} views ({tab_views} tab + {detail_views} detail).")


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
