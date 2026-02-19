#!/usr/bin/env python3
"""
Parse Jell & Adrain (2002) Literature Cited and import into database.
"""

import re
import sqlite3
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
INPUT_FILE = os.path.join(PROJECT_DIR, 'data', 'Jell_and_Adrain_2002_Literature_Cited.txt')
DATABASE = os.path.join(PROJECT_DIR, 'db', 'trilobase.db')


def read_and_merge_lines(filepath):
    """Read file and merge continuation lines into complete references."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    current_entry = []
    last_author = None

    for line in lines:
        line = line.rstrip()

        # Skip header line
        if line.strip() == 'LITERATURE CITED':
            continue

        # Empty line - save current entry
        if not line.strip():
            if current_entry:
                entries.append((' '.join(current_entry), last_author))
                current_entry = []
            continue

        # Check if this is a new entry
        # New entry starts with: UPPERCASE AUTHOR or year (continuation of same author)
        is_new_author = re.match(r'^[A-Z][A-Z]+[,\s]', line)
        is_year_only = re.match(r'^(\d{4})[a-z]?\.?\s', line)
        is_cross_ref = 'see ' in line.lower() and len(line) < 100

        if is_new_author or is_year_only or is_cross_ref:
            # Save previous entry
            if current_entry:
                entries.append((' '.join(current_entry), last_author))
                current_entry = []

            # Update last author for year-only entries
            if is_new_author:
                # Extract author part (before year)
                match = re.match(r'^(.+?)\s+\d{4}', line)
                if match:
                    last_author = match.group(1).strip()

            current_entry = [line]
        else:
            # Continuation line
            current_entry.append(line)

    # Don't forget last entry
    if current_entry:
        entries.append((' '.join(current_entry), last_author))

    return entries


def parse_reference(raw_text, prev_author=None):
    """Parse a single reference entry into structured fields."""
    result = {
        'authors': None,
        'year': None,
        'year_suffix': None,
        'title': None,
        'journal': None,
        'volume': None,
        'pages': None,
        'publisher': None,
        'city': None,
        'editors': None,
        'book_title': None,
        'reference_type': 'article',
        'raw_entry': raw_text
    }

    text = raw_text.strip()

    # Handle cross-references
    if re.search(r'\bsee\s+[A-Z]', text, re.IGNORECASE):
        result['reference_type'] = 'cross_ref'
        result['authors'] = text
        return result

    # Try to extract author and year
    # Pattern: AUTHOR(S) YEAR. or just YEAR. (continuation)

    # Check if starts with year only (same author continuation)
    year_only_match = re.match(r'^(\d{4})([a-z])?\.?\s*(.+)$', text)
    if year_only_match and prev_author:
        result['authors'] = prev_author
        result['year'] = int(year_only_match.group(1))
        result['year_suffix'] = year_only_match.group(2)
        remainder = year_only_match.group(3)
    else:
        # Standard format: AUTHOR(S) YEAR.
        author_year_match = re.match(r'^(.+?)\s+(\d{4})([a-z])?\.?\s*(.*)$', text)
        if author_year_match:
            result['authors'] = author_year_match.group(1).strip()
            result['year'] = int(author_year_match.group(2))
            result['year_suffix'] = author_year_match.group(3)
            remainder = author_year_match.group(4)
        else:
            # Can't parse - store as is
            result['authors'] = text[:100] if len(text) > 100 else text
            return result

    # Parse remainder for title, journal, etc.
    if remainder:
        # Check for book pattern: (Publisher: City)
        book_match = re.search(r'\(([^:]+):\s*([^)]+)\)', remainder)
        if book_match:
            result['reference_type'] = 'book'
            result['publisher'] = book_match.group(1).strip()
            result['city'] = book_match.group(2).strip()
            # Title is before the publisher
            title_part = remainder[:book_match.start()].strip()
            result['title'] = title_part.rstrip('.')
            # Pages after publisher
            pages_match = re.search(r'(\d+p)', remainder[book_match.end():])
            if pages_match:
                result['pages'] = pages_match.group(1)

        # Check for chapter pattern: Pp. X-Y. In EDITOR (ed.)
        chapter_match = re.search(r'[Pp]p?\.?\s*(\d+[-–]\d+).*?In\s+(.+?)\s*\(ed', remainder)
        if chapter_match:
            result['reference_type'] = 'chapter'
            result['pages'] = chapter_match.group(1)
            result['editors'] = chapter_match.group(2).strip()
            # Extract book title after (ed.) or (eds)
            book_title_match = re.search(r'\(eds?\.\)\s*(.+?)(?:\(|$)', remainder)
            if book_title_match:
                result['book_title'] = book_title_match.group(1).strip().rstrip('.')

        # Check for journal article pattern: Journal volume: pages
        if result['reference_type'] == 'article':
            # Try to find journal pattern
            journal_match = re.search(r'\.\s*([A-Z][^.]+?)\s+(\d+(?:\([^)]+\))?)\s*:\s*(\d+[-–]\d+)', remainder)
            if journal_match:
                result['journal'] = journal_match.group(1).strip()
                result['volume'] = journal_match.group(2)
                result['pages'] = journal_match.group(3)
                # Title is before journal
                title_end = remainder.find(journal_match.group(1))
                if title_end > 0:
                    result['title'] = remainder[:title_end].strip().rstrip('.')
            else:
                # Just extract title (first sentence)
                title_match = re.match(r'^[\[\(]?(.+?)[\]\)]?\.(?:\s|$)', remainder)
                if title_match:
                    result['title'] = title_match.group(1).strip()
                else:
                    result['title'] = remainder[:200] if len(remainder) > 200 else remainder

    return result


def create_table(conn):
    """Create references table."""
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS bibliography')

    cursor.execute('''
        CREATE TABLE bibliography (
            id INTEGER PRIMARY KEY,
            authors TEXT NOT NULL,
            year INTEGER,
            year_suffix TEXT,
            title TEXT,
            journal TEXT,
            volume TEXT,
            pages TEXT,
            publisher TEXT,
            city TEXT,
            editors TEXT,
            book_title TEXT,
            reference_type TEXT DEFAULT 'article',
            raw_entry TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('CREATE INDEX idx_bibliography_authors ON bibliography(authors)')
    cursor.execute('CREATE INDEX idx_bibliography_year ON bibliography(year)')

    conn.commit()


def import_references(conn, references):
    """Import parsed references into database."""
    cursor = conn.cursor()

    for ref in references:
        cursor.execute('''
            INSERT INTO bibliography
            (authors, year, year_suffix, title, journal, volume, pages,
             publisher, city, editors, book_title, reference_type, raw_entry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ref['authors'],
            ref['year'],
            ref['year_suffix'],
            ref['title'],
            ref['journal'],
            ref['volume'],
            ref['pages'],
            ref['publisher'],
            ref['city'],
            ref['editors'],
            ref['book_title'],
            ref['reference_type'],
            ref['raw_entry']
        ))

    conn.commit()


def main():
    print("Phase 12: Parsing Literature Cited")
    print("=" * 50)

    # Step 1: Read and merge lines
    print("\n[Step 1] Reading and merging lines...")
    entries = read_and_merge_lines(INPUT_FILE)
    print(f"  Found {len(entries)} entries")

    # Step 2: Parse each entry
    print("\n[Step 2] Parsing entries...")
    references = []
    last_author = None

    for raw_text, prev_author in entries:
        ref = parse_reference(raw_text, prev_author or last_author)
        references.append(ref)
        if ref['authors'] and ref['reference_type'] != 'cross_ref':
            last_author = ref['authors']

    # Statistics
    types = {}
    years = []
    for ref in references:
        t = ref['reference_type']
        types[t] = types.get(t, 0) + 1
        if ref['year']:
            years.append(ref['year'])

    print(f"  Parsed {len(references)} references")
    print(f"  Types: {types}")
    if years:
        print(f"  Year range: {min(years)} - {max(years)}")

    # Step 3: Create table and import
    print("\n[Step 3] Creating table and importing...")
    conn = sqlite3.connect(DATABASE)

    create_table(conn)
    import_references(conn, references)

    # Verify
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM bibliography')
    count = cursor.fetchone()[0]
    print(f"  Imported {count} references")

    # Show sample
    print("\n[Sample entries]")
    cursor.execute('''
        SELECT id, authors, year, year_suffix, reference_type,
               substr(title, 1, 50) as title_short
        FROM bibliography
        WHERE year IS NOT NULL
        LIMIT 5
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1][:30]}... ({row[2]}{row[3] or ''}) [{row[4]}]")
        if row[5]:
            print(f"      Title: {row[5]}...")

    conn.close()
    print("\n[Done]")


if __name__ == '__main__':
    main()
