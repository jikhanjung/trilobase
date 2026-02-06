"""
Tests for Trilobase Flask application (app.py)
"""

import json
import sqlite3
import os
import tempfile

import pytest

from app import app, get_db


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database with sample data."""
    db_path = str(tmp_path / "test_trilobase.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
        CREATE TABLE taxonomic_ranks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rank TEXT NOT NULL,
            parent_id INTEGER,
            author TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            genera_count INTEGER DEFAULT 0,
            year TEXT,
            year_suffix TEXT,
            type_species TEXT,
            type_species_author TEXT,
            formation TEXT,
            location TEXT,
            temporal_code TEXT,
            is_valid INTEGER DEFAULT 1,
            raw_entry TEXT,
            country_id INTEGER,
            formation_id INTEGER,
            family TEXT,
            FOREIGN KEY (parent_id) REFERENCES taxonomic_ranks(id)
        );

        CREATE TABLE synonyms (
            id INTEGER PRIMARY KEY,
            junior_taxon_id INTEGER,
            senior_taxon_name TEXT,
            synonym_type TEXT,
            fide_author TEXT,
            fide_year TEXT,
            notes TEXT,
            senior_taxon_id INTEGER,
            FOREIGN KEY (junior_taxon_id) REFERENCES taxonomic_ranks(id)
        );

        CREATE TABLE formations (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            normalized_name TEXT,
            formation_type TEXT,
            country TEXT,
            region TEXT,
            period TEXT,
            taxa_count INTEGER DEFAULT 0
        );

        CREATE TABLE countries (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            code TEXT,
            taxa_count INTEGER DEFAULT 0
        );

        CREATE TABLE genus_formations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genus_id INTEGER NOT NULL,
            formation_id INTEGER NOT NULL,
            is_type_locality INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
            FOREIGN KEY (formation_id) REFERENCES formations(id),
            UNIQUE(genus_id, formation_id)
        );

        CREATE TABLE genus_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genus_id INTEGER NOT NULL,
            country_id INTEGER NOT NULL,
            region TEXT,
            is_type_locality INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
            FOREIGN KEY (country_id) REFERENCES countries(id),
            UNIQUE(genus_id, country_id, region)
        );

        CREATE VIEW taxa AS
        SELECT * FROM taxonomic_ranks WHERE rank = 'Genus';

        -- SCODA-Core tables
        CREATE TABLE artifact_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE provenance (
            id INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            citation TEXT NOT NULL,
            description TEXT,
            year INTEGER,
            url TEXT
        );

        CREATE TABLE schema_descriptions (
            table_name TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        );
    """)

    # Insert sample data: Class -> Order -> Family -> Genus hierarchy
    cursor.executescript("""
        -- Class
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count)
        VALUES (1, 'Trilobita', 'Class', NULL, 'WALCH, 1771', 5113);

        -- Orders
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count)
        VALUES (2, 'Phacopida', 'Order', 1, 'SALTER, 1864', 500);

        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count)
        VALUES (3, 'Ptychopariida', 'Order', 1, 'SWINNERTON, 1915', 1200);

        -- Family under Phacopida
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count)
        VALUES (10, 'Phacopidae', 'Family', 2, 'HAWLE & CORDA, 1847', 30);

        -- Family under Ptychopariida
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, genera_count)
        VALUES (11, 'Olenidae', 'Family', 3, 'BURMEISTER, 1843', 50);

        -- Genera under Phacopidae
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family)
        VALUES (100, 'Phacops', 'Genus', 10, 'EMMRICH', '1839', NULL,
            'Calymene macrophthalma BRONGNIART, 1822', 'Various', 'Worldwide',
            'LDEV-UDEV', 1, 'Phacops EMMRICH, 1839. ...', 'Phacopidae');

        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family)
        VALUES (101, 'Acuticryphops', 'Genus', 10, 'RICHTER & RICHTER', '1926', NULL,
            'Phacops acuticeps KAYSER, 1889', 'Büdesheimer Sh', 'Germany',
            'UDEV', 1, 'Acuticryphops RICHTER & RICHTER, 1926. ...', 'Phacopidae');

        -- An invalid genus (synonym)
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family)
        VALUES (102, 'Cryphops', 'Genus', 10, 'RICHTER', '1856', NULL,
            NULL, NULL, 'Germany', 'UDEV', 0,
            'Cryphops RICHTER, 1856 [j.s.s. of Acuticryphops]', 'Phacopidae');

        -- Genus under Olenidae
        INSERT INTO taxonomic_ranks (id, name, rank, parent_id, author, year, type_species,
            type_species_author, formation, location, temporal_code, is_valid, raw_entry, family)
        VALUES (200, 'Olenus', 'Genus', 11, 'DALMAN', '1827', NULL,
            'Entomostracites gibbosus WAHLENBERG, 1818', 'Alum Sh', 'Sweden',
            'UCAM', 1, 'Olenus DALMAN, 1827. ...', 'Olenidae');
    """)

    # Synonyms
    cursor.execute("""
        INSERT INTO synonyms (id, junior_taxon_id, senior_taxon_name, senior_taxon_id,
            synonym_type, fide_author, fide_year)
        VALUES (1, 102, 'Acuticryphops', 101, 'j.s.s.', 'CLARKSON', '1969')
    """)

    # Countries
    cursor.executescript("""
        INSERT INTO countries (id, name, code, taxa_count) VALUES (1, 'Germany', 'DE', 150);
        INSERT INTO countries (id, name, code, taxa_count) VALUES (2, 'Sweden', 'SE', 80);
    """)

    # Formations
    cursor.executescript("""
        INSERT INTO formations (id, name, normalized_name, formation_type, country, period, taxa_count)
        VALUES (1, 'Büdesheimer Sh', 'budesheimer sh', 'Sh', 'Germany', 'Devonian', 5);

        INSERT INTO formations (id, name, normalized_name, formation_type, country, period, taxa_count)
        VALUES (2, 'Alum Sh', 'alum sh', 'Sh', 'Sweden', 'Cambrian', 20);
    """)

    # Genus-Formation relations
    cursor.executescript("""
        INSERT INTO genus_formations (genus_id, formation_id) VALUES (101, 1);
        INSERT INTO genus_formations (genus_id, formation_id) VALUES (200, 2);
    """)

    # Genus-Location relations
    cursor.executescript("""
        INSERT INTO genus_locations (genus_id, country_id, region) VALUES (101, 1, 'Eifel');
        INSERT INTO genus_locations (genus_id, country_id, region) VALUES (200, 2, 'Scania');
    """)

    # Bibliography (for metadata statistics)
    cursor.execute("""
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
    """)
    cursor.execute("""
        INSERT INTO bibliography (id, authors, year, title, journal, reference_type, raw_entry)
        VALUES (1, 'Jell, P.A. & Adrain, J.M.', 2002, 'Available generic names for trilobites',
                'Memoirs of the Queensland Museum', 'article',
                'Jell, P.A. & Adrain, J.M. (2002) Available generic names for trilobites.')
    """)

    # SCODA metadata
    cursor.executescript("""
        INSERT INTO artifact_metadata (key, value) VALUES ('artifact_id', 'trilobase');
        INSERT INTO artifact_metadata (key, value) VALUES ('name', 'Trilobase');
        INSERT INTO artifact_metadata (key, value) VALUES ('version', '1.0.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('schema_version', '1.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('description', 'Trilobite genus-level taxonomy database');
        INSERT INTO artifact_metadata (key, value) VALUES ('license', 'CC-BY-4.0');
    """)

    # SCODA provenance
    cursor.executescript("""
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (1, 'primary', 'Jell & Adrain (2002)', 'Primary source for genus-level taxonomy', 2002);
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (2, 'supplementary', 'Adrain (2011)', 'Suprafamilial classification', 2011);
    """)

    # SCODA schema descriptions (sample)
    cursor.executescript("""
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('taxonomic_ranks', NULL, 'Unified taxonomic hierarchy from Class to Genus');
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('taxonomic_ranks', 'rank', 'Taxonomic rank: Class, Order, Suborder, Superfamily, Family, or Genus');
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('synonyms', NULL, 'Taxonomic synonym relationships');
    """)

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def client(test_db, monkeypatch):
    """Create Flask test client with test database."""
    import app as app_module
    monkeypatch.setattr(app_module, 'DATABASE', test_db)
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# --- Index page ---

class TestIndex:
    def test_index_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200


# --- /api/tree ---

class TestApiTree:
    def test_tree_returns_200(self, client):
        response = client.get('/api/tree')
        assert response.status_code == 200

    def test_tree_root_is_class(self, client):
        response = client.get('/api/tree')
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['name'] == 'Trilobita'
        assert data[0]['rank'] == 'Class'

    def test_tree_has_orders(self, client):
        response = client.get('/api/tree')
        data = json.loads(response.data)
        children = data[0]['children']
        names = [c['name'] for c in children]
        assert 'Phacopida' in names
        assert 'Ptychopariida' in names

    def test_tree_has_families_under_orders(self, client):
        response = client.get('/api/tree')
        data = json.loads(response.data)
        phacopida = next(c for c in data[0]['children'] if c['name'] == 'Phacopida')
        family_names = [f['name'] for f in phacopida['children']]
        assert 'Phacopidae' in family_names

    def test_tree_excludes_genera(self, client):
        """Tree should only go down to Family level, not Genus."""
        response = client.get('/api/tree')
        data = json.loads(response.data)
        phacopida = next(c for c in data[0]['children'] if c['name'] == 'Phacopida')
        phacopidae = next(f for f in phacopida['children'] if f['name'] == 'Phacopidae')
        # Family children should be empty (no genera in tree)
        assert phacopidae['children'] == []

    def test_tree_node_structure(self, client):
        response = client.get('/api/tree')
        data = json.loads(response.data)
        node = data[0]
        assert 'id' in node
        assert 'name' in node
        assert 'rank' in node
        assert 'author' in node
        assert 'genera_count' in node
        assert 'children' in node

    def test_tree_genera_count(self, client):
        response = client.get('/api/tree')
        data = json.loads(response.data)
        assert data[0]['genera_count'] == 5113


# --- /api/family/<id>/genera ---

class TestApiFamilyGenera:
    def test_family_genera_returns_200(self, client):
        response = client.get('/api/family/10/genera')
        assert response.status_code == 200

    def test_family_genera_returns_family_info(self, client):
        response = client.get('/api/family/10/genera')
        data = json.loads(response.data)
        assert data['family']['name'] == 'Phacopidae'
        assert data['family']['id'] == 10

    def test_family_genera_lists_genera(self, client):
        response = client.get('/api/family/10/genera')
        data = json.loads(response.data)
        names = [g['name'] for g in data['genera']]
        assert 'Phacops' in names
        assert 'Acuticryphops' in names
        assert 'Cryphops' in names  # invalid genus is also listed

    def test_family_genera_sorted_by_name(self, client):
        response = client.get('/api/family/10/genera')
        data = json.loads(response.data)
        names = [g['name'] for g in data['genera']]
        assert names == sorted(names)

    def test_family_genera_includes_validity(self, client):
        response = client.get('/api/family/10/genera')
        data = json.loads(response.data)
        cryphops = next(g for g in data['genera'] if g['name'] == 'Cryphops')
        assert cryphops['is_valid'] == 0
        phacops = next(g for g in data['genera'] if g['name'] == 'Phacops')
        assert phacops['is_valid'] == 1

    def test_family_genera_genus_structure(self, client):
        response = client.get('/api/family/10/genera')
        data = json.loads(response.data)
        genus = data['genera'][0]
        assert 'id' in genus
        assert 'name' in genus
        assert 'author' in genus
        assert 'year' in genus
        assert 'type_species' in genus
        assert 'location' in genus
        assert 'is_valid' in genus

    def test_family_not_found(self, client):
        response = client.get('/api/family/9999/genera')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_non_family_rank_returns_404(self, client):
        """Requesting genera for an Order id should return 404."""
        response = client.get('/api/family/2/genera')  # id 2 is an Order
        assert response.status_code == 404


# --- /api/rank/<id> ---

class TestApiRankDetail:
    def test_rank_detail_class(self, client):
        response = client.get('/api/rank/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Trilobita'
        assert data['rank'] == 'Class'
        assert data['parent_name'] is None

    def test_rank_detail_order(self, client):
        response = client.get('/api/rank/2')
        data = json.loads(response.data)
        assert data['name'] == 'Phacopida'
        assert data['rank'] == 'Order'
        assert data['parent_name'] == 'Trilobita'
        assert data['parent_rank'] == 'Class'

    def test_rank_detail_family(self, client):
        response = client.get('/api/rank/10')
        data = json.loads(response.data)
        assert data['name'] == 'Phacopidae'
        assert data['rank'] == 'Family'
        assert data['parent_name'] == 'Phacopida'

    def test_rank_detail_children_counts(self, client):
        """Class should show counts of child Orders."""
        response = client.get('/api/rank/1')
        data = json.loads(response.data)
        counts = {c['rank']: c['count'] for c in data['children_counts']}
        assert counts.get('Order') == 2

    def test_rank_detail_children_list(self, client):
        response = client.get('/api/rank/1')
        data = json.loads(response.data)
        child_names = [c['name'] for c in data['children']]
        assert 'Phacopida' in child_names
        assert 'Ptychopariida' in child_names

    def test_rank_detail_not_found(self, client):
        response = client.get('/api/rank/9999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_rank_detail_response_structure(self, client):
        response = client.get('/api/rank/2')
        data = json.loads(response.data)
        expected_keys = ['id', 'name', 'rank', 'author', 'year', 'genera_count',
                         'notes', 'parent_name', 'parent_rank',
                         'children_counts', 'children']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def test_family_children_counts_include_genera(self, client):
        """Family should show Genus count in children_counts."""
        response = client.get('/api/rank/10')
        data = json.loads(response.data)
        counts = {c['rank']: c['count'] for c in data['children_counts']}
        assert counts.get('Genus') == 3  # Phacops, Acuticryphops, Cryphops


# --- /api/genus/<id> ---

class TestApiGenusDetail:
    def test_genus_detail_valid(self, client):
        response = client.get('/api/genus/100')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Phacops'
        assert data['author'] == 'EMMRICH'
        assert data['year'] == '1839'
        assert data['is_valid'] == 1

    def test_genus_detail_family_name(self, client):
        response = client.get('/api/genus/100')
        data = json.loads(response.data)
        assert data['family_name'] == 'Phacopidae'
        assert data['family'] == 'Phacopidae'

    def test_genus_detail_invalid_genus(self, client):
        response = client.get('/api/genus/102')
        data = json.loads(response.data)
        assert data['name'] == 'Cryphops'
        assert data['is_valid'] == 0

    def test_genus_detail_synonyms(self, client):
        """Cryphops should have a synonym record pointing to Acuticryphops."""
        response = client.get('/api/genus/102')
        data = json.loads(response.data)
        assert len(data['synonyms']) == 1
        syn = data['synonyms'][0]
        assert syn['senior_name'] == 'Acuticryphops'
        assert syn['synonym_type'] == 'j.s.s.'
        assert syn['fide_author'] == 'CLARKSON'

    def test_genus_detail_no_synonyms(self, client):
        response = client.get('/api/genus/100')
        data = json.loads(response.data)
        assert data['synonyms'] == []

    def test_genus_detail_formations(self, client):
        response = client.get('/api/genus/101')
        data = json.loads(response.data)
        assert len(data['formations']) == 1
        assert data['formations'][0]['name'] == 'Büdesheimer Sh'

    def test_genus_detail_locations(self, client):
        response = client.get('/api/genus/101')
        data = json.loads(response.data)
        assert len(data['locations']) == 1
        assert data['locations'][0]['country'] == 'Germany'
        assert data['locations'][0]['region'] == 'Eifel'

    def test_genus_detail_no_formations(self, client):
        """Genus without formation relations should return empty list."""
        response = client.get('/api/genus/100')
        data = json.loads(response.data)
        assert data['formations'] == []

    def test_genus_detail_not_found(self, client):
        response = client.get('/api/genus/9999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_genus_detail_non_genus_rank(self, client):
        """Requesting genus detail for a Family id should return 404."""
        response = client.get('/api/genus/10')  # id 10 is Family
        assert response.status_code == 404

    def test_genus_detail_response_structure(self, client):
        response = client.get('/api/genus/100')
        data = json.loads(response.data)
        expected_keys = ['id', 'name', 'author', 'year', 'year_suffix',
                         'type_species', 'type_species_author',
                         'formation', 'location', 'family', 'family_name',
                         'temporal_code', 'is_valid', 'notes', 'raw_entry',
                         'synonyms', 'formations', 'locations']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def test_genus_detail_synonym_structure(self, client):
        response = client.get('/api/genus/102')
        data = json.loads(response.data)
        syn = data['synonyms'][0]
        expected_keys = ['id', 'senior_taxon_id', 'senior_name',
                         'synonym_type', 'fide_author', 'fide_year']
        for key in expected_keys:
            assert key in data['synonyms'][0], f"Missing synonym key: {key}"

    def test_genus_detail_olenus(self, client):
        """Test genus from a different family."""
        response = client.get('/api/genus/200')
        data = json.loads(response.data)
        assert data['name'] == 'Olenus'
        assert data['family_name'] == 'Olenidae'
        assert len(data['formations']) == 1
        assert data['formations'][0]['name'] == 'Alum Sh'
        assert len(data['locations']) == 1
        assert data['locations'][0]['country'] == 'Sweden'


# --- /api/metadata ---

class TestApiMetadata:
    def test_metadata_returns_200(self, client):
        response = client.get('/api/metadata')
        assert response.status_code == 200

    def test_metadata_has_identity(self, client):
        response = client.get('/api/metadata')
        data = json.loads(response.data)
        assert data['artifact_id'] == 'trilobase'
        assert data['name'] == 'Trilobase'
        assert data['version'] == '1.0.0'
        assert data['schema_version'] == '1.0'

    def test_metadata_has_license(self, client):
        response = client.get('/api/metadata')
        data = json.loads(response.data)
        assert data['license'] == 'CC-BY-4.0'

    def test_metadata_has_statistics(self, client):
        response = client.get('/api/metadata')
        data = json.loads(response.data)
        stats = data['statistics']
        assert 'genus' in stats
        assert 'family' in stats
        assert 'order' in stats
        assert 'valid_genera' in stats
        assert 'synonyms' in stats
        assert 'bibliography' in stats
        assert 'formations' in stats
        assert 'countries' in stats

    def test_metadata_statistics_values(self, client):
        """Statistics should reflect test data counts."""
        response = client.get('/api/metadata')
        data = json.loads(response.data)
        stats = data['statistics']
        assert stats['genus'] == 4       # Phacops, Acuticryphops, Cryphops, Olenus
        assert stats['family'] == 2      # Phacopidae, Olenidae
        assert stats['order'] == 2       # Phacopida, Ptychopariida
        assert stats['valid_genera'] == 3  # Phacops, Acuticryphops, Olenus
        assert stats['synonyms'] == 1
        assert stats['bibliography'] == 1
        assert stats['formations'] == 2
        assert stats['countries'] == 2


# --- /api/provenance ---

class TestApiProvenance:
    def test_provenance_returns_200(self, client):
        response = client.get('/api/provenance')
        assert response.status_code == 200

    def test_provenance_returns_list(self, client):
        response = client.get('/api/provenance')
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_provenance_has_primary_source(self, client):
        response = client.get('/api/provenance')
        data = json.loads(response.data)
        primary = next(s for s in data if s['source_type'] == 'primary')
        assert 'Jell' in primary['citation']
        assert primary['year'] == 2002

    def test_provenance_has_supplementary_source(self, client):
        response = client.get('/api/provenance')
        data = json.loads(response.data)
        supp = next(s for s in data if s['source_type'] == 'supplementary')
        assert 'Adrain' in supp['citation']
        assert supp['year'] == 2011

    def test_provenance_record_structure(self, client):
        response = client.get('/api/provenance')
        data = json.loads(response.data)
        record = data[0]
        expected_keys = ['id', 'source_type', 'citation', 'description', 'year', 'url']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"
