#!/usr/bin/env python3
"""
T-4: Migrate synonyms table → SYNONYM_OF opinions in taxonomic_opinions.

Steps:
  1. Add synonym_type column to taxonomic_opinions
  2. Insert 1,055 SYNONYM_OF opinions from synonyms table
  3. Build synonym_id→opinion_id mapping for taxon_bibliography
  4. Rebuild taxon_bibliography: synonym_id → opinion_id
  5. Create backward-compatible synonyms VIEW
  6. Drop synonyms TABLE
  7. Verify all counts

Usage:
    python scripts/migrate_synonyms_to_opinions.py             # Run migration
    python scripts/migrate_synonyms_to_opinions.py --dry-run   # Preview only
    python scripts/migrate_synonyms_to_opinions.py --verify    # Verify post-migration
"""

import argparse
import sqlite3
import sys

DB_PATH = 'db/trilobase.db'

# Priority for is_accepted when a taxon has multiple synonym records.
# Higher priority = gets is_accepted=1.
SYNONYM_PRIORITY = {
    'j.s.s.': 5,
    'j.o.s.': 4,
    'suppressed': 3,
    'replacement': 2,
    'preocc.': 1,
}


def add_synonym_type_column(conn, dry_run=False):
    """Step 1: Add synonym_type column to taxonomic_opinions."""
    # Check if column already exists
    cursor = conn.execute("PRAGMA table_info(taxonomic_opinions)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'synonym_type' in columns:
        print("  SKIP: synonym_type column already exists")
        return

    print("  Adding synonym_type column...")
    if dry_run:
        print("  [DRY RUN] Would add synonym_type column")
        return

    # SQLite doesn't support ADD COLUMN with CHECK, so we rebuild the table
    conn.executescript("""
        -- 1. Create new table with synonym_type
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
            synonym_type        TEXT
                                CHECK(synonym_type IS NULL OR synonym_type IN
                                    ('j.s.s.', 'j.o.s.', 'preocc.', 'replacement', 'suppressed')),
            notes               TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Copy existing data
        INSERT INTO taxonomic_opinions_new
            (id, taxon_id, opinion_type, related_taxon_id, proposed_valid,
             bibliography_id, assertion_status, curation_confidence, is_accepted,
             synonym_type, notes, created_at)
        SELECT id, taxon_id, opinion_type, related_taxon_id, proposed_valid,
               bibliography_id, assertion_status, curation_confidence, is_accepted,
               NULL, notes, created_at
        FROM taxonomic_opinions;

        -- 3. Drop old table
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
    print("  Done: table rebuilt with synonym_type column")


def determine_accepted(synonyms_for_taxon):
    """Given a list of synonym records for one taxon, return which gets is_accepted=1.

    Returns the synonym id that should be accepted (highest priority).
    """
    if len(synonyms_for_taxon) == 1:
        return synonyms_for_taxon[0]['id']

    # Sort by priority descending
    sorted_syns = sorted(
        synonyms_for_taxon,
        key=lambda s: SYNONYM_PRIORITY.get(s['synonym_type'], 0),
        reverse=True
    )
    return sorted_syns[0]['id']


def insert_synonym_opinions(conn, dry_run=False):
    """Step 2: Insert 1,055 SYNONYM_OF opinions from synonyms table."""
    cursor = conn.cursor()

    # Check if already migrated
    existing = cursor.execute(
        "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type = 'SYNONYM_OF'"
    ).fetchone()[0]
    if existing > 0:
        print(f"  SKIP: {existing} SYNONYM_OF opinions already exist")
        return {}

    # Load all synonyms
    rows = cursor.execute("""
        SELECT id, junior_taxon_id, senior_taxon_id, synonym_type,
               fide_author, fide_year, notes
        FROM synonyms
        ORDER BY id
    """).fetchall()

    print(f"  Found {len(rows)} synonym records to migrate")

    # Group by junior_taxon_id to determine is_accepted
    from collections import defaultdict
    by_taxon = defaultdict(list)
    for row in rows:
        by_taxon[row[1]].append({
            'id': row[0],
            'junior_taxon_id': row[1],
            'senior_taxon_id': row[2],
            'synonym_type': row[3],
            'fide_author': row[4],
            'fide_year': row[5],
            'notes': row[6],
        })

    multi_count = sum(1 for v in by_taxon.values() if len(v) > 1)
    print(f"  Multi-synonym taxa: {multi_count}")

    # Match fide to bibliography_id via existing taxon_bibliography fide links
    fide_map = {}
    fide_rows = cursor.execute("""
        SELECT synonym_id, bibliography_id
        FROM taxon_bibliography
        WHERE relationship_type = 'fide' AND synonym_id IS NOT NULL
    """).fetchall()
    for syn_id, bib_id in fide_rows:
        fide_map[syn_id] = bib_id
    print(f"  fide→bibliography matches: {len(fide_map)}")

    # Build mapping: old synonym_id → new opinion_id
    syn_to_opinion = {}
    inserted = 0

    if dry_run:
        print(f"  [DRY RUN] Would insert {len(rows)} SYNONYM_OF opinions")
        return {}

    for taxon_id, syns in by_taxon.items():
        accepted_syn_id = determine_accepted(syns)

        for syn in syns:
            is_accepted = 1 if syn['id'] == accepted_syn_id else 0
            bib_id = fide_map.get(syn['id'])

            # Build notes: preserve fide text if no bibliography match
            notes = syn['notes'] or ''
            if syn['fide_author'] and not bib_id:
                fide_text = f"fide {syn['fide_author']}"
                if syn['fide_year']:
                    fide_text += f", {syn['fide_year']}"
                if notes:
                    notes = f"{fide_text}; {notes}"
                else:
                    notes = fide_text

            cursor.execute("""
                INSERT INTO taxonomic_opinions
                    (taxon_id, opinion_type, related_taxon_id, bibliography_id,
                     assertion_status, curation_confidence, is_accepted,
                     synonym_type, notes)
                VALUES (?, 'SYNONYM_OF', ?, ?, 'asserted', 'high', ?, ?, ?)
            """, (
                syn['junior_taxon_id'],
                syn['senior_taxon_id'],
                bib_id,
                is_accepted,
                syn['synonym_type'],
                notes if notes else None,
            ))

            new_opinion_id = cursor.lastrowid
            syn_to_opinion[syn['id']] = new_opinion_id
            inserted += 1

    conn.commit()
    print(f"  Inserted {inserted} SYNONYM_OF opinions")
    return syn_to_opinion


def rebuild_taxon_bibliography(conn, syn_to_opinion, dry_run=False):
    """Step 3: Rebuild taxon_bibliography: synonym_id → opinion_id."""
    cursor = conn.cursor()

    # Check if already rebuilt
    cols = {row[1] for row in cursor.execute("PRAGMA table_info(taxon_bibliography)").fetchall()}
    if 'opinion_id' in cols and 'synonym_id' not in cols:
        print("  SKIP: taxon_bibliography already has opinion_id (no synonym_id)")
        return

    if dry_run:
        fide_count = cursor.execute(
            "SELECT COUNT(*) FROM taxon_bibliography WHERE synonym_id IS NOT NULL"
        ).fetchone()[0]
        print(f"  [DRY RUN] Would rebuild taxon_bibliography ({fide_count} fide rows to remap)")
        return

    # If syn_to_opinion is empty, build it from the DB
    if not syn_to_opinion:
        # Build mapping from existing data
        syn_rows = cursor.execute("""
            SELECT s.id as syn_id, o.id as opinion_id
            FROM synonyms s
            JOIN taxonomic_opinions o
              ON o.taxon_id = s.junior_taxon_id
              AND o.opinion_type = 'SYNONYM_OF'
              AND o.synonym_type = s.synonym_type
        """).fetchall()
        syn_to_opinion = {r[0]: r[1] for r in syn_rows}

    # Get all current data
    rows = cursor.execute("""
        SELECT id, taxon_id, bibliography_id, relationship_type,
               synonym_id, match_confidence, match_method, notes, created_at
        FROM taxon_bibliography
    """).fetchall()

    print(f"  Rebuilding taxon_bibliography ({len(rows)} rows)...")

    conn.executescript("""
        CREATE TABLE taxon_bibliography_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            taxon_id INTEGER NOT NULL,
            bibliography_id INTEGER NOT NULL,
            relationship_type TEXT NOT NULL DEFAULT 'original_description'
                CHECK(relationship_type IN ('original_description', 'fide')),
            opinion_id INTEGER,
            match_confidence TEXT NOT NULL DEFAULT 'high'
                CHECK(match_confidence IN ('high', 'medium', 'low')),
            match_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (taxon_id) REFERENCES taxonomic_ranks(id),
            FOREIGN KEY (bibliography_id) REFERENCES bibliography(id),
            FOREIGN KEY (opinion_id) REFERENCES taxonomic_opinions(id),
            UNIQUE(taxon_id, bibliography_id, relationship_type, opinion_id)
        );
    """)

    for row_id, taxon_id, bib_id, rel_type, syn_id, confidence, method, notes, created in rows:
        opinion_id = syn_to_opinion.get(syn_id) if syn_id else None
        cursor.execute("""
            INSERT INTO taxon_bibliography_new
                (id, taxon_id, bibliography_id, relationship_type, opinion_id,
                 match_confidence, match_method, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (row_id, taxon_id, bib_id, rel_type, opinion_id, confidence, method, notes, created))

    conn.executescript("""
        DROP TABLE taxon_bibliography;
        ALTER TABLE taxon_bibliography_new RENAME TO taxon_bibliography;
        CREATE INDEX idx_tb_taxon ON taxon_bibliography(taxon_id);
        CREATE INDEX idx_tb_bib ON taxon_bibliography(bibliography_id);
        CREATE INDEX idx_tb_type ON taxon_bibliography(relationship_type);
    """)

    remapped = sum(1 for r in rows if r[4] and syn_to_opinion.get(r[4]))
    print(f"  Done: {remapped} fide rows remapped synonym_id→opinion_id")


def create_synonyms_view(conn, dry_run=False):
    """Step 4: Drop synonyms table and create backward-compatible VIEW."""
    cursor = conn.cursor()

    # Check current state
    row = cursor.execute(
        "SELECT type FROM sqlite_master WHERE name='synonyms'"
    ).fetchone()

    if row and row[0] == 'view':
        print("  SKIP: synonyms is already a VIEW")
        return

    if dry_run:
        print("  [DRY RUN] Would drop synonyms TABLE and create VIEW")
        return

    if row and row[0] == 'table':
        conn.execute("DROP TABLE synonyms")
        print("  Dropped synonyms TABLE")

    conn.execute("""
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
        WHERE o.opinion_type = 'SYNONYM_OF'
    """)
    conn.commit()
    print("  Created synonyms VIEW (backward-compatible)")


def update_schema_descriptions(conn, dry_run=False):
    """Step 5: Update schema_descriptions for new/changed entities."""
    cursor = conn.cursor()

    updates = [
        # New column
        ('taxonomic_opinions', 'synonym_type',
         'Synonym sub-type: j.s.s., j.o.s., preocc., replacement, suppressed (NULL for non-SYNONYM_OF)'),
        # Rename synonym_id → opinion_id
        ('taxon_bibliography', 'opinion_id',
         'Reference to taxonomic_opinions.id (for fide relationships)'),
        # synonyms is now a VIEW
        ('synonyms', None,
         'Backward-compatible VIEW over taxonomic_opinions WHERE opinion_type = SYNONYM_OF'),
    ]

    if dry_run:
        print(f"  [DRY RUN] Would update {len(updates)} schema descriptions")
        return

    # Remove old synonym_id description
    cursor.execute(
        "DELETE FROM schema_descriptions WHERE table_name = 'taxon_bibliography' AND column_name = 'synonym_id'"
    )

    for table_name, column_name, desc in updates:
        cursor.execute(
            "INSERT OR REPLACE INTO schema_descriptions (table_name, column_name, description) VALUES (?, ?, ?)",
            (table_name, column_name, desc)
        )

    conn.commit()
    print(f"  Updated {len(updates)} schema descriptions")


def verify(conn):
    """Verify post-migration state."""
    cursor = conn.cursor()
    errors = []

    # 1. Total SYNONYM_OF count
    count = cursor.execute(
        "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type = 'SYNONYM_OF'"
    ).fetchone()[0]
    print(f"  SYNONYM_OF opinions: {count}")
    if count != 1055:
        errors.append(f"Expected 1055 SYNONYM_OF, got {count}")

    # 2. Total opinions
    total = cursor.execute("SELECT COUNT(*) FROM taxonomic_opinions").fetchone()[0]
    print(f"  Total opinions: {total}")
    if total != 1139:
        errors.append(f"Expected 1139 total opinions, got {total}")

    # 3. Distribution
    print("  Distribution:")
    rows = cursor.execute("""
        SELECT synonym_type, COUNT(*) FROM taxonomic_opinions
        WHERE opinion_type = 'SYNONYM_OF' GROUP BY synonym_type ORDER BY COUNT(*) DESC
    """).fetchall()
    expected = {'j.s.s.': 721, 'preocc.': 146, 'replacement': 125, 'j.o.s.': 54, 'suppressed': 9}
    for syn_type, cnt in rows:
        print(f"    {syn_type}: {cnt}")
        if expected.get(syn_type) != cnt:
            errors.append(f"synonym_type {syn_type}: expected {expected.get(syn_type)}, got {cnt}")

    # 4. Accepted count
    accepted = cursor.execute("""
        SELECT COUNT(*) FROM taxonomic_opinions
        WHERE opinion_type = 'SYNONYM_OF' AND is_accepted = 1
    """).fetchone()[0]
    print(f"  Accepted SYNONYM_OF: {accepted}")
    if accepted != 1012:
        errors.append(f"Expected 1012 accepted, got {accepted}")

    # 5. FK integrity — opinion_id in taxon_bibliography
    fk_count = cursor.execute(
        "SELECT COUNT(*) FROM taxon_bibliography WHERE opinion_id IS NOT NULL"
    ).fetchone()[0]
    print(f"  taxon_bibliography with opinion_id: {fk_count}")
    if fk_count != 433:
        errors.append(f"Expected 433 opinion_id refs, got {fk_count}")

    # 6. Backward-compat view
    view_count = cursor.execute("SELECT COUNT(*) FROM synonyms").fetchone()[0]
    print(f"  synonyms VIEW count: {view_count}")
    if view_count != 1055:
        errors.append(f"Expected 1055 in synonyms VIEW, got {view_count}")

    # 7. Opinion type breakdown
    print("  Opinion type breakdown:")
    for otype, cnt in cursor.execute(
        "SELECT opinion_type, COUNT(*) FROM taxonomic_opinions GROUP BY opinion_type ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"    {otype}: {cnt}")

    # 8. synonyms should be a VIEW not TABLE
    obj_type = cursor.execute(
        "SELECT type FROM sqlite_master WHERE name = 'synonyms'"
    ).fetchone()
    if obj_type and obj_type[0] == 'view':
        print("  synonyms: VIEW (correct)")
    else:
        errors.append(f"synonyms should be a VIEW, got {obj_type}")

    # 9. taxon_bibliography should have opinion_id, not synonym_id
    tb_cols = {row[1] for row in cursor.execute("PRAGMA table_info(taxon_bibliography)").fetchall()}
    if 'opinion_id' in tb_cols:
        print("  taxon_bibliography.opinion_id: present (correct)")
    else:
        errors.append("taxon_bibliography missing opinion_id column")
    if 'synonym_id' not in tb_cols:
        print("  taxon_bibliography.synonym_id: absent (correct)")
    else:
        errors.append("taxon_bibliography still has synonym_id column")

    # 10. Existing opinions untouched
    placed_in = cursor.execute(
        "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type = 'PLACED_IN'"
    ).fetchone()[0]
    spelling_of = cursor.execute(
        "SELECT COUNT(*) FROM taxonomic_opinions WHERE opinion_type = 'SPELLING_OF'"
    ).fetchone()[0]
    print(f"  PLACED_IN: {placed_in}, SPELLING_OF: {spelling_of}")
    if placed_in != 82:
        errors.append(f"Expected 82 PLACED_IN, got {placed_in}")
    if spelling_of != 2:
        errors.append(f"Expected 2 SPELLING_OF, got {spelling_of}")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
        return False
    else:
        print("\n  All checks passed!")
        return True


def main():
    parser = argparse.ArgumentParser(description='Migrate synonyms → SYNONYM_OF opinions')
    parser.add_argument('--dry-run', action='store_true', help='Preview without modifying DB')
    parser.add_argument('--verify', action='store_true', help='Verify post-migration state only')
    parser.add_argument('db', nargs='?', default=DB_PATH, help=f'Database path (default: {DB_PATH})')
    args = parser.parse_args()

    if args.verify:
        print("=== Verify Post-Migration State ===\n")
        conn = sqlite3.connect(args.db)
        ok = verify(conn)
        conn.close()
        sys.exit(0 if ok else 1)

    dry_run = args.dry_run
    if dry_run:
        print("=== DRY RUN: Synonym → Opinion Migration ===\n")
    else:
        print("=== Synonym → Opinion Migration ===\n")

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        print("[1/5] Add synonym_type column to taxonomic_opinions")
        add_synonym_type_column(conn, dry_run)

        print("\n[2/5] Insert SYNONYM_OF opinions from synonyms table")
        syn_to_opinion = insert_synonym_opinions(conn, dry_run)

        print("\n[3/5] Rebuild taxon_bibliography: synonym_id → opinion_id")
        rebuild_taxon_bibliography(conn, syn_to_opinion, dry_run)

        print("\n[4/5] Create synonyms VIEW and drop TABLE")
        create_synonyms_view(conn, dry_run)

        print("\n[5/5] Update schema descriptions")
        update_schema_descriptions(conn, dry_run)

        if not dry_run:
            conn.commit()
            print("\n=== Migration Complete ===\n")
            print("Running verification...")
            verify(conn)
        else:
            print("\n[DRY RUN] No changes made.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
