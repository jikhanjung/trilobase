"""
Tests for Trilobase domain-specific functionality (taxonomy, geography, stratigraphy).
"""

import json
import sqlite3
import os
import sys
import tempfile
import zipfile

import pytest

import scoda_desktop.scoda_package as scoda_package
from scoda_desktop.app import app
from scoda_desktop.scoda_package import get_db, ScodaPackage




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




# --- Declarative Manifest Detail Views (Phase 39) ---

class TestManifestDetailSchema:
    """Tests for manifest detail view schema (Phase 39)."""

    def _get_manifest(self, client):
        response = client.get('/api/manifest')
        return json.loads(response.data)['manifest']

    def _detail_views(self, client):
        m = self._get_manifest(client)
        return {k: v for k, v in m['views'].items() if v['type'] == 'detail'}

    def _table_views(self, client):
        m = self._get_manifest(client)
        return {k: v for k, v in m['views'].items() if v['type'] == 'table'}

    def test_detail_view_count(self, client):
        """Should have 7 detail views."""
        assert len(self._detail_views(client)) == 7

    def test_detail_views_have_source(self, client):
        """All detail views should have source with {id} placeholder."""
        for key, view in self._detail_views(client).items():
            assert 'source' in view, f"{key} missing source"
            assert '{id}' in view['source'], f"{key} source missing {{id}}"

    def test_detail_views_have_title_template(self, client):
        """All detail views should have title_template."""
        for key, view in self._detail_views(client).items():
            assert 'title_template' in view, f"{key} missing title_template"
            assert 'format' in view['title_template'], f"{key} title_template missing format"

    def test_detail_views_have_sections(self, client):
        """All detail views should have non-empty sections."""
        for key, view in self._detail_views(client).items():
            assert 'sections' in view, f"{key} missing sections"
            assert len(view['sections']) > 0, f"{key} has empty sections"

    def test_detail_sections_have_type(self, client):
        """Every section should have a type field."""
        for key, view in self._detail_views(client).items():
            for i, section in enumerate(view['sections']):
                assert 'type' in section, f"{key} section[{i}] missing type"

    def test_field_grid_sections_have_fields(self, client):
        """field_grid sections should have fields array."""
        for key, view in self._detail_views(client).items():
            for section in view['sections']:
                if section['type'] == 'field_grid':
                    assert 'fields' in section, f"{key} field_grid missing fields"
                    assert len(section['fields']) > 0

    def test_linked_table_sections_have_columns(self, client):
        """linked_table sections should have columns and data_key."""
        for key, view in self._detail_views(client).items():
            for section in view['sections']:
                if section['type'] == 'linked_table':
                    assert 'columns' in section, f"{key} linked_table missing columns"
                    assert 'data_key' in section, f"{key} linked_table missing data_key"

    def test_table_views_have_on_row_click(self, client):
        """All table views should have on_row_click."""
        for key, view in self._table_views(client).items():
            assert 'on_row_click' in view, f"{key} missing on_row_click"
            rc = view['on_row_click']
            assert 'detail_view' in rc, f"{key} on_row_click missing detail_view"
            assert 'id_key' in rc, f"{key} on_row_click missing id_key"

    def test_on_row_click_references_existing_detail(self, client):
        """on_row_click detail_view should reference an existing view."""
        m = self._get_manifest(client)
        for key, view in self._table_views(client).items():
            target = view['on_row_click']['detail_view']
            assert target in m['views'], f"{key} references non-existent view {target}"

    def test_genus_detail_has_all_section_types(self, client):
        """genus_detail should cover multiple section types."""
        m = self._get_manifest(client)
        genus = m['views']['genus_detail']
        types = {s['type'] for s in genus['sections']}
        assert 'field_grid' in types
        assert 'genus_geography' in types
        assert 'annotations' in types

    def test_rank_detail_has_rank_children(self, client):
        """rank_detail should have rank_children section."""
        m = self._get_manifest(client)
        rank = m['views']['rank_detail']
        types = {s['type'] for s in rank['sections']}
        assert 'rank_children' in types
        assert 'rank_statistics' in types

    def test_chronostrat_detail_has_tagged_list(self, client):
        """chronostrat_detail should have tagged_list for mapped codes."""
        m = self._get_manifest(client)
        chrono = m['views'].get('chronostrat_detail')
        if chrono:
            types = {s['type'] for s in chrono['sections']}
            assert 'tagged_list' in types or 'field_grid' in types

    def test_bibliography_detail_has_raw_text(self, client):
        """bibliography_detail should have raw_text section."""
        m = self._get_manifest(client)
        bib = m['views']['bibliography_detail']
        types = {s['type'] for s in bib['sections']}
        assert 'raw_text' in types

    def test_chart_view_has_chart_options(self, client):
        """chronostratigraphy_table should have chart_options."""
        m = self._get_manifest(client)
        chrono = m['views']['chronostratigraphy_table']
        assert 'chart_options' in chrono
        assert 'cell_click' in chrono['chart_options']


# --- Manifest Tree & Chart Options (Phase 41) ---




# --- Manifest Tree & Chart Options (Phase 41) ---

class TestManifestTreeChart:
    """Tests for manifest tree_options and chart_options extensions (Phase 41)."""

    def _get_manifest(self, client):
        response = client.get('/api/manifest')
        return json.loads(response.data)['manifest']

    def test_tree_view_has_tree_options(self, client):
        """taxonomy_tree should have tree_options with required keys."""
        m = self._get_manifest(client)
        tree = m['views']['taxonomy_tree']
        assert 'tree_options' in tree
        opts = tree['tree_options']
        for key in ['id_key', 'parent_key', 'label_key', 'rank_key', 'leaf_rank', 'count_key']:
            assert key in opts, f"tree_options missing key: {key}"

    def test_tree_options_item_query_exists(self, client):
        """tree_options.item_query should reference an existing named query."""
        m = self._get_manifest(client)
        opts = m['views']['taxonomy_tree']['tree_options']
        assert 'item_query' in opts
        assert 'item_param' in opts

        queries_response = client.get('/api/queries')
        query_names = {q['name'] for q in json.loads(queries_response.data)}
        assert opts['item_query'] in query_names, \
            f"item_query '{opts['item_query']}' not found in named queries"

    def test_tree_options_item_columns(self, client):
        """tree_options.item_columns should be an array of column definitions."""
        m = self._get_manifest(client)
        opts = m['views']['taxonomy_tree']['tree_options']
        assert 'item_columns' in opts
        cols = opts['item_columns']
        assert isinstance(cols, list)
        assert len(cols) > 0
        for col in cols:
            assert 'key' in col, "Each item_column must have 'key'"
            assert 'label' in col, "Each item_column must have 'label'"

    def test_tree_options_on_node_info(self, client):
        """tree_options.on_node_info should define detail view navigation."""
        m = self._get_manifest(client)
        opts = m['views']['taxonomy_tree']['tree_options']
        assert 'on_node_info' in opts
        info = opts['on_node_info']
        assert 'detail_view' in info
        assert info['detail_view'] in m['views'], \
            f"on_node_info.detail_view '{info['detail_view']}' not in manifest views"

    def test_chart_options_rank_columns(self, client):
        """chart_options.rank_columns should be an array with rank and label."""
        m = self._get_manifest(client)
        opts = m['views']['chronostratigraphy_table']['chart_options']
        assert 'rank_columns' in opts
        cols = opts['rank_columns']
        assert isinstance(cols, list)
        assert len(cols) >= 4  # At least Eon, Era, Period, Epoch
        for col in cols:
            assert 'rank' in col, "Each rank_column must have 'rank'"
            assert 'label' in col, "Each rank_column must have 'label'"

    def test_chart_options_value_column(self, client):
        """chart_options.value_column should exist with key and label."""
        m = self._get_manifest(client)
        opts = m['views']['chronostratigraphy_table']['chart_options']
        assert 'value_column' in opts
        vc = opts['value_column']
        assert 'key' in vc
        assert 'label' in vc

    def test_chart_options_skip_ranks(self, client):
        """chart_options.skip_ranks should be a list."""
        m = self._get_manifest(client)
        opts = m['views']['chronostratigraphy_table']['chart_options']
        assert 'skip_ranks' in opts
        assert isinstance(opts['skip_ranks'], list)

    def test_tree_options_no_legacy_options(self, client):
        """taxonomy_tree should not have the legacy 'options' key."""
        m = self._get_manifest(client)
        tree = m['views']['taxonomy_tree']
        assert 'options' not in tree, "Legacy 'options' key should be replaced by 'tree_options'"


# --- Release Mechanism (Phase 16) ---




# --- PaleoCore .scoda Package (Phase 35) ---

class TestPaleocoreScoda:
    """Tests for creating and using paleocore.scoda packages."""

    def _create_paleocore_db(self, tmp_path):
        """Create a minimal paleocore DB for testing."""
        pc_db = str(tmp_path / "pc_test.db")
        conn = sqlite3.connect(pc_db)
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE artifact_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT INTO artifact_metadata (key, value) VALUES ('artifact_id', 'paleocore');
            INSERT INTO artifact_metadata (key, value) VALUES ('name', 'PaleoCore');
            INSERT INTO artifact_metadata (key, value) VALUES ('version', '0.3.0');
            INSERT INTO artifact_metadata (key, value) VALUES ('schema_version', '1.0');
            INSERT INTO artifact_metadata (key, value) VALUES ('description', 'Test PaleoCore');
            INSERT INTO artifact_metadata (key, value) VALUES ('license', 'CC-BY-4.0');

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

            CREATE TABLE countries (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                code TEXT
            );
            INSERT INTO countries VALUES (1, 'Germany', 'DE');
            INSERT INTO countries VALUES (2, 'Sweden', 'SE');

            CREATE TABLE formations (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                normalized_name TEXT,
                formation_type TEXT,
                country TEXT,
                period TEXT
            );
            INSERT INTO formations VALUES (1, 'Alum Sh', 'alum sh', 'Sh', 'Sweden', 'Cambrian');
        """)
        conn.commit()
        conn.close()
        return pc_db

    def test_create_paleocore_scoda(self, tmp_path):
        """ScodaPackage.create should work with paleocore DB (no taxonomic_ranks)."""
        pc_db = self._create_paleocore_db(tmp_path)
        scoda_path = str(tmp_path / "test_paleocore.scoda")
        result = ScodaPackage.create(pc_db, scoda_path)
        assert os.path.exists(result)
        assert zipfile.is_zipfile(result)

    def test_paleocore_scoda_manifest(self, tmp_path):
        """PaleoCore .scoda manifest should have correct metadata."""
        pc_db = self._create_paleocore_db(tmp_path)
        scoda_path = str(tmp_path / "test_paleocore.scoda")
        ScodaPackage.create(pc_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.name == 'paleocore'
            assert pkg.version == '0.3.0'
            assert pkg.record_count == 3  # 2 countries + 1 formation
            assert pkg.verify_checksum()

    def test_paleocore_scoda_record_count(self, tmp_path):
        """record_count should sum data tables, excluding SCODA metadata tables."""
        pc_db = self._create_paleocore_db(tmp_path)
        scoda_path = str(tmp_path / "test_paleocore.scoda")
        ScodaPackage.create(pc_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            # countries(2) + formations(1) = 3
            # artifact_metadata, provenance, schema_descriptions excluded
            assert pkg.record_count == 3

    def test_trilobase_scoda_with_dependency(self, test_db, tmp_path):
        """trilobase.scoda can declare dependency on paleocore."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "trilobase_dep.scoda")
        dep = {
            "dependencies": [{
                "name": "paleocore",
                "version": "0.3.0",
                "file": "paleocore.scoda",
            }]
        }
        ScodaPackage.create(canonical_db, scoda_path, metadata=dep)

        with ScodaPackage(scoda_path) as pkg:
            assert 'dependencies' in pkg.manifest
            assert len(pkg.manifest['dependencies']) == 1
            assert pkg.manifest['dependencies'][0]['name'] == 'paleocore'

    def test_paleocore_scoda_db_accessible(self, tmp_path):
        """Extracted paleocore DB should be queryable."""
        pc_db = self._create_paleocore_db(tmp_path)
        scoda_path = str(tmp_path / "test_paleocore.scoda")
        ScodaPackage.create(pc_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            conn = sqlite3.connect(pkg.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM countries")
            assert cursor.fetchone()['cnt'] == 2
            cursor.execute("SELECT COUNT(*) as cnt FROM formations")
            assert cursor.fetchone()['cnt'] == 1
            conn.close()


# --- ICS Chronostrat (Phase 28) ---




# --- ICS Chronostrat (Phase 28) ---

class TestICSChronostrat:
    """Tests for ics_chronostrat and temporal_ics_mapping tables (in paleocore.db)."""

    def test_ics_table_exists(self, test_db):
        """ics_chronostrat table should exist with sample data."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ics_chronostrat")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 6

    def test_ics_hierarchy_eon_to_age(self, test_db):
        """Hierarchy chain: Wuliuan → Miaolingian → Cambrian → Paleozoic → Phanerozoic."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        # Walk up from Wuliuan (Age) to Phanerozoic (Eon)
        cursor.execute("""
            SELECT a.name, e.name, p.name, er.name, eo.name
            FROM ics_chronostrat a
            JOIN ics_chronostrat e ON a.parent_id = e.id
            JOIN ics_chronostrat p ON e.parent_id = p.id
            JOIN ics_chronostrat er ON p.parent_id = er.id
            JOIN ics_chronostrat eo ON er.parent_id = eo.id
            WHERE a.name = 'Wuliuan'
        """)
        row = cursor.fetchone()
        conn.close()
        assert row == ('Wuliuan', 'Miaolingian', 'Cambrian', 'Paleozoic', 'Phanerozoic')

    def test_ics_ranks(self, test_db):
        """Each concept should have a valid rank."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT rank FROM ics_chronostrat ORDER BY rank")
        ranks = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert ranks == {'Age', 'Eon', 'Epoch', 'Era', 'Period'}

    def test_ics_cambrian_time_range(self, test_db):
        """Cambrian should have start_mya=538.8 and end_mya=486.85."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("SELECT start_mya, end_mya FROM ics_chronostrat WHERE name = 'Cambrian'")
        row = cursor.fetchone()
        conn.close()
        assert row[0] == 538.8
        assert row[1] == 486.85

    def test_ics_color_and_short_code(self, test_db):
        """Cambrian should have color #7FA056 and short code Ep."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("SELECT color, short_code FROM ics_chronostrat WHERE name = 'Cambrian'")
        row = cursor.fetchone()
        conn.close()
        assert row[0] == '#7FA056'
        assert row[1] == 'Ep'

    def test_ics_unique_uri(self, test_db):
        """Each concept should have a unique URI."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT ics_uri) FROM ics_chronostrat")
        distinct = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM ics_chronostrat")
        total = cursor.fetchone()[0]
        conn.close()
        assert distinct == total

    def test_mapping_table_exists(self, test_db):
        """temporal_ics_mapping table should exist with sample data."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM temporal_ics_mapping")
        count = cursor.fetchone()[0]
        conn.close()
        assert count == 5

    def test_mapping_exact(self, test_db):
        """MCAM should map exactly to Miaolingian."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ic.name, m.mapping_type
            FROM temporal_ics_mapping m
            JOIN ics_chronostrat ic ON m.ics_id = ic.id
            WHERE m.temporal_code = 'MCAM'
        """)
        row = cursor.fetchone()
        conn.close()
        assert row[0] == 'Miaolingian'
        assert row[1] == 'exact'

    def test_mapping_aggregate(self, test_db):
        """MUCAM should map to both Miaolingian and Furongian as aggregate."""
        _, _, paleocore_db = test_db
        conn = sqlite3.connect(paleocore_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ic.name, m.mapping_type
            FROM temporal_ics_mapping m
            JOIN ics_chronostrat ic ON m.ics_id = ic.id
            WHERE m.temporal_code = 'MUCAM'
            ORDER BY ic.name
        """)
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 2
        assert rows[0] == ('Furongian', 'aggregate')
        assert rows[1] == ('Miaolingian', 'aggregate')


# --- /api/chronostrat/<id> (Phase 29 Web UI) ---




# --- /api/chronostrat/<id> (Phase 29 Web UI) ---

class TestApiChronostratDetail:
    def test_chronostrat_detail_valid(self, client):
        """Should return basic info for Cambrian."""
        response = client.get('/api/chronostrat/3')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Cambrian'
        assert data['rank'] == 'Period'
        assert data['start_mya'] == 538.8
        assert data['end_mya'] == 486.85
        assert data['color'] == '#7FA056'
        assert data['short_code'] == 'Ep'

    def test_chronostrat_detail_not_found(self, client):
        response = client.get('/api/chronostrat/9999')
        assert response.status_code == 404

    def test_chronostrat_detail_parent(self, client):
        """Cambrian's parent should be Paleozoic."""
        response = client.get('/api/chronostrat/3')
        data = json.loads(response.data)
        assert data['parent'] is not None
        assert data['parent']['name'] == 'Paleozoic'
        assert data['parent']['rank'] == 'Era'

    def test_chronostrat_detail_no_parent(self, client):
        """Phanerozoic (Eon, root) should have no parent."""
        response = client.get('/api/chronostrat/1')
        data = json.loads(response.data)
        assert data['parent'] is None

    def test_chronostrat_detail_children(self, client):
        """Cambrian should have Miaolingian and Furongian as children."""
        response = client.get('/api/chronostrat/3')
        data = json.loads(response.data)
        child_names = [c['name'] for c in data['children']]
        assert 'Miaolingian' in child_names
        assert 'Furongian' in child_names

    def test_chronostrat_detail_children_structure(self, client):
        """Children should have id, name, rank, start_mya, end_mya, color."""
        response = client.get('/api/chronostrat/3')
        data = json.loads(response.data)
        child = data['children'][0]
        for key in ['id', 'name', 'rank', 'start_mya', 'end_mya', 'color']:
            assert key in child, f"Missing key: {key}"

    def test_chronostrat_detail_mappings(self, client):
        """Miaolingian should have MCAM and MUCAM mappings."""
        response = client.get('/api/chronostrat/4')
        data = json.loads(response.data)
        codes = [m['temporal_code'] for m in data['mappings']]
        assert 'MCAM' in codes
        assert 'MUCAM' in codes

    def test_chronostrat_detail_mapping_types(self, client):
        """MCAM should be exact, MUCAM should be aggregate."""
        response = client.get('/api/chronostrat/4')
        data = json.loads(response.data)
        mapping_map = {m['temporal_code']: m['mapping_type'] for m in data['mappings']}
        assert mapping_map['MCAM'] == 'exact'
        assert mapping_map['MUCAM'] == 'aggregate'

    def test_chronostrat_detail_genera(self, client):
        """Furongian (UCAM mapped) should list Olenus."""
        response = client.get('/api/chronostrat/6')
        data = json.loads(response.data)
        genus_names = [g['name'] for g in data['genera']]
        assert 'Olenus' in genus_names

    def test_chronostrat_detail_genera_structure(self, client):
        """Genera should have id, name, author, year, is_valid, temporal_code."""
        response = client.get('/api/chronostrat/6')
        data = json.loads(response.data)
        if data['genera']:
            g = data['genera'][0]
            for key in ['id', 'name', 'author', 'year', 'is_valid', 'temporal_code']:
                assert key in g, f"Missing key: {key}"

    def test_chronostrat_detail_response_structure(self, client):
        """Full response should have all required keys."""
        response = client.get('/api/chronostrat/3')
        data = json.loads(response.data)
        expected_keys = ['id', 'name', 'rank', 'start_mya', 'end_mya',
                         'start_uncertainty', 'end_uncertainty', 'short_code',
                         'color', 'ratified_gssp', 'parent', 'children',
                         'mappings', 'genera']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def test_chronostrat_query_execute(self, client):
        """ics_chronostrat_list query should return 6 rows."""
        response = client.get('/api/queries/ics_chronostrat_list/execute')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['row_count'] == 6

    def test_chronostrat_query_includes_parent_id(self, client):
        """ics_chronostrat_list query should include parent_id column."""
        response = client.get('/api/queries/ics_chronostrat_list/execute')
        data = json.loads(response.data)
        assert 'parent_id' in data['columns']
        # Cambrian (id=3) should have parent_id=2 (Paleozoic)
        cambrian = next(r for r in data['rows'] if r['name'] == 'Cambrian')
        assert cambrian['parent_id'] == 2

    def test_manifest_chart_type(self, client):
        """chronostratigraphy_table should have type 'chart'."""
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        chrono = data['manifest']['views']['chronostratigraphy_table']
        assert chrono['type'] == 'chart'


# --- Genus Detail ICS Mapping (Phase 29 Web UI) ---




# --- Genus Detail ICS Mapping (Phase 29 Web UI) ---

class TestGenusDetailICSMapping:
    def test_genus_detail_has_temporal_ics_mapping(self, client):
        """Genus detail should include temporal_ics_mapping field."""
        response = client.get('/api/genus/200')
        data = json.loads(response.data)
        assert 'temporal_ics_mapping' in data

    def test_genus_detail_ics_mapping_olenus(self, client):
        """Olenus (UCAM) should map to Furongian."""
        response = client.get('/api/genus/200')
        data = json.loads(response.data)
        assert len(data['temporal_ics_mapping']) == 1
        m = data['temporal_ics_mapping'][0]
        assert m['name'] == 'Furongian'
        assert m['rank'] == 'Epoch'
        assert m['mapping_type'] == 'exact'

    def test_genus_detail_ics_mapping_structure(self, client):
        """ICS mapping entries should have id, name, rank, mapping_type."""
        response = client.get('/api/genus/200')
        data = json.loads(response.data)
        if data['temporal_ics_mapping']:
            m = data['temporal_ics_mapping'][0]
            for key in ['id', 'name', 'rank', 'mapping_type']:
                assert key in m, f"Missing key: {key}"

    def test_genus_detail_ics_mapping_no_match(self, client):
        """Phacops (LDEV-UDEV) has no ICS mapping — should be empty list."""
        response = client.get('/api/genus/100')
        data = json.loads(response.data)
        assert data['temporal_ics_mapping'] == []


# --- Combined SCODA Deployment (Phase 36) ---




# --- Combined SCODA Deployment (Phase 36) ---

class TestCombinedScodaDeployment:
    """Tests for combined trilobase.scoda + paleocore.scoda deployment."""

    def _add_scoda_metadata_to_paleocore(self, paleocore_db_path):
        """Add SCODA metadata tables to paleocore DB for .scoda packaging."""
        conn = sqlite3.connect(paleocore_db_path)
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS artifact_metadata (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            INSERT OR REPLACE INTO artifact_metadata VALUES ('artifact_id', 'paleocore');
            INSERT OR REPLACE INTO artifact_metadata VALUES ('name', 'PaleoCore');
            INSERT OR REPLACE INTO artifact_metadata VALUES ('version', '0.3.0');
            INSERT OR REPLACE INTO artifact_metadata VALUES ('schema_version', '1.0');
            INSERT OR REPLACE INTO artifact_metadata VALUES ('description', 'Test PaleoCore');
            INSERT OR REPLACE INTO artifact_metadata VALUES ('license', 'CC-BY-4.0');

            CREATE TABLE IF NOT EXISTS provenance (
                id INTEGER PRIMARY KEY, source_type TEXT NOT NULL,
                citation TEXT NOT NULL, description TEXT, year INTEGER, url TEXT
            );

            CREATE TABLE IF NOT EXISTS schema_descriptions (
                table_name TEXT NOT NULL, column_name TEXT,
                description TEXT NOT NULL, PRIMARY KEY (table_name, column_name)
            );
        """)
        conn.commit()
        conn.close()

    def _setup_combined_scoda(self, test_db, tmp_path):
        """Create both .scoda packages from test DBs and set module-level paths."""
        canonical_db, overlay_db, paleocore_db = test_db
        self._add_scoda_metadata_to_paleocore(paleocore_db)

        tri_scoda = str(tmp_path / "trilobase.scoda")
        pc_scoda = str(tmp_path / "paleocore.scoda")
        ScodaPackage.create(canonical_db, tri_scoda)
        ScodaPackage.create(paleocore_db, pc_scoda)

        tri_pkg = ScodaPackage(tri_scoda)
        pc_pkg = ScodaPackage(pc_scoda)

        scoda_package._canonical_db = tri_pkg.db_path
        scoda_package._overlay_db = overlay_db
        scoda_package._paleocore_db = pc_pkg.db_path
        scoda_package._scoda_pkg = tri_pkg
        scoda_package._paleocore_pkg = pc_pkg

        return tri_pkg, pc_pkg

    def test_resolve_paleocore_finds_scoda(self, test_db, tmp_path):
        """_resolve_paleocore() should discover .scoda and set _paleocore_pkg."""
        _, _, paleocore_db = test_db
        self._add_scoda_metadata_to_paleocore(paleocore_db)

        scoda_dir = str(tmp_path / "scoda_resolve_test")
        os.makedirs(scoda_dir)
        ScodaPackage.create(paleocore_db, os.path.join(scoda_dir, "paleocore.scoda"))

        scoda_package._reset_paths()
        scoda_package._resolve_paleocore(scoda_dir)

        try:
            assert scoda_package._paleocore_pkg is not None
            assert scoda_package._paleocore_db is not None
            assert os.path.exists(scoda_package._paleocore_db)
        finally:
            scoda_package._reset_paths()

    def test_resolve_paleocore_falls_back_to_db(self, tmp_path):
        """When no .scoda exists, _resolve_paleocore() should fall back to .db path."""
        scoda_dir = str(tmp_path / "empty_dir")
        os.makedirs(scoda_dir)

        scoda_package._reset_paths()
        scoda_package._resolve_paleocore(scoda_dir)

        try:
            assert scoda_package._paleocore_pkg is None
            expected = os.path.join(scoda_dir, 'paleocore.db')
            assert scoda_package._paleocore_db == expected
        finally:
            scoda_package._reset_paths()

    def test_combined_scoda_get_db(self, test_db, tmp_path):
        """Two .scoda packages should yield working 3-DB ATTACH + cross-DB JOIN."""
        try:
            self._setup_combined_scoda(test_db, tmp_path)

            conn = get_db()
            dbs = conn.execute("PRAGMA database_list").fetchall()
            db_names = [row['name'] for row in dbs]
            assert 'main' in db_names
            assert 'overlay' in db_names
            assert 'pc' in db_names

            # Cross-DB JOIN: genus_locations ↔ pc.countries
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM genus_locations gl
                JOIN pc.countries c ON gl.country_id = c.id
            """)
            assert cursor.fetchone()['cnt'] > 0
            conn.close()
        finally:
            scoda_package._reset_paths()

    def test_combined_scoda_flask_api(self, test_db, tmp_path):
        """Flask /api/paleocore/status should work with .scoda-extracted DBs."""
        try:
            self._setup_combined_scoda(test_db, tmp_path)

            app.config['TESTING'] = True
            with app.test_client() as client:
                response = client.get('/api/paleocore/status')
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['attached'] is True
                assert 'tables' in data
                assert data['cross_db_join_test']['status'] == 'OK'
        finally:
            scoda_package._reset_paths()

    def test_combined_scoda_info(self, test_db, tmp_path):
        """get_scoda_info() should report both sources as 'scoda'."""
        try:
            self._setup_combined_scoda(test_db, tmp_path)

            info = scoda_package.get_scoda_info()
            assert info['source_type'] == 'scoda'
            assert info['paleocore_source_type'] == 'scoda'
            assert info['canonical_exists'] is True
            assert info['paleocore_exists'] is True
        finally:
            scoda_package._reset_paths()

    def test_combined_scoda_genus_detail(self, test_db, tmp_path):
        """Genus detail API should JOIN pc.formations and pc.geographic_regions from .scoda."""
        try:
            self._setup_combined_scoda(test_db, tmp_path)

            app.config['TESTING'] = True
            with app.test_client() as client:
                response = client.get('/api/genus/101')  # Acuticryphops
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['name'] == 'Acuticryphops'
                # formations via pc.formations
                assert len(data['formations']) > 0
                # locations via pc.geographic_regions
                assert len(data['locations']) > 0
        finally:
            scoda_package._reset_paths()


# --- /api/paleocore/status (Phase 36) ---




# --- /api/paleocore/status (Phase 36) ---

class TestApiPaleocoreStatus:
    """Tests for /api/paleocore/status endpoint (basic, using direct .db paths)."""

    def test_paleocore_status_200(self, client):
        """Endpoint should return 200."""
        response = client.get('/api/paleocore/status')
        assert response.status_code == 200

    def test_paleocore_status_attached(self, client):
        """Response should show attached=True with tables dict."""
        response = client.get('/api/paleocore/status')
        data = json.loads(response.data)
        assert data['attached'] is True
        assert 'tables' in data
        assert isinstance(data['tables'], dict)

    def test_paleocore_status_cross_db_join(self, client):
        """Cross-DB join test should report OK with matched rows."""
        response = client.get('/api/paleocore/status')
        data = json.loads(response.data)
        assert 'cross_db_join_test' in data
        assert data['cross_db_join_test']['status'] == 'OK'
        assert data['cross_db_join_test']['matched_rows'] > 0


# ---------------------------------------------------------------------------
# PackageRegistry tests
# ---------------------------------------------------------------------------

