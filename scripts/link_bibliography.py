"""
Taxon-Bibliography Junction: DB schema migration and data linking.

Creates:
  - taxon_bibliography table (junction linking taxonomic_ranks ↔ bibliography)
  - original_description links (~4,000+): taxon author/year → bibliography author/year
  - fide links (~500): synonym fide_author/fide_year → bibliography
  - taxon_bibliography_list, taxon_bibliography named queries
  - Manifest updates (bibliography_detail, genus_detail, rank_detail)
  - Schema descriptions (8 entries)

Usage:
    python scripts/link_bibliography.py                 # Apply to trilobase.db
    python scripts/link_bibliography.py --dry-run       # Preview only
    python scripts/link_bibliography.py --report        # Report matching stats only
    python scripts/link_bibliography.py path/to/db      # Custom DB path
"""

import sqlite3
import os
import sys
import json
import re
from collections import defaultdict
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')


def table_exists(cursor, name):
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cursor.fetchone()[0] > 0


def query_exists(cursor, name):
    cursor.execute("SELECT COUNT(*) FROM ui_queries WHERE name = ?", (name,))
    return cursor.fetchone()[0] > 0


# ---------------------------------------------------------------------------
# Surname extraction
# ---------------------------------------------------------------------------

def extract_surnames(author):
    """Extract surname(s) from taxonomic_ranks.author field.

    Patterns:
      - "LIEBERMAN" → {'LIEBERMAN'}
      - "RICHTER & RICHTER" → {'RICHTER'}
      - "YANG & LIU in YANG et al." → {'YANG', 'LIU'}
      - "SIVOV in EGOROVA et al." → {'SIVOV'}
      - "M.ROMANENKO in LAZARENKO & NIKIFOROV" → {'ROMANENKO'}
    """
    if not author:
        return set()

    # Take only the part before "in " — that's the describing author(s)
    if ' in ' in author:
        author = author.split(' in ')[0]

    # Remove "et al." suffix
    author = re.sub(r'\s+et\s+al\.?', '', author)

    # Split on & or ,
    parts = re.split(r'\s*[&,]\s*', author)

    surnames = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Remove initials like "M." or "W.T." at the beginning
        part = re.sub(r'^[A-Z]\.(\s*[A-Z]\.)*\s*', '', part)
        # Clean any remaining dots or whitespace
        part = part.strip().rstrip('.')
        if part:
            surnames.add(part.upper())

    return surnames


def extract_bib_surnames(authors):
    """Extract surname(s) from bibliography.authors field.

    Patterns (ALL CAPS + initials):
      - "LIEBERMAN, B.S." → {'LIEBERMAN'}
      - "RICHTER, R. & RICHTER, E." → {'RICHTER'}
      - "ADRAIN, J.M. & CHATTERTON, B.D.E." → {'ADRAIN', 'CHATTERTON'}
      - "CHIEN see QIAN." → skip (cross_ref)
    """
    if not authors:
        return set()

    # Skip cross-references
    if ' see ' in authors:
        return set()

    # Split on "&" first to get individual authors
    parts = re.split(r'\s*&\s*', authors)

    surnames = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Each author is "SURNAME, INITIALS" — take just the surname
        # Also handle "SURNAME" without initials
        if ',' in part:
            surname = part.split(',')[0].strip()
        else:
            # No comma — take the whole thing, but strip trailing dots
            surname = part.strip().rstrip('.')

        # Remove any initials-only entries
        if surname and not re.match(r'^[A-Z]\.?$', surname):
            surnames.add(surname.upper())

    return surnames


# ---------------------------------------------------------------------------
# Index building and matching
# ---------------------------------------------------------------------------

def build_bib_index(cursor):
    """Build a lookup index: (frozenset(surnames), year) → [bib entries].

    Returns:
      index: dict mapping (frozenset, int) → list of (id, year_suffix, authors)
      total: total bibliography entries processed
      skipped: cross_ref entries skipped
    """
    cursor.execute("SELECT id, authors, year, year_suffix, reference_type FROM bibliography")
    rows = cursor.fetchall()

    index = defaultdict(list)
    total = 0
    skipped = 0

    for bib_id, authors, year, year_suffix, ref_type in rows:
        total += 1
        if ref_type == 'cross_ref':
            skipped += 1
            continue

        surnames = extract_bib_surnames(authors)
        if not surnames or year is None:
            continue

        key = (frozenset(surnames), int(year))
        index[key].append({
            'id': bib_id,
            'year_suffix': year_suffix or '',
            'authors': authors,
        })

    return index, total, skipped


def match_taxon_to_bib(author, year, year_suffix, bib_index):
    """Match a taxon's author/year to bibliography entries.

    Returns: list of (bib_id, confidence, method) or empty list
    """
    surnames = extract_surnames(author)
    if not surnames or not year:
        return []

    try:
        year_int = int(year)
    except (ValueError, TypeError):
        return []

    key = (frozenset(surnames), year_int)
    candidates = bib_index.get(key, [])

    if not candidates:
        return []

    if len(candidates) == 1:
        return [(candidates[0]['id'], 'high', 'unique_match')]

    # Multiple candidates — try year_suffix disambiguation
    taxon_suffix = (year_suffix or '').strip()

    if taxon_suffix:
        # Filter by matching suffix
        suffix_matches = [c for c in candidates if c['year_suffix'] == taxon_suffix]
        if len(suffix_matches) == 1:
            return [(suffix_matches[0]['id'], 'high', 'suffix_disambiguated')]
        elif len(suffix_matches) > 1:
            # Multiple with same suffix — shouldn't happen, but mark as low
            return [(suffix_matches[0]['id'], 'low', 'suffix_ambiguous')]

    # No suffix on taxon, or suffix didn't help
    # If there's only one candidate without suffix, match it
    no_suffix = [c for c in candidates if not c['year_suffix']]
    if len(no_suffix) == 1 and not taxon_suffix:
        return [(no_suffix[0]['id'], 'high', 'no_suffix_unique')]

    # Ambiguous — return all as low confidence
    return [(c['id'], 'low', 'ambiguous') for c in candidates]


def match_fide_to_bib(fide_author, fide_year, bib_index):
    """Match synonym fide author/year to bibliography.

    Skip special patterns: "herein", "pers. comm."
    """
    if not fide_author or not fide_year:
        return []

    # Skip special patterns
    fide_lower = fide_author.lower()
    if 'herein' in fide_lower or 'pers.' in fide_lower:
        return []

    # fide_year may contain suffix like "1952c" or "1958a"
    # Also may contain extra text like "WHITTINGTON, 1952c"
    year_match = re.search(r'(\d{4})([a-z])?', fide_year)
    if not year_match:
        return []

    year_int = int(year_match.group(1))
    fide_suffix = year_match.group(2) or ''

    # fide_author may contain extra text like "SHERGOLD & LAURIE"
    # or "WHITTINGTON, 1952c" — strip year/trailing junk
    clean_author = re.sub(r',?\s*\d{4}[a-z]?.*$', '', fide_author).strip()
    surnames = extract_surnames(clean_author)
    if not surnames:
        return []

    key = (frozenset(surnames), year_int)
    candidates = bib_index.get(key, [])

    if not candidates:
        return []

    if len(candidates) == 1:
        return [(candidates[0]['id'], 'high', 'fide_unique')]

    # Try suffix
    if fide_suffix:
        suffix_matches = [c for c in candidates if c['year_suffix'] == fide_suffix]
        if len(suffix_matches) == 1:
            return [(suffix_matches[0]['id'], 'high', 'fide_suffix')]
        elif len(suffix_matches) > 1:
            return [(suffix_matches[0]['id'], 'low', 'fide_suffix_ambiguous')]

    # Ambiguous
    no_suffix = [c for c in candidates if not c['year_suffix']]
    if len(no_suffix) == 1 and not fide_suffix:
        return [(no_suffix[0]['id'], 'high', 'fide_no_suffix_unique')]

    return [(c['id'], 'low', 'fide_ambiguous') for c in candidates]


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

def create_table(conn, dry_run=False):
    """Step 1: Create taxon_bibliography table (idempotent)."""
    cursor = conn.cursor()
    if table_exists(cursor, 'taxon_bibliography'):
        print("  [SKIP] taxon_bibliography table already exists")
        return

    sql = """
        CREATE TABLE taxon_bibliography (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            taxon_id INTEGER NOT NULL,
            bibliography_id INTEGER NOT NULL,
            relationship_type TEXT NOT NULL DEFAULT 'original_description'
                CHECK(relationship_type IN ('original_description', 'fide')),
            synonym_id INTEGER,
            match_confidence TEXT NOT NULL DEFAULT 'high'
                CHECK(match_confidence IN ('high', 'medium', 'low')),
            match_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (taxon_id) REFERENCES taxonomic_ranks(id),
            FOREIGN KEY (bibliography_id) REFERENCES bibliography(id),
            FOREIGN KEY (synonym_id) REFERENCES synonyms(id),
            UNIQUE(taxon_id, bibliography_id, relationship_type, synonym_id)
        )
    """
    print("  [CREATE] taxon_bibliography table")
    if not dry_run:
        cursor.execute(sql)
        cursor.execute("CREATE INDEX idx_tb_taxon ON taxon_bibliography(taxon_id)")
        cursor.execute("CREATE INDEX idx_tb_bib ON taxon_bibliography(bibliography_id)")
        cursor.execute("CREATE INDEX idx_tb_type ON taxon_bibliography(relationship_type)")
        conn.commit()
    print("  [CREATE] indexes (taxon_id, bibliography_id, relationship_type)")


def match_original_descriptions(conn, bib_index, dry_run=False, report_only=False):
    """Step 3: Match taxonomic_ranks author/year → bibliography (original_description)."""
    cursor = conn.cursor()

    # Check if already populated
    if not report_only and table_exists(cursor, 'taxon_bibliography'):
        cursor.execute("SELECT COUNT(*) FROM taxon_bibliography WHERE relationship_type = 'original_description'")
        if cursor.fetchone()[0] > 0:
            existing = cursor.fetchone() if False else None
            cursor.execute("SELECT COUNT(*) FROM taxon_bibliography WHERE relationship_type = 'original_description'")
            count = cursor.fetchone()[0]
            print(f"  [SKIP] {count} original_description links already exist")
            return

    cursor.execute("""
        SELECT id, name, rank, author, year, year_suffix
        FROM taxonomic_ranks
        WHERE author IS NOT NULL AND year IS NOT NULL
    """)
    taxa = cursor.fetchall()

    stats = {'total': len(taxa), 'matched': 0, 'high': 0, 'low': 0, 'unmatched': 0}
    inserts = []

    for taxon_id, name, rank, author, year, year_suffix in taxa:
        matches = match_taxon_to_bib(author, year, year_suffix, bib_index)
        if matches:
            for bib_id, confidence, method in matches:
                if confidence == 'low' and len(matches) > 1:
                    # Skip ambiguous low-confidence matches
                    continue
                inserts.append((taxon_id, bib_id, 'original_description', None, confidence, method))
                if confidence == 'high':
                    stats['high'] += 1
                else:
                    stats['low'] += 1
            stats['matched'] += 1
        else:
            stats['unmatched'] += 1

    print(f"  Total taxa with author+year: {stats['total']}")
    print(f"  Matched: {stats['matched']} ({stats['high']} high, {stats['low']} low)")
    print(f"  Unmatched: {stats['unmatched']}")

    if not dry_run and not report_only:
        for taxon_id, bib_id, rel_type, syn_id, confidence, method in inserts:
            cursor.execute("""
                INSERT OR IGNORE INTO taxon_bibliography
                    (taxon_id, bibliography_id, relationship_type, synonym_id, match_confidence, match_method)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (taxon_id, bib_id, rel_type, syn_id, confidence, method))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM taxon_bibliography WHERE relationship_type = 'original_description'")
        print(f"  Inserted: {cursor.fetchone()[0]} original_description rows")


def match_fide_links(conn, bib_index, dry_run=False, report_only=False):
    """Step 4: Match synonyms fide_author/fide_year → bibliography (fide)."""
    cursor = conn.cursor()

    # Check if already populated
    if not report_only and table_exists(cursor, 'taxon_bibliography'):
        cursor.execute("SELECT COUNT(*) FROM taxon_bibliography WHERE relationship_type = 'fide'")
        if cursor.fetchone()[0] > 0:
            cursor.execute("SELECT COUNT(*) FROM taxon_bibliography WHERE relationship_type = 'fide'")
            count = cursor.fetchone()[0]
            print(f"  [SKIP] {count} fide links already exist")
            return

    cursor.execute("""
        SELECT s.id, s.junior_taxon_id, s.fide_author, s.fide_year
        FROM synonyms s
        WHERE s.fide_author IS NOT NULL AND s.fide_author != ''
    """)
    synonyms = cursor.fetchall()

    stats = {'total': len(synonyms), 'matched': 0, 'skipped': 0, 'high': 0, 'low': 0, 'unmatched': 0}
    inserts = []

    for syn_id, junior_taxon_id, fide_author, fide_year in synonyms:
        # Skip herein/pers. comm.
        fide_lower = (fide_author or '').lower()
        if 'herein' in fide_lower or 'pers.' in fide_lower:
            stats['skipped'] += 1
            continue

        matches = match_fide_to_bib(fide_author, fide_year, bib_index)
        if matches:
            for bib_id, confidence, method in matches:
                if confidence == 'low' and len(matches) > 1:
                    continue
                inserts.append((junior_taxon_id, bib_id, 'fide', syn_id, confidence, method))
                if confidence == 'high':
                    stats['high'] += 1
                else:
                    stats['low'] += 1
            stats['matched'] += 1
        else:
            stats['unmatched'] += 1

    print(f"  Total synonyms with fide: {stats['total']}")
    print(f"  Skipped (herein/pers. comm.): {stats['skipped']}")
    print(f"  Matched: {stats['matched']} ({stats['high']} high, {stats['low']} low)")
    print(f"  Unmatched: {stats['unmatched']}")

    if not dry_run and not report_only:
        for taxon_id, bib_id, rel_type, syn_id, confidence, method in inserts:
            cursor.execute("""
                INSERT OR IGNORE INTO taxon_bibliography
                    (taxon_id, bibliography_id, relationship_type, synonym_id, match_confidence, match_method)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (taxon_id, bib_id, rel_type, syn_id, confidence, method))
        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM taxon_bibliography WHERE relationship_type = 'fide'")
        print(f"  Inserted: {cursor.fetchone()[0]} fide rows")


def add_named_queries(conn, dry_run=False):
    """Step 5: Add named queries to ui_queries."""
    cursor = conn.cursor()

    queries = [
        {
            'name': 'taxon_bibliography_list',
            'description': 'Taxa linked to a specific bibliography entry',
            'sql': (
                "SELECT tr.id, tr.name, tr.rank, tr.author, tr.year, tr.is_valid, "
                "tb.relationship_type, tb.match_confidence "
                "FROM taxon_bibliography tb "
                "JOIN taxonomic_ranks tr ON tb.taxon_id = tr.id "
                "WHERE tb.bibliography_id = :bibliography_id "
                "ORDER BY tb.relationship_type, tr.rank, tr.name"
            ),
            'params': '{"bibliography_id": "integer"}',
        },
        {
            'name': 'taxon_bibliography',
            'description': 'Bibliography entries linked to a specific taxon',
            'sql': (
                "SELECT b.id, b.authors, b.year, b.year_suffix, b.title, b.reference_type, "
                "tb.relationship_type, tb.match_confidence "
                "FROM taxon_bibliography tb "
                "JOIN bibliography b ON tb.bibliography_id = b.id "
                "WHERE tb.taxon_id = :taxon_id "
                "ORDER BY tb.relationship_type, b.year, b.authors"
            ),
            'params': '{"taxon_id": "integer"}',
        },
    ]

    for q in queries:
        if query_exists(cursor, q['name']):
            print(f"  [SKIP] {q['name']} query already exists")
            continue
        print(f"  [INSERT] {q['name']} named query")
        if not dry_run:
            cursor.execute(
                "INSERT INTO ui_queries (name, description, sql, params_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (q['name'], q['description'], q['sql'], q['params'], datetime.now().isoformat())
            )

    if not dry_run:
        conn.commit()


def update_manifest(conn, dry_run=False):
    """Step 5b: Update manifest — bibliography_detail, genus_detail, rank_detail."""
    cursor = conn.cursor()
    cursor.execute("SELECT manifest_json FROM ui_manifest WHERE name = 'default'")
    row = cursor.fetchone()
    if not row:
        print("  [SKIP] No default manifest found")
        return

    manifest = json.loads(row[0])
    views = manifest.get('views', {})
    changed = False

    # --- bibliography_detail: replace genera sub_query with taxon_bibliography_list ---
    bib_detail = views.get('bibliography_detail')
    if bib_detail:
        sub_queries = bib_detail.get('sub_queries', {})
        if 'genera' in sub_queries and sub_queries['genera'].get('query') == 'bibliography_genera':
            sub_queries['taxa'] = {
                "query": "taxon_bibliography_list",
                "params": {"bibliography_id": "id"}
            }
            del sub_queries['genera']
            bib_detail['sub_queries'] = sub_queries

            # Update sections: replace genera linked_table
            for section in bib_detail.get('sections', []):
                if section.get('data_key') == 'genera' and section.get('type') == 'linked_table':
                    section['title'] = 'Related Taxa ({count})'
                    section['data_key'] = 'taxa'
                    section['columns'] = [
                        {"key": "name", "label": "Name", "italic": True},
                        {"key": "rank", "label": "Rank"},
                        {"key": "author", "label": "Author"},
                        {"key": "year", "label": "Year"},
                        {"key": "relationship_type", "label": "Relationship"},
                        {"key": "is_valid", "label": "Valid", "format": "boolean"},
                    ]

            changed = True
            print("  [UPDATE] bibliography_detail: genera → taxa (taxon_bibliography_list)")

    # --- genus_detail: add bibliography sub_query + section ---
    genus_detail = views.get('genus_detail')
    if genus_detail:
        # Add sub_queries if not present
        if 'sub_queries' not in genus_detail:
            genus_detail['sub_queries'] = {}
        sub_queries = genus_detail['sub_queries']

        # Add source_query/source_param if not present
        if 'source_query' not in genus_detail:
            genus_detail['source_query'] = 'genus_detail'
            genus_detail['source_param'] = 'genus_id'
            changed = True

        # Ensure existing sub_queries are present (from conftest pattern)
        expected_subs = {
            'hierarchy': {"query": "genus_hierarchy", "params": {"genus_id": "id"}},
            'synonyms': {"query": "genus_synonyms", "params": {"genus_id": "id"}},
            'formations': {"query": "genus_formations", "params": {"genus_id": "id"}},
            'locations': {"query": "genus_locations", "params": {"genus_id": "id"}},
            'temporal_ics_mapping': {"query": "genus_ics_mapping", "params": {"temporal_code": "result.temporal_code"}},
        }
        for key, val in expected_subs.items():
            if key not in sub_queries:
                sub_queries[key] = val
                changed = True

        if 'bibliography' not in sub_queries:
            sub_queries['bibliography'] = {
                "query": "taxon_bibliography",
                "params": {"taxon_id": "id"}
            }

            # Add bibliography section before Original Entry
            sections = genus_detail.get('sections', [])
            bib_section = {
                "title": "Bibliography ({count})",
                "type": "linked_table",
                "data_key": "bibliography",
                "condition": "bibliography",
                "columns": [
                    {"key": "authors", "label": "Authors"},
                    {"key": "year", "label": "Year"},
                    {"key": "title", "label": "Title"},
                    {"key": "relationship_type", "label": "Relationship"},
                ],
                "on_row_click": {"detail_view": "bibliography_detail", "id_key": "id"}
            }

            # Insert before "Original Entry" or "My Notes"
            insert_idx = len(sections)
            for i, s in enumerate(sections):
                if s.get('type') in ('raw_text', 'annotations') and s.get('data_key') in ('raw_entry', 'notes', None):
                    if s.get('title', '').startswith('Notes') or s.get('title', '').startswith('Original'):
                        insert_idx = i
                        break
                if s.get('type') == 'annotations':
                    insert_idx = i
                    break
            sections.insert(insert_idx, bib_section)

            changed = True
            print("  [UPDATE] genus_detail: added bibliography sub_query + section")

        # Update source to composite
        if genus_detail.get('source', '').startswith('/api/genus/'):
            genus_detail['source'] = '/api/composite/genus_detail?id={id}'
            changed = True
            print("  [UPDATE] genus_detail: source → /api/composite/genus_detail?id={id}")

    # --- rank_detail: add bibliography sub_query + section ---
    rank_detail = views.get('rank_detail')
    if rank_detail:
        sub_queries = rank_detail.get('sub_queries', {})
        if 'bibliography' not in sub_queries:
            sub_queries['bibliography'] = {
                "query": "taxon_bibliography",
                "params": {"taxon_id": "id"}
            }
            if 'sub_queries' not in rank_detail:
                rank_detail['sub_queries'] = sub_queries

            # Add children/children_counts sub_queries if missing
            if 'children_counts' not in sub_queries:
                sub_queries['children_counts'] = {"query": "rank_children_counts", "params": {"rank_id": "id"}}
            if 'children' not in sub_queries:
                sub_queries['children'] = {"query": "rank_children", "params": {"rank_id": "id"}}

            # Add bibliography section before Opinions or Notes or Annotations
            sections = rank_detail.get('sections', [])
            bib_section = {
                "title": "Bibliography ({count})",
                "type": "linked_table",
                "data_key": "bibliography",
                "condition": "bibliography",
                "columns": [
                    {"key": "authors", "label": "Authors"},
                    {"key": "year", "label": "Year"},
                    {"key": "title", "label": "Title"},
                    {"key": "relationship_type", "label": "Relationship"},
                ],
                "on_row_click": {"detail_view": "bibliography_detail", "id_key": "id"}
            }

            insert_idx = len(sections)
            for i, s in enumerate(sections):
                if s.get('data_key') in ('opinions', 'notes') or s.get('type') == 'annotations':
                    insert_idx = i
                    break
            sections.insert(insert_idx, bib_section)

            changed = True
            print("  [UPDATE] rank_detail: added bibliography sub_query + section")

    if changed:
        if not dry_run:
            cursor.execute(
                "UPDATE ui_manifest SET manifest_json = ? WHERE name = 'default'",
                (json.dumps(manifest),)
            )
            conn.commit()
    else:
        print("  [SKIP] Manifest already up to date")


def add_schema_descriptions(conn, dry_run=False):
    """Step 6: Add schema descriptions for taxon_bibliography."""
    cursor = conn.cursor()

    descriptions = [
        ('taxon_bibliography', None, 'Junction table linking taxa to bibliography entries'),
        ('taxon_bibliography', 'taxon_id', 'Reference to taxonomic_ranks.id'),
        ('taxon_bibliography', 'bibliography_id', 'Reference to bibliography.id'),
        ('taxon_bibliography', 'relationship_type', 'original_description (taxon author=bib) or fide (synonym fide=bib)'),
        ('taxon_bibliography', 'synonym_id', 'Reference to synonyms.id (for fide relationships)'),
        ('taxon_bibliography', 'match_confidence', 'Confidence of the automated match: high, medium, low'),
        ('taxon_bibliography', 'match_method', 'Algorithm used for matching (unique_match, suffix_disambiguated, etc.)'),
        ('taxon_bibliography', 'notes', 'Additional notes about the link'),
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = '--dry-run' in sys.argv
    report_only = '--report' in sys.argv
    args = [a for a in sys.argv[1:] if a not in ('--dry-run', '--report')]
    db_path = args[0] if args else DB_PATH

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    mode = " (DRY RUN)" if dry_run else " (REPORT ONLY)" if report_only else ""
    print(f"=== Taxon-Bibliography Junction Migration{mode} ===")
    print(f"Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    if not report_only:
        print("[1/6] Create taxon_bibliography table")
        create_table(conn, dry_run)
    else:
        print("[1/6] Create table — skipped (report only)")

    print("\n[2/6] Build bibliography index")
    cursor = conn.cursor()
    bib_index, bib_total, bib_skipped = build_bib_index(cursor)
    print(f"  Bibliography entries: {bib_total} (skipped {bib_skipped} cross_ref)")
    print(f"  Index keys: {len(bib_index)}")

    print("\n[3/6] Match taxonomic_ranks → bibliography (original_description)")
    match_original_descriptions(conn, bib_index, dry_run, report_only)

    print("\n[4/6] Match synonyms fide → bibliography (fide)")
    match_fide_links(conn, bib_index, dry_run, report_only)

    if not report_only:
        print("\n[5/6] Add named queries + update manifest")
        add_named_queries(conn, dry_run)
        update_manifest(conn, dry_run)

        print("\n[6/6] Add schema descriptions")
        add_schema_descriptions(conn, dry_run)
    else:
        print("\n[5/6] Named queries — skipped (report only)")
        print("[6/6] Schema descriptions — skipped (report only)")

    # Verification
    if not dry_run and not report_only:
        print("\n=== Verification ===")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM taxon_bibliography")
        print(f"  Total links: {cursor.fetchone()[0]}")
        cursor.execute("SELECT relationship_type, COUNT(*) FROM taxon_bibliography GROUP BY relationship_type")
        for row in cursor.fetchall():
            print(f"    {row[0]}: {row[1]}")
        cursor.execute("SELECT match_confidence, COUNT(*) FROM taxon_bibliography GROUP BY match_confidence")
        for row in cursor.fetchall():
            print(f"    confidence={row[0]}: {row[1]}")
        cursor.execute("SELECT COUNT(*) FROM ui_queries WHERE name IN ('taxon_bibliography_list', 'taxon_bibliography')")
        print(f"  Named queries: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM schema_descriptions WHERE table_name = 'taxon_bibliography'")
        print(f"  Schema descriptions: {cursor.fetchone()[0]}")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
