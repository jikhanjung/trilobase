"""
Tests for Trilobase Flask application (app.py)
"""

import json
import sqlite3
import os
import stat
import sys
import tempfile
import zipfile

import pytest

import scoda_package
from app import app
from scoda_package import get_db, ScodaPackage

# Import release script functions
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from release import (
    get_version, calculate_sha256, store_sha256, get_statistics,
    get_provenance, build_metadata_json, generate_readme, create_release
)


@pytest.fixture
def test_db(tmp_path):
    """Create temporary test databases (canonical + overlay) with sample data."""
    canonical_db_path = str(tmp_path / "test_trilobase.db")
    overlay_db_path = str(tmp_path / "test_overlay.db")

    # Create CANONICAL database
    conn = sqlite3.connect(canonical_db_path)
    cursor = conn.cursor()

    # Create tables (canonical only - NO user_annotations)
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
            region_id INTEGER,
            is_type_locality INTEGER DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genus_id) REFERENCES taxonomic_ranks(id),
            FOREIGN KEY (country_id) REFERENCES countries(id),
            UNIQUE(genus_id, country_id, region)
        );

        CREATE TABLE geographic_regions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            parent_id INTEGER,
            cow_ccode INTEGER,
            taxa_count INTEGER DEFAULT 0,
            FOREIGN KEY (parent_id) REFERENCES geographic_regions(id)
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

        -- SCODA UI tables (Phase 14)
        CREATE TABLE ui_display_intent (
            id INTEGER PRIMARY KEY,
            entity TEXT NOT NULL,
            default_view TEXT NOT NULL,
            description TEXT,
            source_query TEXT,
            priority INTEGER DEFAULT 0
        );

        CREATE TABLE ui_queries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            sql TEXT NOT NULL,
            params_json TEXT,
            created_at TEXT NOT NULL
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

    # Geographic regions
    cursor.executescript("""
        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count)
        VALUES (1, 'Germany', 'country', NULL, 255, 150);
        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count)
        VALUES (2, 'Sweden', 'country', NULL, 380, 80);
        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count)
        VALUES (3, 'Eifel', 'region', 1, NULL, 5);
        INSERT INTO geographic_regions (id, name, level, parent_id, cow_ccode, taxa_count)
        VALUES (4, 'Scania', 'region', 2, NULL, 20);
    """)

    # Genus-Location relations (with region_id)
    cursor.executescript("""
        INSERT INTO genus_locations (genus_id, country_id, region, region_id) VALUES (101, 1, 'Eifel', 3);
        INSERT INTO genus_locations (genus_id, country_id, region, region_id) VALUES (200, 2, 'Scania', 4);
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

    # SCODA display intents (Phase 14)
    cursor.executescript("""
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (1, 'genera', 'tree', 'Taxonomic hierarchy is primary structure', 'taxonomy_tree', 0);
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (2, 'genera', 'table', 'Flat listing for search/filtering', 'genera_list', 1);
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (3, 'references', 'table', 'Literature references sorted by year', 'bibliography_list', 0);
    """)

    # SCODA saved queries (Phase 14)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genera_list', 'Flat list of all genera',
                'SELECT id, name, author, year, family, is_valid FROM taxonomic_ranks WHERE rank = ''Genus'' ORDER BY name',
                NULL, '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('family_genera', 'Genera in a specific family',
                'SELECT id, name, author, year, is_valid FROM taxonomic_ranks WHERE parent_id = :family_id AND rank = ''Genus'' ORDER BY name',
                '{"family_id": "integer"}', '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('taxonomy_tree', 'Tree from Class to Family',
                'SELECT id, name, rank, parent_id, author FROM taxonomic_ranks WHERE rank != ''Genus'' ORDER BY name',
                NULL, '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('bibliography_list', 'All literature references',
                'SELECT id, authors, year, title, journal, reference_type FROM bibliography ORDER BY authors',
                NULL, '2026-02-07T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('genus_detail', 'Full detail for a single genus',
                'SELECT tr.*, parent.name as family_name FROM taxonomic_ranks tr LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id WHERE tr.id = :genus_id AND tr.rank = ''Genus''',
                '{"genus_id": "integer"}', '2026-02-07T00:00:00')
    """)

    # SCODA UI Manifest (Phase 15)
    cursor.execute("""
        CREATE TABLE ui_manifest (
            name TEXT PRIMARY KEY,
            description TEXT,
            manifest_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    import json as _json
    test_manifest = {
        "default_view": "taxonomy_tree",
        "views": {
            "taxonomy_tree": {
                "type": "tree",
                "title": "Taxonomy Tree",
                "description": "Hierarchical classification from Class to Family",
                "source_query": "taxonomy_tree",
                "icon": "bi-diagram-3",
                "options": {
                    "root_rank": "Class",
                    "leaf_rank": "Family",
                    "show_genera_count": True
                }
            },
            "genera_table": {
                "type": "table",
                "title": "All Genera",
                "description": "Flat list of all trilobite genera",
                "source_query": "genera_list",
                "icon": "bi-table",
                "columns": [
                    {"key": "name", "label": "Genus", "sortable": True, "searchable": True, "italic": True},
                    {"key": "author", "label": "Author", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "family", "label": "Family", "sortable": True, "searchable": True},
                    {"key": "is_valid", "label": "Valid", "sortable": True, "searchable": False, "type": "boolean"}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
            },
            "genus_detail": {
                "type": "detail",
                "title": "Genus Detail",
                "description": "Detailed information for a single genus",
                "source_query": "genus_detail",
                "sections": [
                    {
                        "title": "Basic Information",
                        "fields": [
                            {"key": "name", "label": "Name"}
                        ]
                    }
                ]
            },
            "references_table": {
                "type": "table",
                "title": "Bibliography",
                "description": "Literature references",
                "source_query": "bibliography_list",
                "icon": "bi-book",
                "columns": [
                    {"key": "authors", "label": "Authors", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "title", "label": "Title", "sortable": False, "searchable": True}
                ],
                "default_sort": {"key": "authors", "direction": "asc"},
                "searchable": True
            }
        }
    }
    cursor.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?, ?, ?, ?)",
        ('default', 'Test manifest', _json.dumps(test_manifest), '2026-02-07T00:00:00')
    )

    conn.commit()
    conn.close()

    # Create OVERLAY database using init_overlay_db script
    from init_overlay_db import create_overlay_db
    create_overlay_db(overlay_db_path, canonical_version='1.0.0')

    return canonical_db_path, overlay_db_path


@pytest.fixture
def client(test_db):
    """Create Flask test client with test databases (canonical + overlay)."""
    canonical_db_path, overlay_db_path = test_db
    scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
    scoda_package._reset_paths()


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
        assert data['locations'][0]['country_name'] == 'Germany'
        assert data['locations'][0]['region_name'] == 'Eifel'
        assert data['locations'][0]['country_id'] == 1
        assert data['locations'][0]['region_id'] == 3

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
        assert data['locations'][0]['country_name'] == 'Sweden'


# --- /api/country/<id> ---

class TestApiCountryDetail:
    def test_country_detail_valid(self, client):
        response = client.get('/api/country/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Germany'
        assert data['cow_ccode'] == 255

    def test_country_detail_has_regions(self, client):
        response = client.get('/api/country/1')
        data = json.loads(response.data)
        assert len(data['regions']) == 1
        assert data['regions'][0]['name'] == 'Eifel'

    def test_country_detail_has_genera(self, client):
        response = client.get('/api/country/1')
        data = json.loads(response.data)
        assert len(data['genera']) >= 1
        names = [g['name'] for g in data['genera']]
        assert 'Acuticryphops' in names

    def test_country_detail_not_found(self, client):
        response = client.get('/api/country/9999')
        assert response.status_code == 404

    def test_country_detail_region_is_not_country(self, client):
        """A region id should return 404 for country endpoint."""
        response = client.get('/api/country/3')  # id 3 is Eifel (region)
        assert response.status_code == 404


# --- /api/region/<id> ---

class TestApiRegionDetail:
    def test_region_detail_valid(self, client):
        response = client.get('/api/region/3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Eifel'
        assert data['parent']['name'] == 'Germany'
        assert data['parent']['id'] == 1

    def test_region_detail_has_genera(self, client):
        response = client.get('/api/region/3')
        data = json.loads(response.data)
        assert len(data['genera']) >= 1
        names = [g['name'] for g in data['genera']]
        assert 'Acuticryphops' in names

    def test_region_detail_not_found(self, client):
        response = client.get('/api/region/9999')
        assert response.status_code == 404

    def test_region_detail_country_is_not_region(self, client):
        """A country id should return 404 for region endpoint."""
        response = client.get('/api/region/1')  # id 1 is Germany (country)
        assert response.status_code == 404


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


# --- /api/display-intent ---

class TestApiDisplayIntent:
    def test_display_intent_returns_200(self, client):
        response = client.get('/api/display-intent')
        assert response.status_code == 200

    def test_display_intent_returns_list(self, client):
        response = client.get('/api/display-intent')
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_display_intent_primary_view(self, client):
        """genera entity should have tree as primary (priority=0) view."""
        response = client.get('/api/display-intent')
        data = json.loads(response.data)
        genera_intents = [i for i in data if i['entity'] == 'genera']
        primary = next(i for i in genera_intents if i['priority'] == 0)
        assert primary['default_view'] == 'tree'

    def test_display_intent_secondary_view(self, client):
        """genera entity should have table as secondary (priority=1) view."""
        response = client.get('/api/display-intent')
        data = json.loads(response.data)
        genera_intents = [i for i in data if i['entity'] == 'genera']
        secondary = next(i for i in genera_intents if i['priority'] == 1)
        assert secondary['default_view'] == 'table'

    def test_display_intent_source_query(self, client):
        response = client.get('/api/display-intent')
        data = json.loads(response.data)
        tree_intent = next(i for i in data if i['default_view'] == 'tree')
        assert tree_intent['source_query'] == 'taxonomy_tree'

    def test_display_intent_record_structure(self, client):
        response = client.get('/api/display-intent')
        data = json.loads(response.data)
        record = data[0]
        expected_keys = ['id', 'entity', 'default_view', 'description',
                         'source_query', 'priority']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"


# --- /api/queries ---

class TestApiQueries:
    def test_queries_returns_200(self, client):
        response = client.get('/api/queries')
        assert response.status_code == 200

    def test_queries_returns_list(self, client):
        response = client.get('/api/queries')
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 5  # genera_list, family_genera, taxonomy_tree, bibliography_list, genus_detail

    def test_queries_record_structure(self, client):
        response = client.get('/api/queries')
        data = json.loads(response.data)
        record = data[0]
        expected_keys = ['id', 'name', 'description', 'params', 'created_at']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"

    def test_queries_sorted_by_name(self, client):
        response = client.get('/api/queries')
        data = json.loads(response.data)
        names = [q['name'] for q in data]
        assert names == sorted(names)


# --- /api/queries/<name>/execute ---

class TestApiQueryExecute:
    def test_execute_no_params(self, client):
        """Execute genera_list query (no parameters needed)."""
        response = client.get('/api/queries/genera_list/execute')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['query'] == 'genera_list'
        assert data['row_count'] == 4  # 4 genera in test data
        assert 'columns' in data
        assert 'rows' in data

    def test_execute_with_params(self, client):
        """Execute family_genera query with family_id parameter."""
        response = client.get('/api/queries/family_genera/execute?family_id=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['row_count'] == 3  # Phacops, Acuticryphops, Cryphops
        names = [r['name'] for r in data['rows']]
        assert 'Phacops' in names

    def test_execute_results_sorted(self, client):
        """genera_list results should be sorted by name."""
        response = client.get('/api/queries/genera_list/execute')
        data = json.loads(response.data)
        names = [r['name'] for r in data['rows']]
        assert names == sorted(names)

    def test_execute_not_found(self, client):
        response = client.get('/api/queries/nonexistent/execute')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_execute_columns_present(self, client):
        """Result should include column names."""
        response = client.get('/api/queries/genera_list/execute')
        data = json.loads(response.data)
        assert 'name' in data['columns']
        assert 'is_valid' in data['columns']

    def test_execute_row_is_dict(self, client):
        """Each row should be a dictionary with column keys."""
        response = client.get('/api/queries/genera_list/execute')
        data = json.loads(response.data)
        row = data['rows'][0]
        assert isinstance(row, dict)
        assert 'name' in row


# --- /api/manifest ---

class TestApiManifest:
    def test_manifest_returns_200(self, client):
        response = client.get('/api/manifest')
        assert response.status_code == 200

    def test_manifest_returns_json(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_manifest_has_name(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert data['name'] == 'default'

    def test_manifest_has_description(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert data['description'] == 'Test manifest'

    def test_manifest_has_created_at(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert 'created_at' in data
        assert data['created_at'] == '2026-02-07T00:00:00'

    def test_manifest_has_manifest_object(self, client):
        """manifest_json should be parsed as an object, not returned as string."""
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert 'manifest' in data
        assert isinstance(data['manifest'], dict)

    def test_manifest_has_default_view(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert data['manifest']['default_view'] == 'taxonomy_tree'

    def test_manifest_has_views(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert 'views' in data['manifest']
        assert isinstance(data['manifest']['views'], dict)

    def test_manifest_view_count(self, client):
        """Test manifest should have 4 views."""
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert len(data['manifest']['views']) == 4

    def test_manifest_tree_view(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        tree = data['manifest']['views']['taxonomy_tree']
        assert tree['type'] == 'tree'
        assert tree['source_query'] == 'taxonomy_tree'

    def test_manifest_table_view(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        table = data['manifest']['views']['genera_table']
        assert table['type'] == 'table'
        assert table['source_query'] == 'genera_list'

    def test_manifest_detail_view(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        detail = data['manifest']['views']['genus_detail']
        assert detail['type'] == 'detail'

    def test_manifest_table_columns(self, client):
        """Table views should have column definitions."""
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        table = data['manifest']['views']['genera_table']
        assert 'columns' in table
        assert isinstance(table['columns'], list)
        assert len(table['columns']) > 0
        col = table['columns'][0]
        assert 'key' in col
        assert 'label' in col

    def test_manifest_table_default_sort(self, client):
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        table = data['manifest']['views']['genera_table']
        assert 'default_sort' in table
        assert table['default_sort']['key'] == 'name'
        assert table['default_sort']['direction'] == 'asc'

    def test_manifest_source_query_exists(self, client):
        """source_query references should point to actual ui_queries entries."""
        response = client.get('/api/manifest')
        data = json.loads(response.data)

        queries_response = client.get('/api/queries')
        queries_data = json.loads(queries_response.data)
        query_names = {q['name'] for q in queries_data}

        for key, view in data['manifest']['views'].items():
            sq = view.get('source_query')
            if sq:
                assert sq in query_names, f"View '{key}' references query '{sq}' which doesn't exist"

    def test_manifest_response_structure(self, client):
        """Top-level response should have exactly these keys."""
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        expected_keys = ['name', 'description', 'manifest', 'created_at']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"


# --- Release Mechanism (Phase 16) ---

class TestRelease:
    def test_get_version(self, test_db):
        """get_version should return '1.0.0' from test DB."""
        canonical_db, _ = test_db
        assert get_version(canonical_db) == '1.0.0'

    def test_get_version_missing(self, tmp_path):
        """get_version should raise SystemExit when no version key exists."""
        db_path = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE artifact_metadata (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()
        with pytest.raises(SystemExit):
            get_version(db_path)

    def test_calculate_sha256(self, test_db):
        """calculate_sha256 should return a 64-char hex string."""
        canonical_db, _ = test_db
        h = calculate_sha256(canonical_db)
        assert len(h) == 64
        assert all(c in '0123456789abcdef' for c in h)

    def test_calculate_sha256_deterministic(self, test_db):
        """Same file should always produce the same hash."""
        canonical_db, _ = test_db
        h1 = calculate_sha256(canonical_db)
        h2 = calculate_sha256(canonical_db)
        assert h1 == h2

    def test_calculate_sha256_changes(self, test_db):
        """Modifying the DB should change the hash."""
        canonical_db, _ = test_db
        h_before = calculate_sha256(canonical_db)
        conn = sqlite3.connect(canonical_db)
        conn.execute("INSERT INTO artifact_metadata (key, value) VALUES ('test_key', 'test_value')")
        conn.commit()
        conn.close()
        h_after = calculate_sha256(canonical_db)
        assert h_before != h_after

    def test_store_sha256(self, test_db):
        """store_sha256 should insert/update sha256 key in artifact_metadata."""
        canonical_db, _ = test_db
        store_sha256(canonical_db, 'abc123def456')
        conn = sqlite3.connect(canonical_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM artifact_metadata WHERE key = 'sha256'"
        ).fetchone()
        conn.close()
        assert row['value'] == 'abc123def456'

    def test_get_statistics(self, test_db):
        """get_statistics should return correct counts for test data."""
        canonical_db, _ = test_db
        stats = get_statistics(canonical_db)
        assert stats['genera'] == 4         # Phacops, Acuticryphops, Cryphops, Olenus
        assert stats['valid_genera'] == 3   # Phacops, Acuticryphops, Olenus
        assert stats['family'] == 2         # Phacopidae, Olenidae
        assert stats['order'] == 2          # Phacopida, Ptychopariida
        assert stats['synonyms'] == 1
        assert stats['bibliography'] == 1
        assert stats['formations'] == 2
        assert stats['countries'] == 2

    def test_get_provenance(self, test_db):
        """get_provenance should return 2 records with correct structure."""
        canonical_db, _ = test_db
        prov = get_provenance(canonical_db)
        assert len(prov) == 2
        assert prov[0]['source_type'] == 'primary'
        assert 'Jell' in prov[0]['citation']
        assert prov[1]['source_type'] == 'supplementary'
        for record in prov:
            assert 'id' in record
            assert 'citation' in record
            assert 'description' in record
            assert 'year' in record

    def test_build_metadata_json(self, test_db):
        """build_metadata_json should include all required keys."""
        canonical_db, _ = test_db
        meta = build_metadata_json(canonical_db, 'fakehash123')
        assert meta['artifact_id'] == 'trilobase'
        assert meta['version'] == '1.0.0'
        assert meta['sha256'] == 'fakehash123'
        assert 'released_at' in meta
        assert 'provenance' in meta
        assert isinstance(meta['provenance'], list)
        assert len(meta['provenance']) == 2
        assert 'statistics' in meta
        assert isinstance(meta['statistics'], dict)
        assert meta['statistics']['genera'] == 4

    def test_generate_readme(self, test_db):
        """generate_readme should include version, hash, and statistics."""
        canonical_db, _ = test_db
        stats = get_statistics(canonical_db)
        readme = generate_readme('1.0.0', 'abc123hash', stats)
        assert '1.0.0' in readme
        assert 'abc123hash' in readme
        assert 'Genera: 4' in readme
        assert 'Valid genera: 3' in readme
        assert 'sha256sum --check' in readme

    def test_create_release(self, test_db, tmp_path):
        """Integration: create_release should produce directory with 4 files."""
        canonical_db, _ = test_db
        output_dir = str(tmp_path / "releases")
        release_dir = create_release(canonical_db, output_dir)

        # Directory exists
        assert os.path.isdir(release_dir)
        assert 'trilobase-v1.0.0' in release_dir

        # 4 files exist
        assert os.path.isfile(os.path.join(release_dir, 'trilobase.db'))
        assert os.path.isfile(os.path.join(release_dir, 'metadata.json'))
        assert os.path.isfile(os.path.join(release_dir, 'checksums.sha256'))
        assert os.path.isfile(os.path.join(release_dir, 'README.md'))

        # DB is read-only
        db_stat = os.stat(os.path.join(release_dir, 'trilobase.db'))
        assert not (db_stat.st_mode & stat.S_IWUSR)
        assert not (db_stat.st_mode & stat.S_IWGRP)
        assert not (db_stat.st_mode & stat.S_IWOTH)

        # metadata.json is valid JSON with required keys
        with open(os.path.join(release_dir, 'metadata.json')) as f:
            meta = json.load(f)
        assert meta['version'] == '1.0.0'
        assert meta['artifact_id'] == 'trilobase'
        assert len(meta['sha256']) == 64

        # checksums.sha256 matches actual DB hash
        with open(os.path.join(release_dir, 'checksums.sha256')) as f:
            checksum_line = f.read().strip()
        recorded_hash = checksum_line.split('  ')[0]
        actual_hash = calculate_sha256(os.path.join(release_dir, 'trilobase.db'))
        assert recorded_hash == actual_hash

        # sha256 stored in source DB
        conn = sqlite3.connect(canonical_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM artifact_metadata WHERE key = 'sha256'"
        ).fetchone()
        conn.close()
        assert row['value'] == actual_hash

    def test_create_release_already_exists(self, test_db, tmp_path):
        """Attempting to create a duplicate release should fail."""
        canonical_db, _ = test_db
        output_dir = str(tmp_path / "releases")
        create_release(canonical_db, output_dir)
        with pytest.raises(SystemExit):
            create_release(canonical_db, output_dir)


# --- /api/annotations --- (Phase 17)

class TestAnnotations:
    def test_get_annotations_empty(self, client):
        """Entity with no annotations should return empty list."""
        response = client.get('/api/annotations/genus/100')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_create_annotation(self, client):
        """POST should create annotation and return 201."""
        response = client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'genus',
                'entity_id': 100,
                'annotation_type': 'note',
                'content': 'This genus needs revision.',
                'author': 'Test User'
            }),
            content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['entity_type'] == 'genus'
        assert data['entity_id'] == 100
        assert data['annotation_type'] == 'note'
        assert data['content'] == 'This genus needs revision.'
        assert data['author'] == 'Test User'

    def test_create_annotation_missing_content(self, client):
        """POST without content should return 400."""
        response = client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'genus',
                'entity_id': 100,
                'annotation_type': 'note'
            }),
            content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_annotation_invalid_type(self, client):
        """POST with invalid annotation_type should return 400."""
        response = client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'genus',
                'entity_id': 100,
                'annotation_type': 'invalid_type',
                'content': 'Test'
            }),
            content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_create_annotation_invalid_entity(self, client):
        """POST with invalid entity_type should return 400."""
        response = client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'invalid_entity',
                'entity_id': 100,
                'annotation_type': 'note',
                'content': 'Test'
            }),
            content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_get_annotations_after_create(self, client):
        """GET after POST should return the created annotation."""
        client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'genus',
                'entity_id': 100,
                'annotation_type': 'note',
                'content': 'Test note'
            }),
            content_type='application/json')

        response = client.get('/api/annotations/genus/100')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['content'] == 'Test note'

    def test_delete_annotation(self, client):
        """DELETE should remove annotation and return 200."""
        create_resp = client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'genus',
                'entity_id': 100,
                'annotation_type': 'note',
                'content': 'To be deleted'
            }),
            content_type='application/json')
        annotation_id = json.loads(create_resp.data)['id']

        response = client.delete(f'/api/annotations/{annotation_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == annotation_id

        # Verify it's gone
        get_resp = client.get('/api/annotations/genus/100')
        assert json.loads(get_resp.data) == []

    def test_delete_annotation_not_found(self, client):
        """DELETE for non-existent ID should return 404."""
        response = client.delete('/api/annotations/99999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_annotations_ordered_by_date(self, client):
        """Annotations should be returned newest first."""
        client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'genus',
                'entity_id': 100,
                'annotation_type': 'note',
                'content': 'First note'
            }),
            content_type='application/json')
        client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'genus',
                'entity_id': 100,
                'annotation_type': 'correction',
                'content': 'Second note'
            }),
            content_type='application/json')

        response = client.get('/api/annotations/genus/100')
        data = json.loads(response.data)
        assert len(data) == 2
        # Most recent first (both created in same second, so check by id desc)
        assert data[0]['content'] == 'Second note'
        assert data[1]['content'] == 'First note'

    def test_annotation_response_structure(self, client):
        """Annotation response should have all required keys."""
        client.post('/api/annotations',
            data=json.dumps({
                'entity_type': 'family',
                'entity_id': 10,
                'annotation_type': 'alternative',
                'content': 'May belong to different order',
                'author': 'Reviewer'
            }),
            content_type='application/json')

        response = client.get('/api/annotations/family/10')
        data = json.loads(response.data)
        record = data[0]
        expected_keys = ['id', 'entity_type', 'entity_id', 'annotation_type',
                         'content', 'author', 'created_at']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"


# --- ScodaPackage (Phase 25) ---

class TestScodaPackage:
    def test_create_scoda(self, test_db, tmp_path):
        """ScodaPackage.create should produce a valid .scoda ZIP."""
        canonical_db, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        result = ScodaPackage.create(canonical_db, scoda_path)
        assert os.path.exists(result)
        assert zipfile.is_zipfile(result)

    def test_scoda_contains_manifest_and_db(self, test_db, tmp_path):
        """The .scoda ZIP should contain manifest.json and data.db."""
        canonical_db, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with zipfile.ZipFile(scoda_path, 'r') as zf:
            names = zf.namelist()
            assert 'manifest.json' in names
            assert 'data.db' in names

    def test_scoda_manifest_fields(self, test_db, tmp_path):
        """Manifest should contain required metadata fields."""
        canonical_db, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            m = pkg.manifest
            assert m['format'] == 'scoda'
            assert m['format_version'] == '1.0'
            assert m['name'] == 'trilobase'
            assert m['version'] == '1.0.0'
            assert m['data_file'] == 'data.db'
            assert m['record_count'] > 0
            assert len(m['data_checksum_sha256']) == 64

    def test_scoda_open_and_read(self, test_db, tmp_path):
        """Opening a .scoda package should extract DB and allow queries."""
        canonical_db, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            conn = sqlite3.connect(pkg.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM taxonomic_ranks")
            count = cursor.fetchone()['cnt']
            conn.close()
            assert count > 0

    def test_scoda_checksum_verification(self, test_db, tmp_path):
        """verify_checksum() should return True for unmodified package."""
        canonical_db, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.verify_checksum() is True

    def test_scoda_close_cleanup(self, test_db, tmp_path):
        """close() should remove the temp directory."""
        canonical_db, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        pkg = ScodaPackage(scoda_path)
        tmp_dir = pkg._tmp_dir
        assert os.path.exists(tmp_dir)
        pkg.close()
        assert not os.path.exists(tmp_dir)

    def test_scoda_properties(self, test_db, tmp_path):
        """Package properties should match manifest."""
        canonical_db, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.version == '1.0.0'
            assert pkg.name == 'trilobase'
            assert pkg.record_count > 0

    def test_scoda_file_not_found(self, tmp_path):
        """Opening a nonexistent .scoda should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ScodaPackage(str(tmp_path / "nonexistent.scoda"))

    def test_get_db_with_testing_paths(self, test_db):
        """get_db() with _set_paths_for_testing should work correctly."""
        canonical_db, overlay_db = test_db
        scoda_package._set_paths_for_testing(canonical_db, overlay_db)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM taxonomic_ranks")
            count = cursor.fetchone()['cnt']
            conn.close()
            assert count > 0
        finally:
            scoda_package._reset_paths()

    def test_get_db_overlay_attached(self, test_db):
        """get_db() should have overlay DB attached."""
        canonical_db, overlay_db = test_db
        scoda_package._set_paths_for_testing(canonical_db, overlay_db)
        try:
            conn = get_db()
            cursor = conn.cursor()
            # overlay.user_annotations should be accessible
            cursor.execute("SELECT COUNT(*) as cnt FROM overlay.user_annotations")
            count = cursor.fetchone()['cnt']
            conn.close()
            assert count == 0  # empty initially
        finally:
            scoda_package._reset_paths()
