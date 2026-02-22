#!/usr/bin/env python3
"""
Add SPELLING_OF opinion type and create placeholder entries for orthographic variants.

- Adds 'SPELLING_OF' to taxonomic_opinions CHECK constraint (table rebuild)
- Re-inserts Dokimocephalidae, Chengkouaspidae as placeholder entries
- Creates SPELLING_OF opinions linking variants to canonical names

Idempotent: skips steps already completed.
Usage:
    python scripts/add_spelling_of_opinions.py [--dry-run]
"""

import argparse
import sqlite3
import sys

DB_PATH = 'db/trilobase.db'

# Canonical target IDs
DOKIMOKEPHALIDAE_ID = 134
CHENGKOUASPIDIDAE_ID = 36

PLACEHOLDERS = [
    {
        'name': 'Dokimocephalidae',
        'rank': 'Family',
        'parent_id': None,
        'genera_count': 0,
        'is_placeholder': 1,
        'uid': 'scoda:taxon:family:Dokimocephalidae',
        'uid_method': 'name',
        'uid_confidence': 'high',
        'notes': 'Orthographic variant of Dokimokephalidae. Jell & Adrain (2002) spelling.',
        'target_id': DOKIMOKEPHALIDAE_ID,
        'opinion_notes': (
            'Dokimocephalidae is an orthographic variant of Dokimokephalidae (C\u2192K). '
            'Jell & Adrain (2002) used Dokimocephalidae; Adrain (2011) corrected to Dokimokephalidae.'
        ),
    },
    {
        'name': 'Chengkouaspidae',
        'rank': 'Family',
        'parent_id': None,
        'genera_count': 0,
        'is_placeholder': 1,
        'uid': 'scoda:taxon:family:Chengkouaspidae',
        'uid_method': 'name',
        'uid_confidence': 'high',
        'notes': 'Orthographic variant of Chengkouaspididae. Jell & Adrain (2002) spelling.',
        'target_id': CHENGKOUASPIDIDAE_ID,
        'opinion_notes': (
            'Chengkouaspidae is an orthographic variant of Chengkouaspididae (-idae\u2192-ididae). '
            'Jell & Adrain (2002) used Chengkouaspidae; Adrain (2011) corrected to Chengkouaspididae.'
        ),
    },
]


def check_has_spelling_of(conn):
    """Check if CHECK constraint already includes SPELLING_OF."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='taxonomic_opinions'"
    ).fetchone()
    if row is None:
        print("ERROR: taxonomic_opinions table not found")
        sys.exit(1)
    return 'SPELLING_OF' in row[0]


def rebuild_table_with_spelling_of(conn, dry_run):
    """Rebuild taxonomic_opinions table with SPELLING_OF in CHECK constraint."""
    if check_has_spelling_of(conn):
        print("  SKIP: CHECK already includes SPELLING_OF")
        return

    print("  Rebuilding taxonomic_opinions with SPELLING_OF in CHECK...")
    if dry_run:
        print("  [DRY RUN] Would rebuild table")
        return

    conn.executescript("""
        -- 1. Create new table with SPELLING_OF
        CREATE TABLE taxonomic_opinions_new (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            taxon_id            INTEGER NOT NULL REFERENCES taxonomic_ranks(id),
            opinion_type        TEXT NOT NULL
                                CHECK(opinion_type IN ('PLACED_IN', 'VALID_AS', 'SYNONYM_OF', 'SPELLING_OF')),
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
        );

        -- 2. Copy existing data
        INSERT INTO taxonomic_opinions_new
            (id, taxon_id, opinion_type, related_taxon_id, proposed_valid,
             bibliography_id, assertion_status, curation_confidence, is_accepted, notes, created_at)
        SELECT id, taxon_id, opinion_type, related_taxon_id, proposed_valid,
               bibliography_id, assertion_status, curation_confidence, is_accepted, notes, created_at
        FROM taxonomic_opinions;

        -- 3. Drop old table (cascades indexes & triggers)
        DROP TABLE taxonomic_opinions;

        -- 4. Rename
        ALTER TABLE taxonomic_opinions_new RENAME TO taxonomic_opinions;

        -- 5. Recreate indexes
        CREATE INDEX idx_opinions_taxon ON taxonomic_opinions(taxon_id);
        CREATE INDEX idx_opinions_type ON taxonomic_opinions(opinion_type);
        CREATE UNIQUE INDEX idx_unique_accepted_opinion
            ON taxonomic_opinions(taxon_id, opinion_type)
            WHERE is_accepted = 1;

        -- 6. Recreate triggers (PLACED_IN only, unchanged)
        CREATE TRIGGER trg_deactivate_before_insert
        BEFORE INSERT ON taxonomic_opinions
        WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
        BEGIN
            UPDATE taxonomic_opinions
            SET is_accepted = 0
            WHERE taxon_id = NEW.taxon_id
              AND opinion_type = 'PLACED_IN'
              AND is_accepted = 1;
        END;

        CREATE TRIGGER trg_sync_parent_insert
        AFTER INSERT ON taxonomic_opinions
        WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1
        BEGIN
            UPDATE taxonomic_ranks
            SET parent_id = NEW.related_taxon_id
            WHERE id = NEW.taxon_id;
        END;

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
        END;

        CREATE TRIGGER trg_sync_parent_update
        AFTER UPDATE OF is_accepted ON taxonomic_opinions
        WHEN NEW.opinion_type = 'PLACED_IN' AND NEW.is_accepted = 1 AND OLD.is_accepted = 0
        BEGIN
            UPDATE taxonomic_ranks
            SET parent_id = NEW.related_taxon_id
            WHERE id = NEW.taxon_id;
        END;
    """)
    print("  Done: table rebuilt with SPELLING_OF")


def insert_placeholders_and_opinions(conn, dry_run):
    """Insert placeholder entries and SPELLING_OF opinions."""
    for p in PLACEHOLDERS:
        # Check if placeholder already exists
        row = conn.execute(
            "SELECT id FROM taxonomic_ranks WHERE uid = ?", (p['uid'],)
        ).fetchone()

        if row:
            placeholder_id = row[0]
            print(f"  SKIP: {p['name']} placeholder already exists (id={placeholder_id})")
        else:
            print(f"  Inserting placeholder: {p['name']}")
            if dry_run:
                print(f"  [DRY RUN] Would insert {p['name']}")
                continue

            conn.execute(
                """INSERT INTO taxonomic_ranks
                    (name, rank, parent_id, genera_count, is_placeholder,
                     uid, uid_method, uid_confidence, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (p['name'], p['rank'], p['parent_id'], p['genera_count'],
                 p['is_placeholder'], p['uid'], p['uid_method'],
                 p['uid_confidence'], p['notes'])
            )
            placeholder_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            print(f"  Inserted {p['name']} as id={placeholder_id}")

        # Check if opinion already exists
        existing_opinion = conn.execute(
            "SELECT id FROM taxonomic_opinions WHERE taxon_id = ? AND opinion_type = 'SPELLING_OF'",
            (placeholder_id,)
        ).fetchone() if not dry_run else None

        if existing_opinion:
            print(f"  SKIP: SPELLING_OF opinion for {p['name']} already exists (id={existing_opinion[0]})")
        else:
            print(f"  Inserting SPELLING_OF opinion: {p['name']} -> id={p['target_id']}")
            if dry_run:
                print(f"  [DRY RUN] Would insert SPELLING_OF opinion for {p['name']}")
                continue

            conn.execute(
                """INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
                     assertion_status, curation_confidence, is_accepted, notes)
                VALUES (?, 'SPELLING_OF', ?, NULL, 'asserted', 'high', 1, ?)""",
                (placeholder_id, p['target_id'], p['opinion_notes'])
            )
            print(f"  Inserted SPELLING_OF opinion for {p['name']}")


def main():
    parser = argparse.ArgumentParser(description='Add SPELLING_OF opinions for orthographic variants')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without modifying DB')
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        print("=== DRY RUN MODE ===\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        print("Step 1: Rebuild taxonomic_opinions CHECK constraint")
        rebuild_table_with_spelling_of(conn, dry_run)

        print("\nStep 2: Insert placeholders and SPELLING_OF opinions")
        insert_placeholders_and_opinions(conn, dry_run)

        if not dry_run:
            conn.commit()
            print("\nCommitted successfully.")

            # Verify
            count = conn.execute(
                "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type = 'SPELLING_OF'"
            ).fetchone()[0]
            print(f"SPELLING_OF opinions: {count}")

            total = conn.execute("SELECT COUNT(*) FROM taxonomic_opinions").fetchone()[0]
            print(f"Total opinions: {total}")
        else:
            print("\n[DRY RUN] No changes made.")
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
