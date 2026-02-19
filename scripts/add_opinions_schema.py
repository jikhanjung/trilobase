"""
B-1 Taxonomic Opinions PoC: DB schema migration.

Creates:
  - taxonomic_opinions table (CHECK constraints, partial unique index, triggers)
  - is_placeholder column on taxonomic_ranks
  - Adrain 2011 bibliography entry
  - Eurekiidae sample opinions (2 PLACED_IN records)
  - taxon_opinions named query
  - Manifest update (rank_detail opinions section)
  - Schema descriptions

Usage:
    python scripts/add_opinions_schema.py                 # Apply to trilobase.db
    python scripts/add_opinions_schema.py --dry-run       # Preview only
    python scripts/add_opinions_schema.py path/to/db      # Custom DB path
"""

import sqlite3
import os
import sys
import json
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')


def table_exists(cursor, name):
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cursor.fetchone()[0] > 0


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def trigger_exists(cursor, name):
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name=?", (name,))
    return cursor.fetchone()[0] > 0


def create_opinions_table(conn, dry_run=False):
    cursor = conn.cursor()
    if table_exists(cursor, 'taxonomic_opinions'):
        print("  [SKIP] taxonomic_opinions table already exists")
        return

    sql = """
        CREATE TABLE taxonomic_opinions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            taxon_id            INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
            opinion_type        TEXT NOT NULL
                                CHECK(opinion_type IN ('PLACED_IN', 'VALID_AS', 'SYNONYM_OF')),
            related_taxon_id    INTEGER REFERENCES taxonomic_ranks(id),
            proposed_valid      INTEGER,
            bibliography_id     INTEGER REFERENCES bibliography(id),
            assertion_status    TEXT DEFAULT 'asserted'
                                CHECK(assertion_status IN (
                                    'asserted', 'incertae_sedis', 'questionable', 'indet'
                                )),
            curation_confidence TEXT DEFAULT 'high'
                                CHECK(curation_confidence IN ('high', 'medium', 'low')),
            is_accepted         INTEGER DEFAULT 0,
            notes               TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    print("  [CREATE] taxonomic_opinions table")
    if not dry_run:
        cursor.execute(sql)

    # Indexes
    print("  [CREATE] idx_opinions_taxon, idx_opinions_type")
    if not dry_run:
        cursor.execute("CREATE INDEX idx_opinions_taxon ON taxonomic_opinions(taxon_id)")
        cursor.execute("CREATE INDEX idx_opinions_type ON taxonomic_opinions(opinion_type)")

    print("  [CREATE] idx_unique_accepted_opinion (partial unique)")
    if not dry_run:
        cursor.execute("""
            CREATE UNIQUE INDEX idx_unique_accepted_opinion
            ON taxonomic_opinions(taxon_id, opinion_type)
            WHERE is_accepted = 1
        """)

    if not dry_run:
        conn.commit()


def create_triggers(conn, dry_run=False):
    cursor = conn.cursor()

    # BEFORE INSERT: deactivate existing accepted (before unique index check)
    if trigger_exists(cursor, 'trg_deactivate_before_insert'):
        print("  [SKIP] trg_deactivate_before_insert already exists")
    else:
        print("  [CREATE] trg_deactivate_before_insert")
        if not dry_run:
            cursor.execute("""
                CREATE TRIGGER trg_deactivate_before_insert
                BEFORE INSERT ON taxonomic_opinions
                WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
                BEGIN
                    UPDATE taxonomic_opinions
                    SET is_accepted = 0
                    WHERE taxon_id = NEW.taxon_id
                      AND opinion_type = 'PLACED_IN'
                      AND is_accepted = 1;
                END
            """)

    # AFTER INSERT: sync parent_id
    if trigger_exists(cursor, 'trg_sync_parent_insert'):
        print("  [SKIP] trg_sync_parent_insert already exists")
    else:
        print("  [CREATE] trg_sync_parent_insert")
        if not dry_run:
            cursor.execute("""
                CREATE TRIGGER trg_sync_parent_insert
                AFTER INSERT ON taxonomic_opinions
                WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
                BEGIN
                    UPDATE taxonomic_ranks
                    SET parent_id = NEW.related_taxon_id
                    WHERE id = NEW.taxon_id;
                END
            """)

    # BEFORE UPDATE: deactivate other accepted (before unique index check)
    if trigger_exists(cursor, 'trg_deactivate_before_update'):
        print("  [SKIP] trg_deactivate_before_update already exists")
    else:
        print("  [CREATE] trg_deactivate_before_update")
        if not dry_run:
            cursor.execute("""
                CREATE TRIGGER trg_deactivate_before_update
                BEFORE UPDATE OF is_accepted ON taxonomic_opinions
                WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
                BEGIN
                    UPDATE taxonomic_opinions
                    SET is_accepted = 0
                    WHERE taxon_id = NEW.taxon_id
                      AND opinion_type = 'PLACED_IN'
                      AND is_accepted = 1
                      AND id != NEW.id;
                END
            """)

    # AFTER UPDATE: sync parent_id
    if trigger_exists(cursor, 'trg_sync_parent_update'):
        print("  [SKIP] trg_sync_parent_update already exists")
    else:
        print("  [CREATE] trg_sync_parent_update")
        if not dry_run:
            cursor.execute("""
                CREATE TRIGGER trg_sync_parent_update
                AFTER UPDATE OF is_accepted ON taxonomic_opinions
                WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
                BEGIN
                    UPDATE taxonomic_ranks
                    SET parent_id = NEW.related_taxon_id
                    WHERE id = NEW.taxon_id;
                END
            """)

    if not dry_run:
        conn.commit()


def add_is_placeholder(conn, dry_run=False):
    cursor = conn.cursor()
    if column_exists(cursor, 'taxonomic_ranks', 'is_placeholder'):
        print("  [SKIP] is_placeholder column already exists")
        return

    print("  [ALTER] taxonomic_ranks ADD COLUMN is_placeholder")
    if not dry_run:
        cursor.execute("ALTER TABLE taxonomic_ranks ADD COLUMN is_placeholder INTEGER DEFAULT 0")

    # Mark placeholder nodes
    print("  [UPDATE] Mark Uncertain nodes as placeholder")
    if not dry_run:
        cursor.execute("""
            UPDATE taxonomic_ranks SET is_placeholder = 1
            WHERE name = 'Uncertain' AND rank IN ('Order', 'Superfamily')
        """)
        count = cursor.rowcount
        print(f"           → {count} rows marked")
        conn.commit()


def add_adrain_2011(conn, dry_run=False):
    """Add Adrain 2011 to bibliography if not already present."""
    cursor = conn.cursor()

    # Check if already exists
    cursor.execute("SELECT id FROM bibliography WHERE authors LIKE '%ADRAIN%' AND year = 2011")
    row = cursor.fetchone()
    if row:
        print(f"  [SKIP] Adrain 2011 already in bibliography (id={row[0]})")
        return row[0]

    print("  [INSERT] Adrain 2011 into bibliography")
    if not dry_run:
        cursor.execute("""
            INSERT INTO bibliography (authors, year, title, journal, volume, pages, reference_type, raw_entry,
                uid, uid_method, uid_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'ADRAIN, J.M.', 2011,
            'Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification and survey of taxonomic richness',
            'Zootaxa', '3148', '104-109', 'article',
            'ADRAIN, J.M. (2011) Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification and survey of taxonomic richness. Zootaxa, 3148, 104-109.',
            'scoda:bib:fp_v1:sha256:adrain_2011_zootaxa3148', 'fp_v1', 'medium'
        ))
        conn.commit()
        bib_id = cursor.lastrowid
        print(f"           → id={bib_id}")
        return bib_id
    else:
        return None


def insert_eurekiidae_opinions(conn, dry_run=False):
    """Insert sample opinions for Eurekiidae (id=164)."""
    cursor = conn.cursor()

    # Check if opinions already exist
    cursor.execute("SELECT COUNT(*) FROM taxonomic_opinions WHERE taxon_id = 164")
    if cursor.fetchone()[0] > 0:
        print("  [SKIP] Eurekiidae opinions already exist")
        return

    # Get Adrain 2011 bibliography id
    cursor.execute("SELECT id FROM bibliography WHERE authors LIKE '%ADRAIN%' AND year = 2011")
    adrain_row = cursor.fetchone()
    adrain_id = adrain_row[0] if adrain_row else None

    if adrain_id is None:
        print("  [WARN] Adrain 2011 not found in bibliography, skipping opinions")
        return

    print("  [INSERT] Eurekiidae opinion 1: incertae sedis (Adrain 2011, accepted)")
    if not dry_run:
        cursor.execute("""
            INSERT INTO taxonomic_opinions
                (taxon_id, opinion_type, related_taxon_id, bibliography_id,
                 assertion_status, curation_confidence, is_accepted)
            VALUES (164, 'PLACED_IN', 144, ?, 'incertae_sedis', 'high', 1)
        """, (adrain_id,))

    print("  [INSERT] Eurekiidae opinion 2: Asaphida (alternative)")
    if not dry_run:
        cursor.execute("""
            INSERT INTO taxonomic_opinions
                (taxon_id, opinion_type, related_taxon_id, bibliography_id,
                 assertion_status, curation_confidence, is_accepted,
                 notes)
            VALUES (164, 'PLACED_IN', 115, NULL, 'asserted', 'medium', 0,
                    'Hypothetical example for PoC — some authors have suggested Asaphida affinity')
        """)
        conn.commit()
        print("           → 2 opinions inserted")


def add_taxon_opinions_query(conn, dry_run=False):
    """Add taxon_opinions named query to ui_queries."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ui_queries WHERE name = 'taxon_opinions'")
    if cursor.fetchone()[0] > 0:
        print("  [SKIP] taxon_opinions query already exists")
        return

    sql = (
        "SELECT o.id, o.opinion_type, o.related_taxon_id, "
        "t.name as related_taxon_name, t.rank as related_taxon_rank, "
        "o.bibliography_id, b.authors as bib_authors, b.year as bib_year, "
        "o.assertion_status, o.curation_confidence, o.is_accepted, o.notes, o.created_at "
        "FROM taxonomic_opinions o "
        "LEFT JOIN taxonomic_ranks t ON o.related_taxon_id = t.id "
        "LEFT JOIN bibliography b ON o.bibliography_id = b.id "
        "WHERE o.taxon_id = :taxon_id "
        "ORDER BY o.is_accepted DESC, o.created_at"
    )
    print("  [INSERT] taxon_opinions named query")
    if not dry_run:
        cursor.execute(
            "INSERT INTO ui_queries (name, description, sql, params_json, created_at) VALUES (?, ?, ?, ?, ?)",
            ('taxon_opinions', 'Taxonomic opinions for a specific taxon',
             sql, '{"taxon_id": "integer"}', datetime.now().isoformat())
        )
        conn.commit()


def update_manifest_opinions(conn, dry_run=False):
    """Add opinions sub_query and section to rank_detail view in manifest."""
    cursor = conn.cursor()
    cursor.execute("SELECT manifest_json FROM ui_manifest WHERE name = 'default'")
    row = cursor.fetchone()
    if not row:
        print("  [SKIP] No default manifest found")
        return

    manifest = json.loads(row[0])
    rank_detail = manifest.get('views', {}).get('rank_detail')
    if not rank_detail:
        print("  [SKIP] No rank_detail view in manifest")
        return

    # Check if already has opinions sub_query
    sub_queries = rank_detail.get('sub_queries', {})
    if 'opinions' in sub_queries:
        print("  [SKIP] rank_detail already has opinions sub_query")
        return

    # Add sub_queries if not present
    if 'sub_queries' not in rank_detail:
        rank_detail['sub_queries'] = {}
    rank_detail['sub_queries']['opinions'] = {
        "query": "taxon_opinions",
        "params": {"taxon_id": "id"}
    }

    # Also ensure source_query and source_param exist for composite endpoint
    if 'source_query' not in rank_detail:
        rank_detail['source_query'] = 'rank_detail'
    if 'source_param' not in rank_detail:
        rank_detail['source_param'] = 'rank_id'

    # Add opinions section before "My Notes" (annotations)
    opinions_section = {
        "title": "Taxonomic Opinions ({count})",
        "type": "linked_table",
        "data_key": "opinions",
        "condition": "opinions",
        "columns": [
            {"key": "related_taxon_name", "label": "Proposed Parent"},
            {"key": "related_taxon_rank", "label": "Rank"},
            {"key": "bib_authors", "label": "Author"},
            {"key": "bib_year", "label": "Year"},
            {"key": "assertion_status", "label": "Status"},
            {"key": "is_accepted", "label": "Accepted", "format": "boolean"}
        ],
        "on_row_click": {"detail_view": "rank_detail", "id_key": "related_taxon_id"}
    }

    sections = rank_detail.get('sections', [])
    # Find annotations section index and insert before it
    insert_idx = len(sections)
    for i, s in enumerate(sections):
        if s.get('type') == 'annotations':
            insert_idx = i
            break
    sections.insert(insert_idx, opinions_section)

    print("  [UPDATE] rank_detail manifest: added opinions sub_query + section")
    if not dry_run:
        cursor.execute(
            "UPDATE ui_manifest SET manifest_json = ? WHERE name = 'default'",
            (json.dumps(manifest),)
        )
        conn.commit()


def add_schema_descriptions(conn, dry_run=False):
    """Add schema descriptions for taxonomic_opinions and is_placeholder."""
    cursor = conn.cursor()

    descriptions = [
        ('taxonomic_opinions', None, 'Taxonomic opinions — multiple classification viewpoints per taxon'),
        ('taxonomic_opinions', 'taxon_id', 'Subject taxon of this opinion'),
        ('taxonomic_opinions', 'opinion_type', 'PLACED_IN, VALID_AS, or SYNONYM_OF'),
        ('taxonomic_opinions', 'related_taxon_id', 'Target taxon (parent for PLACED_IN, senior for SYNONYM_OF)'),
        ('taxonomic_opinions', 'proposed_valid', 'Proposed validity for VALID_AS (1=valid, 0=invalid)'),
        ('taxonomic_opinions', 'bibliography_id', 'Source reference for this opinion'),
        ('taxonomic_opinions', 'assertion_status', 'Author certainty: asserted, incertae_sedis, questionable, indet'),
        ('taxonomic_opinions', 'curation_confidence', 'Curator confidence: high, medium, low'),
        ('taxonomic_opinions', 'is_accepted', 'Whether this is the currently accepted opinion (max 1 per taxon+type)'),
        ('taxonomic_ranks', 'is_placeholder', 'Whether this node is a placeholder (e.g., Uncertain Order)'),
    ]

    inserted = 0
    for table_name, column_name, desc in descriptions:
        cursor.execute(
            "SELECT COUNT(*) FROM schema_descriptions WHERE table_name = ? AND column_name IS ?",
            (table_name, column_name)
        )
        if cursor.fetchone()[0] > 0:
            continue
        if not dry_run:
            cursor.execute(
                "INSERT INTO schema_descriptions (table_name, column_name, description) VALUES (?, ?, ?)",
                (table_name, column_name, desc)
            )
        inserted += 1

    if inserted > 0:
        print(f"  [INSERT] {inserted} schema descriptions")
        if not dry_run:
            conn.commit()
    else:
        print("  [SKIP] Schema descriptions already exist")


def main():
    dry_run = '--dry-run' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--dry-run']
    db_path = args[0] if args else DB_PATH

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    mode = " (DRY RUN)" if dry_run else ""
    print(f"=== B-1 Taxonomic Opinions Schema Migration{mode} ===")
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    print("[1/7] Create taxonomic_opinions table + indexes")
    create_opinions_table(conn, dry_run)

    print("\n[2/7] Create parent_id sync triggers")
    create_triggers(conn, dry_run)

    print("\n[3/7] Add is_placeholder column to taxonomic_ranks")
    add_is_placeholder(conn, dry_run)

    print("\n[4/7] Add Adrain 2011 to bibliography")
    add_adrain_2011(conn, dry_run)

    print("\n[5/7] Insert Eurekiidae sample opinions")
    if table_exists(conn.cursor(), 'taxonomic_opinions'):
        insert_eurekiidae_opinions(conn, dry_run)
    else:
        print("  [SKIP] taxonomic_opinions table not created (dry-run)")

    print("\n[6/7] Add taxon_opinions named query + update manifest")
    add_taxon_opinions_query(conn, dry_run)
    update_manifest_opinions(conn, dry_run)

    print("\n[7/7] Add schema descriptions")
    add_schema_descriptions(conn, dry_run)

    # Verification
    if not dry_run:
        cursor = conn.cursor()
        print("\n=== Verification ===")
        cursor.execute("SELECT COUNT(*) FROM taxonomic_opinions")
        print(f"  taxonomic_opinions: {cursor.fetchone()[0]} records")
        cursor.execute("SELECT COUNT(*) FROM taxonomic_ranks WHERE is_placeholder = 1")
        print(f"  placeholder nodes: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM bibliography WHERE authors LIKE '%ADRAIN%' AND year = 2011")
        print(f"  Adrain 2011 in bibliography: {'Yes' if cursor.fetchone()[0] > 0 else 'No'}")
        cursor.execute("SELECT COUNT(*) FROM ui_queries WHERE name = 'taxon_opinions'")
        print(f"  taxon_opinions query: {'Yes' if cursor.fetchone()[0] > 0 else 'No'}")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
