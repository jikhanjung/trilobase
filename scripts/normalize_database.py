#!/usr/bin/env python3
"""
Trilobase Database Normalization Script
Phase 5: Normalize formations, locations, and complete synonym relationships
"""

import sqlite3
import re
from pathlib import Path
from collections import Counter

def normalize_database(db_path):
    """Normalize the trilobase database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=== Phase 5: Database Normalization ===\n")

    # 1. Add senior_taxon_id column to synonyms if not exists
    print("1. Adding senior_taxon_id to synonyms table...")
    try:
        cursor.execute("ALTER TABLE synonyms ADD COLUMN senior_taxon_id INTEGER")
        conn.commit()
        print("   - Column added")
    except sqlite3.OperationalError:
        print("   - Column already exists")

    # 2. Link synonyms to senior taxa
    print("\n2. Linking synonyms to senior taxa...")
    cursor.execute("""
        UPDATE synonyms
        SET senior_taxon_id = (
            SELECT t.id FROM taxa t
            WHERE t.name = synonyms.senior_taxon_name
            LIMIT 1
        )
        WHERE senior_taxon_name IS NOT NULL AND senior_taxon_name != ''
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM synonyms WHERE senior_taxon_id IS NOT NULL")
    linked = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM synonyms WHERE senior_taxon_name IS NOT NULL AND senior_taxon_name != ''")
    total_with_name = cursor.fetchone()[0]
    print(f"   - Linked: {linked}/{total_with_name}")

    # 3. Create normalized formations table
    print("\n3. Creating normalized formations table...")
    cursor.executescript("""
        DROP TABLE IF EXISTS formations;
        CREATE TABLE formations (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            normalized_name TEXT,
            formation_type TEXT,  -- Fm, Lst, Sh, Gp, etc.
            country TEXT,
            region TEXT,
            period TEXT,
            taxa_count INTEGER DEFAULT 0
        );
    """)

    # Extract unique formations and insert
    cursor.execute("SELECT DISTINCT formation FROM taxa WHERE formation IS NOT NULL")
    formations = cursor.fetchall()

    formation_data = []
    for (formation,) in formations:
        # Parse formation type
        fm_type = None
        if ' Fm' in formation or formation.endswith(' Fm'):
            fm_type = 'Formation'
        elif ' Lst' in formation:
            fm_type = 'Limestone'
        elif ' Sh' in formation:
            fm_type = 'Shale'
        elif ' Gp' in formation:
            fm_type = 'Group'
        elif ' Horizon' in formation:
            fm_type = 'Horizon'
        elif ' Zone' in formation:
            fm_type = 'Zone'
        elif ' Suite' in formation:
            fm_type = 'Suite'
        elif ' Beds' in formation:
            fm_type = 'Beds'

        # Normalize name (remove type suffix for grouping)
        normalized = re.sub(r'\s+(Fm|Lst|Sh|Gp|Horizon|Zone|Suite|Beds)\.?$', '', formation)

        formation_data.append((formation, normalized, fm_type))

    cursor.executemany(
        "INSERT OR IGNORE INTO formations (name, normalized_name, formation_type) VALUES (?, ?, ?)",
        formation_data
    )
    conn.commit()

    # Update taxa_count
    cursor.execute("""
        UPDATE formations SET taxa_count = (
            SELECT COUNT(*) FROM taxa WHERE taxa.formation = formations.name
        )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM formations")
    print(f"   - Formations inserted: {cursor.fetchone()[0]}")

    # 4. Create countries table and extract countries from locations
    print("\n4. Creating countries table and extracting country data...")
    cursor.executescript("""
        DROP TABLE IF EXISTS countries;
        CREATE TABLE countries (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            code TEXT,
            taxa_count INTEGER DEFAULT 0
        );
    """)

    # Extract countries from location field
    cursor.execute("SELECT DISTINCT location FROM taxa WHERE location IS NOT NULL")
    locations = cursor.fetchall()

    country_counter = Counter()
    for (location,) in locations:
        # Country is usually the last part after comma
        if location:
            parts = [p.strip() for p in location.split(',')]
            country = parts[-1] if parts else location
            # Clean up common variations
            country = country.strip()
            if country:
                country_counter[country] += 1

    # Insert countries
    for country in country_counter.keys():
        cursor.execute("INSERT OR IGNORE INTO countries (name) VALUES (?)", (country,))

    # Update taxa_count for countries
    cursor.execute("SELECT id, name FROM countries")
    countries = cursor.fetchall()
    for country_id, country_name in countries:
        cursor.execute(
            "SELECT COUNT(*) FROM taxa WHERE location LIKE ?",
            (f'%{country_name}',)
        )
        count = cursor.fetchone()[0]
        cursor.execute("UPDATE countries SET taxa_count = ? WHERE id = ?", (count, country_id))

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM countries")
    print(f"   - Countries extracted: {cursor.fetchone()[0]}")

    # 5. Add country_id to taxa table
    print("\n5. Adding country reference to taxa...")
    try:
        cursor.execute("ALTER TABLE taxa ADD COLUMN country_id INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Update country_id based on location
    cursor.execute("SELECT id, name FROM countries")
    countries = cursor.fetchall()
    for country_id, country_name in countries:
        cursor.execute(
            "UPDATE taxa SET country_id = ? WHERE location LIKE ?",
            (country_id, f'%{country_name}')
        )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM taxa WHERE country_id IS NOT NULL")
    print(f"   - Taxa with country linked: {cursor.fetchone()[0]}")

    # 6. Add formation_id to taxa table
    print("\n6. Adding formation reference to taxa...")
    try:
        cursor.execute("ALTER TABLE taxa ADD COLUMN formation_id INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    cursor.execute("""
        UPDATE taxa SET formation_id = (
            SELECT f.id FROM formations f WHERE f.name = taxa.formation
        )
        WHERE formation IS NOT NULL
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM taxa WHERE formation_id IS NOT NULL")
    print(f"   - Taxa with formation linked: {cursor.fetchone()[0]}")

    # 7. Create indexes for better query performance
    print("\n7. Creating indexes...")
    cursor.executescript("""
        CREATE INDEX IF NOT EXISTS idx_taxa_country ON taxa(country_id);
        CREATE INDEX IF NOT EXISTS idx_taxa_formation_id ON taxa(formation_id);
        CREATE INDEX IF NOT EXISTS idx_synonyms_senior ON synonyms(senior_taxon_id);
        CREATE INDEX IF NOT EXISTS idx_formations_type ON formations(formation_type);
        CREATE INDEX IF NOT EXISTS idx_countries_name ON countries(name);
    """)
    conn.commit()
    print("   - Indexes created")

    # Print summary statistics
    print("\n=== Normalization Complete ===\n")

    print("Table Statistics:")
    for table in ['taxa', 'synonyms', 'formations', 'countries', 'temporal_ranges']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  - {table}: {cursor.fetchone()[0]} records")

    print("\nTop 10 Countries by Taxa Count:")
    cursor.execute("""
        SELECT name, taxa_count FROM countries
        ORDER BY taxa_count DESC LIMIT 10
    """)
    for name, count in cursor.fetchall():
        print(f"  - {name}: {count}")

    print("\nSynonym Linkage:")
    cursor.execute("SELECT COUNT(*) FROM synonyms WHERE senior_taxon_id IS NOT NULL")
    linked = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM synonyms")
    total = cursor.fetchone()[0]
    print(f"  - Linked to senior taxa: {linked}/{total} ({100*linked/total:.1f}%)")

    conn.close()


if __name__ == '__main__':
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / 'trilobase.db'

    print(f"Normalizing database: {db_path}\n")
    normalize_database(db_path)
