#!/usr/bin/env python3
"""
UID Population Phase C — Bibliography + Formations

Adds uid columns and generates UIDs for:
  trilobase.db:  bibliography  (2,130 records)
  paleocore.db:  formations    (2,004 records)

Strategy:
  1. fp_v1 fingerprint for all records (100% immediate coverage)
  2. --crossref: CrossRef API DOI lookup → upgrade fp_v1 → doi (bibliography)
  3. --macrostrat: Macrostrat API lexicon ID → upgrade fp_v1 → lexicon (formations)

Usage:
  python scripts/populate_uids_phase_c.py                              # fp_v1 only
  python scripts/populate_uids_phase_c.py --report                     # statistics
  python scripts/populate_uids_phase_c.py --crossref --email user@ex   # DOI lookup
  python scripts/populate_uids_phase_c.py --macrostrat                 # Macrostrat lookup
  python scripts/populate_uids_phase_c.py --dry-run                    # preview
"""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata


TRILOBASE_DB = os.path.join(os.path.dirname(__file__), '..', 'db', 'trilobase.db')
PALEOCORE_DB = os.path.join(os.path.dirname(__file__), '..', 'db', 'paleocore.db')

UID_COLUMNS = [
    ('uid', 'TEXT'),
    ('uid_method', 'TEXT'),
    ('uid_confidence', 'TEXT'),
    ('same_as_uid', 'TEXT'),
]


# ── Utilities (shared with Phase A) ──────────────────────────────────────

def normalize_for_fp(text):
    """Normalize text for fingerprint hashing (NFKC, lowercase, collapse spaces)."""
    if not text:
        return ''
    text = unicodedata.normalize('NFKC', text)
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def fp_sha256(canonical_string):
    """Generate SHA-256 fingerprint from a canonical string."""
    return hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()


# ── Column Management ─────────────────────────────────────────────────────

def has_uid_columns(conn, table):
    """Check if table already has uid columns."""
    cols = [row[1] for row in conn.execute(
        f"PRAGMA table_info({table})").fetchall()]
    return 'uid' in cols


def add_uid_columns(conn, table):
    """Add uid columns to a table if they don't exist."""
    if has_uid_columns(conn, table):
        return False
    for col_name, col_type in UID_COLUMNS:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
    conn.commit()
    return True


def create_uid_index(conn, table):
    """Create unique index on uid column."""
    idx_name = f"idx_{table}_uid"
    conn.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS {idx_name} ON {table}(uid)")
    conn.commit()


# ── Bibliography Fingerprint ─────────────────────────────────────────────

def normalize_title(title):
    """Normalize a bibliography title for fingerprinting.

    - NFKC, lowercase
    - Remove punctuation: .,:;()'"\u00ad
    - Hyphen/slash → space
    - & → and
    - Collapse whitespace
    """
    if not title:
        return ''
    text = unicodedata.normalize('NFKC', title)
    text = text.lower()
    # Remove soft hyphens
    text = text.replace('\u00ad', '')
    # & → and
    text = text.replace('&', 'and')
    # Hyphen/slash → space
    text = re.sub(r'[-/]', ' ', text)
    # Remove punctuation
    text = re.sub(r'''[.,:;()'"\[\]{}]''', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_first_author_family(authors):
    """Extract first author family name from authors string.

    Pattern: FAMILY, INITIALS & ... or FAMILY, INITIALS, ...
    Returns lowercase family name.
    """
    if not authors:
        return ''
    # Split by '&' first, take first part
    first = authors.split('&')[0]
    # Split by ',' and take first token (family name)
    family = first.split(',')[0].strip().lower()
    return family


def extract_first_page(pages):
    """Extract first page number from pages string.

    '132-138' → '132'
    '1009-1043, pls 1-4' → '1009'
    '104p' → '104'
    """
    if not pages:
        return ''
    # Match first numeric sequence
    m = re.match(r'(\d+)', pages.strip())
    return m.group(1) if m else ''


def generate_bibliography_uids(conn, dry_run=False):
    """Generate fp_v1 UIDs for bibliography table.

    Canonical: fa=<first_author_family>|y=<year[suffix]>|t=<normalized_title>|c=<journal_or_book>|v=<volume>|p=<first_page>
    UID: scoda:bib:fp_v1:sha256:<hash>
    cross_ref entries get low confidence.
    """
    rows = conn.execute(
        "SELECT id, authors, year, year_suffix, title, journal, volume, pages, "
        "book_title, reference_type FROM bibliography ORDER BY id"
    ).fetchall()

    # Build canonical strings and detect collisions
    uid_map = {}  # canonical → list of (id, ...)
    records = []

    for row_id, authors, year, year_suffix, title, journal, volume, pages, book_title, ref_type in rows:
        fa = extract_first_author_family(authors)
        y = str(year) if year else ''
        if year_suffix:
            y += year_suffix
        t = normalize_title(title)
        c = normalize_title(journal or book_title or '')
        v = str(volume).strip() if volume else ''
        p = extract_first_page(pages)

        # Build canonical string
        parts = [f"fa={fa}", f"y={y}", f"t={t}"]
        if c:
            parts.append(f"c={c}")
        if v:
            parts.append(f"v={v}")
        if p:
            parts.append(f"p={p}")
        canonical = '|'.join(parts)

        # Determine confidence
        if ref_type == 'cross_ref':
            confidence = 'low'
        else:
            confidence = 'medium'

        records.append((row_id, canonical, confidence, ref_type))

        uid_map.setdefault(canonical, []).append(row_id)

    # Generate UIDs with collision handling
    results = []
    collision_counter = {}  # canonical → next suffix number

    for row_id, canonical, confidence, ref_type in records:
        hash_val = fp_sha256(canonical)
        base_uid = f"scoda:bib:fp_v1:sha256:{hash_val}"

        entries = uid_map[canonical]
        if len(entries) > 1:
            # Collision: assign suffix based on order
            if canonical not in collision_counter:
                collision_counter[canonical] = 0
            collision_counter[canonical] += 1
            idx = collision_counter[canonical]
            if idx == 1:
                uid = base_uid
            else:
                uid = f"{base_uid}-c{idx}"
        else:
            uid = base_uid

        results.append((row_id, uid, 'fp_v1', confidence, None))

    if not dry_run:
        for row_id, uid, method, confidence, same_as in results:
            conn.execute(
                "UPDATE bibliography SET uid=?, uid_method=?, "
                "uid_confidence=?, same_as_uid=? WHERE id=?",
                (uid, method, confidence, same_as, row_id))
        conn.commit()

    return results


# ── Formations Fingerprint ───────────────────────────────────────────────

def generate_formations_uids(conn, dry_run=False):
    """Generate fp_v1 UIDs for formations table.

    Canonical: n=<normalized_name>|r=<formation_type or 'unknown'>
    UID: scoda:strat:formation:fp_v1:sha256:<hash>
    confidence: medium if formation_type present, low if NULL.
    """
    rows = conn.execute(
        "SELECT id, normalized_name, formation_type FROM formations ORDER BY id"
    ).fetchall()

    uid_map = {}  # canonical → list of ids
    records = []

    for row_id, normalized_name, formation_type in rows:
        n = normalize_for_fp(normalized_name) if normalized_name else ''
        r = normalize_for_fp(formation_type) if formation_type else 'unknown'

        canonical = f"n={n}|r={r}"
        confidence = 'medium' if formation_type else 'low'

        records.append((row_id, canonical, confidence))
        uid_map.setdefault(canonical, []).append(row_id)

    # Generate UIDs with collision handling
    results = []
    collision_counter = {}

    for row_id, canonical, confidence in records:
        hash_val = fp_sha256(canonical)
        base_uid = f"scoda:strat:formation:fp_v1:sha256:{hash_val}"

        entries = uid_map[canonical]
        if len(entries) > 1:
            if canonical not in collision_counter:
                collision_counter[canonical] = 0
            collision_counter[canonical] += 1
            idx = collision_counter[canonical]
            if idx == 1:
                uid = base_uid
            else:
                uid = f"{base_uid}-c{idx}"
        else:
            uid = base_uid

        results.append((row_id, uid, 'fp_v1', confidence, None))

    if not dry_run:
        for row_id, uid, method, confidence, same_as in results:
            conn.execute(
                "UPDATE formations SET uid=?, uid_method=?, "
                "uid_confidence=?, same_as_uid=? WHERE id=?",
                (uid, method, confidence, same_as, row_id))
        conn.commit()

    return results


# ── CrossRef DOI Lookup ──────────────────────────────────────────────────

def title_similarity(a, b):
    """Compute normalized token overlap similarity between two strings."""
    if not a or not b:
        return 0.0
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    return 2 * len(intersection) / (len(tokens_a) + len(tokens_b))


def search_crossref_doi(authors, title, year, email):
    """Search CrossRef API for DOI matching the given citation."""
    import requests

    params = {
        'query.bibliographic': f'{authors} {title}',
        'rows': 3,
        'mailto': email,
    }
    if year:
        params['filter'] = f'from-pub-date:{year},until-pub-date:{year}'

    headers = {'User-Agent': f'ScodaTrilobase/1.0 (mailto:{email})'}

    try:
        resp = requests.get(
            'https://api.crossref.org/works',
            params=params, headers=headers, timeout=30)
        if resp.status_code == 200:
            items = resp.json()['message']['items']
            for item in items:
                cr_title = item.get('title', [''])[0] if item.get('title') else ''
                sim = title_similarity(normalize_title(title), normalize_title(cr_title))
                if sim >= 0.85:
                    # Year check
                    cr_year = None
                    if 'published-print' in item:
                        parts = item['published-print'].get('date-parts', [[None]])
                        cr_year = parts[0][0]
                    elif 'published-online' in item:
                        parts = item['published-online'].get('date-parts', [[None]])
                        cr_year = parts[0][0]
                    elif 'issued' in item:
                        parts = item['issued'].get('date-parts', [[None]])
                        cr_year = parts[0][0]

                    if year and cr_year and int(year) == int(cr_year):
                        doi = item.get('DOI', '')
                        if doi:
                            return doi.lower()
            return None
    except Exception:
        return None
    return None


CHECKPOINT_FILE = 'crossref_checkpoint.json'


def load_checkpoint():
    """Load CrossRef lookup checkpoint."""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {'completed': {}, 'doi_found': {}}


def save_checkpoint(data):
    """Save CrossRef lookup checkpoint."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(data, f)


def crossref_upgrade(conn, email, limit=None, resume=False, dry_run=False):
    """Upgrade bibliography fp_v1 UIDs to DOI where possible via CrossRef API.

    Only processes article and chapter types.
    """
    checkpoint = load_checkpoint() if resume else {'completed': {}, 'doi_found': {}}

    rows = conn.execute(
        "SELECT id, authors, year, title, reference_type "
        "FROM bibliography "
        "WHERE reference_type IN ('article', 'chapter') "
        "AND uid_method = 'fp_v1' "
        "ORDER BY id"
    ).fetchall()

    if limit:
        rows = rows[:limit]

    found = 0
    skipped = 0
    errors = 0

    for i, (row_id, authors, year, title, ref_type) in enumerate(rows):
        str_id = str(row_id)
        if str_id in checkpoint['completed']:
            skipped += 1
            continue

        if not title:
            checkpoint['completed'][str_id] = 'no_title'
            continue

        doi = search_crossref_doi(authors, title, year, email)

        if doi:
            new_uid = f"scoda:bib:doi:{doi}"
            # Check if this DOI UID already exists (multiple entries → same DOI)
            existing = conn.execute(
                "SELECT id FROM bibliography WHERE uid = ?", (new_uid,)
            ).fetchone()
            if existing:
                checkpoint['completed'][str_id] = 'duplicate_doi'
                continue
            checkpoint['doi_found'][str_id] = doi
            found += 1
            if not dry_run:
                conn.execute(
                    "UPDATE bibliography SET uid=?, uid_method='doi', "
                    "uid_confidence='high' WHERE id=?",
                    (new_uid, row_id))
        else:
            checkpoint['completed'][str_id] = 'no_match'

        checkpoint['completed'][str_id] = doi or 'no_match'

        # Progress
        if (i + 1) % 50 == 0:
            print(f"  CrossRef: {i+1}/{len(rows)} processed, {found} DOIs found")
            if not dry_run:
                conn.commit()
            save_checkpoint(checkpoint)

        # Rate limit: 1 req/s
        time.sleep(1.0)

    if not dry_run:
        conn.commit()
    save_checkpoint(checkpoint)

    print(f"  CrossRef complete: {found} DOIs found, "
          f"{len(rows) - skipped - found} no match, {skipped} skipped")
    return found


# ── Macrostrat Lexicon Lookup ────────────────────────────────────────────

def search_macrostrat(formation_name):
    """Search Macrostrat API for formation lexicon entry."""
    import requests

    try:
        resp = requests.get(
            'https://macrostrat.org/api/v2/defs/strat_names',
            params={'strat_name_like': formation_name},
            timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data['success'].get('data'):
                for entry in data['success']['data']:
                    name = entry.get('strat_name', '')
                    sim = title_similarity(
                        formation_name.lower(), name.lower())
                    if sim >= 0.90:
                        return entry.get('strat_name_id')
            return None
    except Exception:
        return None
    return None


def macrostrat_upgrade(conn, limit=None, dry_run=False):
    """Upgrade formations fp_v1 UIDs to lexicon where possible via Macrostrat API."""
    rows = conn.execute(
        "SELECT id, normalized_name "
        "FROM formations "
        "WHERE uid_method = 'fp_v1' "
        "ORDER BY id"
    ).fetchall()

    if limit:
        rows = rows[:limit]

    found = 0
    skipped_dupes = 0

    for i, (row_id, normalized_name) in enumerate(rows):
        if not normalized_name:
            continue

        strat_id = search_macrostrat(normalized_name)

        if strat_id:
            new_uid = f"scoda:strat:formation:lexicon:macrostrat:{strat_id}"
            # Check if this UID already exists (multiple formations → same Macrostrat ID)
            existing = conn.execute(
                "SELECT id FROM formations WHERE uid = ?", (new_uid,)
            ).fetchone()
            if existing:
                skipped_dupes += 1
                continue
            found += 1
            if not dry_run:
                conn.execute(
                    "UPDATE formations SET uid=?, uid_method='lexicon', "
                    "uid_confidence='high' WHERE id=?",
                    (new_uid, row_id))

        # Progress
        if (i + 1) % 100 == 0:
            print(f"  Macrostrat: {i+1}/{len(rows)} processed, {found} matches")
            if not dry_run:
                conn.commit()

        # Rate limit: 5 req/s
        time.sleep(0.2)

    if not dry_run:
        conn.commit()

    print(f"  Macrostrat complete: {found} lexicon IDs found, "
          f"{skipped_dupes} duplicate skipped, "
          f"{len(rows) - found - skipped_dupes} fp_v1 retained")
    return found


# ── Report ───────────────────────────────────────────────────────────────

def report(trilobase_path, paleocore_path):
    """Print Phase C UID coverage report."""
    print("\n=== Phase C UID Report ===\n")

    # Bibliography
    conn = sqlite3.connect(trilobase_path)
    if has_uid_columns(conn, 'bibliography'):
        total = conn.execute("SELECT COUNT(*) FROM bibliography").fetchone()[0]
        with_uid = conn.execute(
            "SELECT COUNT(*) FROM bibliography WHERE uid IS NOT NULL"
        ).fetchone()[0]
        null_uid = total - with_uid

        print(f"bibliography: {with_uid}/{total} UIDs (null={null_uid})")

        # Method distribution
        for method, count in conn.execute(
            "SELECT uid_method, COUNT(*) FROM bibliography "
            "WHERE uid IS NOT NULL GROUP BY uid_method ORDER BY COUNT(*) DESC"
        ).fetchall():
            print(f"  {method}: {count}")

        # Confidence distribution
        for conf, count in conn.execute(
            "SELECT uid_confidence, COUNT(*) FROM bibliography "
            "WHERE uid IS NOT NULL GROUP BY uid_confidence ORDER BY uid_confidence"
        ).fetchall():
            print(f"  confidence={conf}: {count}")

        # Uniqueness
        distinct = conn.execute(
            "SELECT COUNT(DISTINCT uid) FROM bibliography WHERE uid IS NOT NULL"
        ).fetchone()[0]
        dupes = with_uid - distinct
        if dupes:
            print(f"  DUPLICATES: {dupes}")
        else:
            print(f"  uniqueness: OK")
    else:
        print("bibliography: uid columns not yet added")
    conn.close()

    # Formations
    conn = sqlite3.connect(paleocore_path)
    if has_uid_columns(conn, 'formations'):
        total = conn.execute("SELECT COUNT(*) FROM formations").fetchone()[0]
        with_uid = conn.execute(
            "SELECT COUNT(*) FROM formations WHERE uid IS NOT NULL"
        ).fetchone()[0]
        null_uid = total - with_uid

        print(f"\nformations: {with_uid}/{total} UIDs (null={null_uid})")

        for method, count in conn.execute(
            "SELECT uid_method, COUNT(*) FROM formations "
            "WHERE uid IS NOT NULL GROUP BY uid_method ORDER BY COUNT(*) DESC"
        ).fetchall():
            print(f"  {method}: {count}")

        for conf, count in conn.execute(
            "SELECT uid_confidence, COUNT(*) FROM formations "
            "WHERE uid IS NOT NULL GROUP BY uid_confidence ORDER BY uid_confidence"
        ).fetchall():
            print(f"  confidence={conf}: {count}")

        distinct = conn.execute(
            "SELECT COUNT(DISTINCT uid) FROM formations WHERE uid IS NOT NULL"
        ).fetchone()[0]
        dupes = with_uid - distinct
        if dupes:
            print(f"  DUPLICATES: {dupes}")
        else:
            print(f"  uniqueness: OK")
    else:
        print("formations: uid columns not yet added")
    conn.close()


# ── Verify ───────────────────────────────────────────────────────────────

def verify_db(db_path, table):
    """Verify UIDs in a database table."""
    conn = sqlite3.connect(db_path)
    total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    with_uid = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE uid IS NOT NULL"
    ).fetchone()[0]
    distinct = conn.execute(
        f"SELECT COUNT(DISTINCT uid) FROM {table} WHERE uid IS NOT NULL"
    ).fetchone()[0]
    dupes = with_uid - distinct
    null_uid = total - with_uid
    status = "OK" if null_uid == 0 and dupes == 0 else "ISSUE"
    print(f"  {table}: {with_uid}/{total} UIDs"
          f" (null={null_uid}, dupes={dupes}) [{status}]")
    conn.close()


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='UID Population Phase C — Bibliography + Formations')
    parser.add_argument(
        '--trilobase-db', default=TRILOBASE_DB,
        help='Path to trilobase.db')
    parser.add_argument(
        '--paleocore-db', default=PALEOCORE_DB,
        help='Path to paleocore.db')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview without applying changes')
    parser.add_argument(
        '--report', action='store_true',
        help='Print coverage report')
    parser.add_argument(
        '--crossref', action='store_true',
        help='Run CrossRef DOI lookup (requires --email)')
    parser.add_argument(
        '--email', type=str,
        help='Email for CrossRef polite pool')
    parser.add_argument(
        '--macrostrat', action='store_true',
        help='Run Macrostrat lexicon lookup')
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Limit API lookups to N records')
    parser.add_argument(
        '--resume', action='store_true',
        help='Resume CrossRef lookup from checkpoint')
    args = parser.parse_args()

    trilobase_path = os.path.abspath(args.trilobase_db)
    paleocore_path = os.path.abspath(args.paleocore_db)

    # Report mode
    if args.report:
        report(trilobase_path, paleocore_path)
        return

    # Validate
    if args.crossref and not args.email:
        print("Error: --crossref requires --email", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(trilobase_path):
        print(f"Error: {trilobase_path} not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(paleocore_path):
        print(f"Error: {paleocore_path} not found", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print("=== DRY RUN (no changes will be made) ===\n")

    # ── Step 1: Schema migration + fp_v1 ──

    if not args.crossref and not args.macrostrat:
        # Bibliography
        print("--- Bibliography (trilobase.db) ---")
        conn = sqlite3.connect(trilobase_path)
        added = add_uid_columns(conn, 'bibliography')
        if added:
            print("  Added uid columns to bibliography")
        else:
            print("  bibliography: uid columns already exist")

        print("  Generating fp_v1 UIDs...")
        results = generate_bibliography_uids(conn, args.dry_run)

        by_confidence = {}
        for _, _, _, conf, _ in results:
            by_confidence[conf] = by_confidence.get(conf, 0) + 1
        conf_str = ', '.join(f"{c}: {n}" for c, n in sorted(by_confidence.items()))
        print(f"  bibliography: {len(results)} UIDs ({conf_str})")

        # Check collisions
        uid_set = set()
        collisions = 0
        for _, uid, _, _, _ in results:
            if uid in uid_set:
                collisions += 1
            uid_set.add(uid)
        if collisions:
            print(f"  WARNING: {collisions} UID collisions detected")

        if not args.dry_run:
            create_uid_index(conn, 'bibliography')
            print("  Created UNIQUE index on bibliography.uid")

        conn.close()

        if not args.dry_run:
            verify_db(trilobase_path, 'bibliography')

        # Formations
        print("\n--- Formations (paleocore.db) ---")
        conn = sqlite3.connect(paleocore_path)
        added = add_uid_columns(conn, 'formations')
        if added:
            print("  Added uid columns to formations")
        else:
            print("  formations: uid columns already exist")

        print("  Generating fp_v1 UIDs...")
        results = generate_formations_uids(conn, args.dry_run)

        by_confidence = {}
        for _, _, _, conf, _ in results:
            by_confidence[conf] = by_confidence.get(conf, 0) + 1
        conf_str = ', '.join(f"{c}: {n}" for c, n in sorted(by_confidence.items()))
        print(f"  formations: {len(results)} UIDs ({conf_str})")

        if not args.dry_run:
            create_uid_index(conn, 'formations')
            print("  Created UNIQUE index on formations.uid")

        conn.close()

        if not args.dry_run:
            verify_db(paleocore_path, 'formations')

    # ── Step 2: CrossRef DOI upgrade ──

    if args.crossref:
        print("\n--- CrossRef DOI Lookup ---")
        conn = sqlite3.connect(trilobase_path)
        crossref_upgrade(conn, args.email, args.limit, args.resume, args.dry_run)
        conn.close()

        if not args.dry_run:
            verify_db(trilobase_path, 'bibliography')

    # ── Step 3: Macrostrat Lexicon upgrade ──

    if args.macrostrat:
        print("\n--- Macrostrat Lexicon Lookup ---")
        conn = sqlite3.connect(paleocore_path)
        macrostrat_upgrade(conn, args.limit, args.dry_run)
        conn.close()

        if not args.dry_run:
            verify_db(paleocore_path, 'formations')

    # Final report
    if args.dry_run:
        report(trilobase_path, paleocore_path)


if __name__ == '__main__':
    main()
