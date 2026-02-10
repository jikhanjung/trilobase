"""
Phase 13: Add SCODA-Core tables to trilobase.db

Creates:
  - artifact_metadata: Identity, version, integrity
  - provenance: Data sources and lineage
  - schema_descriptions: Self-describing schema semantics
"""

import sqlite3
import os
import sys
from datetime import date


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'trilobase.db')


def create_tables(conn):
    """Create SCODA-Core tables."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS artifact_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS provenance (
            id INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            citation TEXT NOT NULL,
            description TEXT,
            year INTEGER,
            url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_descriptions (
            table_name TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        )
    """)

    conn.commit()
    print("SCODA tables created.")


def insert_metadata(conn):
    """Insert artifact identity and metadata."""
    cursor = conn.cursor()

    metadata = [
        ('artifact_id', 'trilobase'),
        ('name', 'Trilobase'),
        ('version', '1.0.0'),
        ('schema_version', '1.0'),
        ('created_at', str(date.today())),
        ('description',
         'Trilobite genus-level taxonomy database based on Jell & Adrain (2002)'),
        ('license', 'CC-BY-4.0'),
    ]

    for key, value in metadata:
        cursor.execute(
            "INSERT OR REPLACE INTO artifact_metadata (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    print(f"Inserted {len(metadata)} metadata entries.")


def insert_provenance(conn):
    """Insert data provenance records."""
    cursor = conn.cursor()

    sources = [
        (1, 'primary',
         'Jell, P.A. & Adrain, J.M. (2002) Available generic names for trilobites. Memoirs of the Queensland Museum 48(2): 331-553.',
         'Primary source for genus-level taxonomy, synonymy, and type species',
         2002, None),
        (2, 'supplementary',
         'Adrain, J.M. (2011) Class Trilobita Walch, 1771. In: Zhang, Z.-Q. (Ed.) Animal biodiversity: An outline of higher-level classification. Zootaxa 3148: 104-109.',
         'Suprafamilial classification (Order, Suborder, Superfamily)',
         2011, None),
        (3, 'build',
         'Trilobase data pipeline (2026). Scripts: normalize_lines.py, create_database.py, normalize_database.py, fix_synonyms.py, normalize_families.py, populate_taxonomic_ranks.py, parse_references.py',
         'Automated extraction, cleaning, and normalization pipeline',
         2026, None),
    ]

    for s in sources:
        cursor.execute(
            "INSERT OR REPLACE INTO provenance (id, source_type, citation, description, year, url) "
            "VALUES (?, ?, ?, ?, ?, ?)", s
        )

    conn.commit()
    print(f"Inserted {len(sources)} provenance records.")


def insert_schema_descriptions(conn):
    """Insert schema descriptions for all tables and columns."""
    cursor = conn.cursor()

    descriptions = [
        # --- taxonomic_ranks ---
        ('taxonomic_ranks', None,
         'Unified taxonomic hierarchy from Class to Genus (5,338 records)'),
        ('taxonomic_ranks', 'id', 'Primary key'),
        ('taxonomic_ranks', 'name', 'Taxon name'),
        ('taxonomic_ranks', 'rank',
         'Taxonomic rank: Class, Order, Suborder, Superfamily, Family, or Genus'),
        ('taxonomic_ranks', 'parent_id',
         'FK to parent taxonomic_ranks.id (Class→Order→...→Family→Genus)'),
        ('taxonomic_ranks', 'author', 'Authority who described or named this taxon'),
        ('taxonomic_ranks', 'year', 'Year of original description'),
        ('taxonomic_ranks', 'year_suffix',
         'Suffix for year disambiguation (a, b, c) when author published multiple taxa in same year'),
        ('taxonomic_ranks', 'genera_count',
         'Count of descendant genera (for ranks above Genus)'),
        ('taxonomic_ranks', 'notes', 'Additional notes or remarks'),
        ('taxonomic_ranks', 'type_species',
         'Type species designation (Genus only)'),
        ('taxonomic_ranks', 'type_species_author',
         'Author of the type species (Genus only)'),
        ('taxonomic_ranks', 'formation',
         'Original formation/locality text from source (Genus only)'),
        ('taxonomic_ranks', 'location',
         'Original country/location text from source (Genus only)'),
        ('taxonomic_ranks', 'family',
         'Family name as text, from original source (Genus only)'),
        ('taxonomic_ranks', 'temporal_code',
         'Geological time code: LCAM, MCAM, UCAM, LORD, MORD, UORD, LSIL, USIL, LDEV, MDEV, UDEV, MISS, PENN, LPERM, PERM, UPERM (Genus only)'),
        ('taxonomic_ranks', 'is_valid',
         '1 = valid taxon, 0 = invalid (synonym, nomen nudum, etc.) (Genus only)'),
        ('taxonomic_ranks', 'raw_entry',
         'Original text entry from Jell & Adrain (2002) (Genus only)'),
        ('taxonomic_ranks', 'country_id',
         'FK to countries.id (legacy, use genus_locations instead)'),
        ('taxonomic_ranks', 'formation_id',
         'FK to formations.id (legacy, use genus_formations instead)'),

        # --- synonyms ---
        ('synonyms', None,
         'Taxonomic synonym relationships (1,055 records)'),
        ('synonyms', 'id', 'Primary key'),
        ('synonyms', 'junior_taxon_id',
         'FK to taxonomic_ranks.id — the junior (invalid) taxon'),
        ('synonyms', 'senior_taxon_name',
         'Name of the senior (valid) taxon'),
        ('synonyms', 'senior_taxon_id',
         'FK to taxonomic_ranks.id — the senior (valid) taxon'),
        ('synonyms', 'synonym_type',
         'Type: j.s.s. (junior subjective synonym), j.o.s. (junior objective synonym), preocc. (preoccupied), replacement, suppressed'),
        ('synonyms', 'fide_author',
         'Attribution: "according to AUTHOR" (fide)'),
        ('synonyms', 'fide_year',
         'Year of the attribution reference'),
        ('synonyms', 'notes', 'Additional notes'),

        # --- formations ---
        ('formations', None,
         'Geological formations where genera were found (2,009 records)'),
        ('formations', 'id', 'Primary key'),
        ('formations', 'name', 'Formation name as given in source'),
        ('formations', 'normalized_name', 'Lowercased, normalized form of name'),
        ('formations', 'formation_type',
         'Abbreviation: Fm (Formation), Sh (Shale), Lst (Limestone), Gp (Group), etc.'),
        ('formations', 'country', 'Country where formation is located'),
        ('formations', 'region', 'Region within country'),
        ('formations', 'period', 'Geological period'),
        ('formations', 'taxa_count', 'Number of genera from this formation'),

        # --- countries ---
        ('countries', None,
         'Countries where genera were found (151 records)'),
        ('countries', 'id', 'Primary key'),
        ('countries', 'name', 'Country name'),
        ('countries', 'code', 'ISO country code'),
        ('countries', 'taxa_count', 'Number of genera from this country'),

        # --- genus_formations ---
        ('genus_formations', None,
         'Many-to-many relationship between genera and formations (4,854 records)'),
        ('genus_formations', 'genus_id', 'FK to taxonomic_ranks.id'),
        ('genus_formations', 'formation_id', 'FK to formations.id'),
        ('genus_formations', 'is_type_locality',
         '1 if this is the type locality for the genus'),
        ('genus_formations', 'notes', 'Additional notes'),

        # --- genus_locations ---
        ('genus_locations', None,
         'Many-to-many relationship between genera and countries (4,841 records)'),
        ('genus_locations', 'genus_id', 'FK to taxonomic_ranks.id'),
        ('genus_locations', 'country_id', 'FK to countries.id'),
        ('genus_locations', 'region', 'Specific region within the country'),
        ('genus_locations', 'is_type_locality',
         '1 if this is the type locality for the genus'),
        ('genus_locations', 'notes', 'Additional notes'),

        # --- temporal_ranges ---
        ('temporal_ranges', None,
         'Geological time period codes and their age ranges (28 records)'),
        ('temporal_ranges', 'id', 'Primary key'),
        ('temporal_ranges', 'code',
         'Short code: LCAM, MCAM, UCAM, LORD, MORD, UORD, etc.'),
        ('temporal_ranges', 'name', 'Full name of the time period'),
        ('temporal_ranges', 'period',
         'Parent period: Cambrian, Ordovician, Silurian, Devonian, Carboniferous, Permian'),
        ('temporal_ranges', 'epoch', 'Epoch within period: Lower, Middle, Upper'),
        ('temporal_ranges', 'start_mya',
         'Start of range in millions of years ago'),
        ('temporal_ranges', 'end_mya',
         'End of range in millions of years ago'),

        # --- bibliography ---
        ('bibliography', None,
         'Literature cited in Jell & Adrain (2002) (2,130 records)'),
        ('bibliography', 'id', 'Primary key'),
        ('bibliography', 'authors', 'Author(s) of the reference'),
        ('bibliography', 'year', 'Publication year'),
        ('bibliography', 'year_suffix',
         'Suffix for disambiguation (a, b, c)'),
        ('bibliography', 'title', 'Title of the work'),
        ('bibliography', 'journal', 'Journal name (for articles)'),
        ('bibliography', 'volume', 'Volume number'),
        ('bibliography', 'pages', 'Page range'),
        ('bibliography', 'publisher', 'Publisher (for books)'),
        ('bibliography', 'city', 'City of publication (for books)'),
        ('bibliography', 'editors', 'Editor(s) (for book chapters)'),
        ('bibliography', 'book_title', 'Book title (for chapters)'),
        ('bibliography', 'reference_type',
         'Type: article, book, chapter, cross_ref'),
        ('bibliography', 'raw_entry', 'Original text from Literature Cited section'),

        # --- SCODA tables ---
        ('artifact_metadata', None,
         'SCODA artifact identity and metadata (key-value store)'),
        ('artifact_metadata', 'key', 'Metadata key (e.g., version, name)'),
        ('artifact_metadata', 'value', 'Metadata value'),

        ('provenance', None,
         'Data sources and lineage for this artifact'),
        ('provenance', 'source_type',
         'Type: primary, supplementary, or build'),
        ('provenance', 'citation', 'Full citation text'),
        ('provenance', 'description',
         'What this source contributed to the dataset'),
        ('provenance', 'year', 'Year of the source'),
        ('provenance', 'url', 'URL if available'),

        ('schema_descriptions', None,
         'Self-describing schema: human-readable descriptions of all tables and columns'),
        ('schema_descriptions', 'table_name', 'Name of the described table'),
        ('schema_descriptions', 'column_name',
         'Column name (NULL for table-level description)'),
        ('schema_descriptions', 'description', 'Human-readable description'),
    ]

    for table_name, column_name, desc in descriptions:
        cursor.execute(
            "INSERT OR REPLACE INTO schema_descriptions (table_name, column_name, description) "
            "VALUES (?, ?, ?)",
            (table_name, column_name, desc)
        )

    conn.commit()
    print(f"Inserted {len(descriptions)} schema descriptions.")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    print(f"Adding SCODA tables to: {db_path}")
    conn = sqlite3.connect(db_path)

    create_tables(conn)
    insert_metadata(conn)
    insert_provenance(conn)
    insert_schema_descriptions(conn)

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM artifact_metadata")
    print(f"\nVerification:")
    print(f"  artifact_metadata: {cursor.fetchone()[0]} entries")
    cursor.execute("SELECT COUNT(*) FROM provenance")
    print(f"  provenance: {cursor.fetchone()[0]} entries")
    cursor.execute("SELECT COUNT(*) FROM schema_descriptions")
    print(f"  schema_descriptions: {cursor.fetchone()[0]} entries")

    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
