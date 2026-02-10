"""
Phase 17: Add user_annotations table to trilobase.db

Creates:
  - user_annotations: Local overlay for user notes, corrections, alternatives, links
"""

import sqlite3
import os
import sys


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trilobase.db')


def create_tables(conn):
    """Create user_annotations table and index."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            annotation_type TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_annotations_entity
            ON user_annotations(entity_type, entity_id)
    """)

    conn.commit()
    print("user_annotations table created.")


def insert_schema_descriptions(conn):
    """Insert schema descriptions for user_annotations."""
    cursor = conn.cursor()

    descriptions = [
        ('user_annotations', None,
         'User annotations (local overlay): notes, corrections, alternatives, and links on any entity'),
        ('user_annotations', 'id', 'Primary key'),
        ('user_annotations', 'entity_type',
         'Type of annotated entity: genus, family, order, suborder, superfamily, class'),
        ('user_annotations', 'entity_id',
         'FK to taxonomic_ranks.id — the annotated record'),
        ('user_annotations', 'annotation_type',
         'Type of annotation: note, correction, alternative, link'),
        ('user_annotations', 'content',
         'Annotation text content'),
        ('user_annotations', 'author',
         'Author of the annotation (optional)'),
        ('user_annotations', 'created_at',
         'Timestamp of annotation creation (UTC)'),
    ]

    for table_name, column_name, desc in descriptions:
        cursor.execute(
            "INSERT OR REPLACE INTO schema_descriptions (table_name, column_name, description) "
            "VALUES (?, ?, ?)",
            (table_name, column_name, desc)
        )

    conn.commit()
    print(f"Inserted {len(descriptions)} schema descriptions for user_annotations.")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    print(f"Adding user_annotations table to: {db_path}")
    conn = sqlite3.connect(db_path)

    create_tables(conn)
    insert_schema_descriptions(conn)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_annotations")
    print(f"\nVerification:")
    print(f"  user_annotations: {cursor.fetchone()[0]} entries")
    cursor.execute(
        "SELECT COUNT(*) FROM schema_descriptions WHERE table_name = 'user_annotations'")
    print(f"  schema_descriptions (user_annotations): {cursor.fetchone()[0]} entries")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
