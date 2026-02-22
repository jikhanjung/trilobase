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

import scoda_engine.scoda_package as scoda_package
from scoda_engine.app import app
from scoda_engine.scoda_package import get_db, ScodaPackage








# --- Declarative Manifest Detail Views (Phase 39) ---

class TestManifestDetailSchema:
    """Tests for manifest detail view schema (Phase 39)."""

    def _get_manifest(self, client):
        response = client.get('/api/manifest')
        return response.json()['manifest']

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

    def test_chart_view_has_nested_table_display(self, client):
        """chronostratigraphy_table should have hierarchy type with nested_table_display."""
        m = self._get_manifest(client)
        chrono = m['views']['chronostratigraphy_table']
        assert chrono['type'] == 'hierarchy'
        assert chrono['display'] == 'nested_table'
        assert 'nested_table_display' in chrono
        assert 'cell_click' in chrono['nested_table_display']


# --- Manifest Hierarchy Options (Phase 41 → A-3 정규화) ---

class TestManifestHierarchy:
    """Tests for manifest hierarchy_options, tree_display, nested_table_display."""

    def _get_manifest(self, client):
        response = client.get('/api/manifest')
        return response.json()['manifest']

    def test_tree_view_has_hierarchy_options(self, client):
        """taxonomy_tree should have hierarchy_options with required keys."""
        m = self._get_manifest(client)
        tree = m['views']['taxonomy_tree']
        assert tree['type'] == 'hierarchy'
        assert tree['display'] == 'tree'
        assert 'hierarchy_options' in tree
        opts = tree['hierarchy_options']
        for key in ['id_key', 'parent_key', 'label_key', 'rank_key']:
            assert key in opts, f"hierarchy_options missing key: {key}"

    def test_tree_display_item_query_exists(self, client):
        """tree_display.item_query should reference an existing named query."""
        m = self._get_manifest(client)
        tree_disp = m['views']['taxonomy_tree']['tree_display']
        assert 'item_query' in tree_disp
        assert 'item_param' in tree_disp

        queries_response = client.get('/api/queries')
        query_names = {q['name'] for q in queries_response.json()}
        assert tree_disp['item_query'] in query_names, \
            f"item_query '{tree_disp['item_query']}' not found in named queries"

    def test_tree_display_item_columns(self, client):
        """tree_display.item_columns should be an array of column definitions."""
        m = self._get_manifest(client)
        tree_disp = m['views']['taxonomy_tree']['tree_display']
        assert 'item_columns' in tree_disp
        cols = tree_disp['item_columns']
        assert isinstance(cols, list)
        assert len(cols) > 0
        for col in cols:
            assert 'key' in col, "Each item_column must have 'key'"
            assert 'label' in col, "Each item_column must have 'label'"

    def test_tree_display_on_node_info(self, client):
        """tree_display.on_node_info should define detail view navigation."""
        m = self._get_manifest(client)
        tree_disp = m['views']['taxonomy_tree']['tree_display']
        assert 'on_node_info' in tree_disp
        info = tree_disp['on_node_info']
        assert 'detail_view' in info
        assert info['detail_view'] in m['views'], \
            f"on_node_info.detail_view '{info['detail_view']}' not in manifest views"

    def test_nested_table_rank_columns(self, client):
        """nested_table_display.rank_columns should be an array with rank and label."""
        m = self._get_manifest(client)
        nt_disp = m['views']['chronostratigraphy_table']['nested_table_display']
        assert 'rank_columns' in nt_disp
        cols = nt_disp['rank_columns']
        assert isinstance(cols, list)
        assert len(cols) >= 4  # At least Eon, Era, Period, Epoch
        for col in cols:
            assert 'rank' in col, "Each rank_column must have 'rank'"
            assert 'label' in col, "Each rank_column must have 'label'"

    def test_nested_table_value_column(self, client):
        """nested_table_display.value_column should exist with key and label."""
        m = self._get_manifest(client)
        nt_disp = m['views']['chronostratigraphy_table']['nested_table_display']
        assert 'value_column' in nt_disp
        vc = nt_disp['value_column']
        assert 'key' in vc
        assert 'label' in vc

    def test_hierarchy_skip_ranks(self, client):
        """hierarchy_options.skip_ranks should be a list."""
        m = self._get_manifest(client)
        opts = m['views']['chronostratigraphy_table']['hierarchy_options']
        assert 'skip_ranks' in opts
        assert isinstance(opts['skip_ranks'], list)

    def test_no_legacy_tree_chart_options(self, client):
        """Views should not have legacy tree_options/chart_options keys."""
        m = self._get_manifest(client)
        tree = m['views']['taxonomy_tree']
        assert 'tree_options' not in tree, "Legacy 'tree_options' should be hierarchy_options + tree_display"
        chrono = m['views']['chronostratigraphy_table']
        assert 'chart_options' not in chrono, "Legacy 'chart_options' should be hierarchy_options + nested_table_display"


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
        assert count == 6

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
        scoda_package._dep_dbs = {'pc': pc_pkg.db_path}
        scoda_package._scoda_pkg = tri_pkg
        scoda_package._dep_pkgs = [pc_pkg]

        return tri_pkg, pc_pkg

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

    def test_combined_scoda_api(self, test_db, tmp_path):
        """/api/manifest should work with .scoda-extracted DBs."""
        try:
            self._setup_combined_scoda(test_db, tmp_path)

            from starlette.testclient import TestClient
            with TestClient(app) as client:
                response = client.get('/api/manifest')
                assert response.status_code == 200
                data = response.json()
                assert 'manifest' in data
        finally:
            scoda_package._reset_paths()

    def test_combined_scoda_info(self, test_db, tmp_path):
        """get_scoda_info() should report scoda source and dependency databases."""
        try:
            self._setup_combined_scoda(test_db, tmp_path)

            info = scoda_package.get_scoda_info()
            assert info['source_type'] == 'scoda'
            assert info['canonical_exists'] is True
            assert 'pc' in info['dep_dbs']
        finally:
            scoda_package._reset_paths()

    def test_combined_scoda_genus_detail(self, test_db, tmp_path):
        """Composite genus detail should JOIN pc.formations and pc.geographic_regions from .scoda."""
        try:
            self._setup_combined_scoda(test_db, tmp_path)

            from starlette.testclient import TestClient
            with TestClient(app) as client:
                response = client.get('/api/composite/genus_detail?id=101')  # Acuticryphops
                assert response.status_code == 200
                data = response.json()
                assert data['name'] == 'Acuticryphops'
                # formations via pc.formations
                assert len(data['formations']) > 0
                # locations via pc.geographic_regions
                assert len(data['locations']) > 0
        finally:
            scoda_package._reset_paths()



# ---------------------------------------------------------------------------
# Phase 46: Composite endpoint domain-specific validation
# ---------------------------------------------------------------------------


class TestCompositeFormationDetail:
    """Composite formation detail via manifest-driven queries."""

    def test_formation_composite(self, client):
        """Composite formation detail should return formation info + genera."""
        response = client.get('/api/composite/formation_detail?id=1')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Büdesheimer Sh'
        assert 'genera' in data
        assert isinstance(data['genera'], list)
        assert len(data['genera']) == 1
        assert data['genera'][0]['name'] == 'Acuticryphops'

    def test_formation_not_found(self, client):
        response = client.get('/api/composite/formation_detail?id=9999')
        assert response.status_code == 404


class TestCompositeCountryDetail:
    """Composite country detail via manifest-driven queries."""

    def test_country_composite(self, client):
        """Composite country detail should return country info + regions + genera."""
        response = client.get('/api/composite/country_detail?id=1')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Germany'
        assert 'regions' in data
        assert 'genera' in data
        assert isinstance(data['regions'], list)
        assert isinstance(data['genera'], list)

    def test_country_has_regions(self, client):
        response = client.get('/api/composite/country_detail?id=1')
        data = response.json()
        region_names = [r['name'] for r in data['regions']]
        assert 'Eifel' in region_names

    def test_country_has_genera(self, client):
        response = client.get('/api/composite/country_detail?id=1')
        data = response.json()
        genus_names = [g['name'] for g in data['genera']]
        assert 'Acuticryphops' in genus_names


class TestCompositeRegionDetail:
    """Composite region detail via manifest-driven queries."""

    def test_region_composite(self, client):
        """Composite region detail should return region info + genera."""
        response = client.get('/api/composite/region_detail?id=3')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Eifel'
        assert data['country_name'] == 'Germany'
        assert 'genera' in data
        assert len(data['genera']) == 1
        assert data['genera'][0]['name'] == 'Acuticryphops'


class TestCompositeBibliographyDetail:
    """Composite bibliography detail via manifest-driven queries."""

    def test_bibliography_composite(self, client):
        """Composite bibliography detail should return bib info + taxa."""
        response = client.get('/api/composite/bibliography_detail?id=1')
        assert response.status_code == 200
        data = response.json()
        assert data['authors'] == 'Jell, P.A. & Adrain, J.M.'
        assert data['year'] == 2002
        assert 'taxa' in data
        assert isinstance(data['taxa'], list)


class TestCompositeChronostratDetail:
    """Composite chronostrat detail via manifest-driven queries."""

    def test_chronostrat_composite(self, client):
        """Composite chronostrat detail should return unit + children + mappings + genera."""
        response = client.get('/api/composite/chronostrat_detail?id=3')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Cambrian'
        assert data['rank'] == 'Period'
        assert 'children' in data
        assert 'mappings' in data
        assert 'genera' in data
        assert isinstance(data['children'], list)

    def test_chronostrat_has_children(self, client):
        """Cambrian should have child epochs (Miaolingian, Furongian)."""
        response = client.get('/api/composite/chronostrat_detail?id=3')
        data = response.json()
        child_names = [c['name'] for c in data['children']]
        assert 'Miaolingian' in child_names
        assert 'Furongian' in child_names

    def test_chronostrat_has_mappings(self, client):
        """Cambrian should have temporal code mappings."""
        response = client.get('/api/composite/chronostrat_detail?id=3')
        data = response.json()
        codes = [m['temporal_code'] for m in data['mappings']]
        assert 'CAM' in codes

    def test_chronostrat_genera(self, client):
        """Furongian (id=6) has UCAM mapping → should find Olenus."""
        response = client.get('/api/composite/chronostrat_detail?id=6')
        data = response.json()
        assert data['name'] == 'Furongian'
        genus_names = [g['name'] for g in data['genera']]
        assert 'Olenus' in genus_names


# ---------------------------------------------------------------------------
# PackageRegistry tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# B-1: Taxonomic Opinions PoC
# ---------------------------------------------------------------------------

class TestTaxonomicOpinions:
    """Tests for taxonomic_opinions table, triggers, constraints, and API integration."""

    # --- Schema tests ---

    def test_opinions_table_exists(self, test_db):
        """taxonomic_opinions table should exist in the test DB."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='taxonomic_opinions'")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_opinions_columns(self, test_db):
        """taxonomic_opinions should have all expected columns."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(taxonomic_opinions)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            'id', 'taxon_id', 'opinion_type', 'related_taxon_id', 'proposed_valid',
            'bibliography_id', 'assertion_status', 'curation_confidence',
            'is_accepted', 'notes', 'created_at'
        }
        assert expected.issubset(columns)
        conn.close()

    def test_is_placeholder_column(self, test_db):
        """taxonomic_ranks should have is_placeholder column."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(taxonomic_ranks)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'is_placeholder' in columns
        conn.close()

    # --- Constraint tests ---

    def test_opinion_type_check(self, test_db):
        """Invalid opinion_type should be rejected by CHECK constraint."""
        conn = sqlite3.connect(test_db[0])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO taxonomic_opinions (taxon_id, opinion_type, related_taxon_id)
                VALUES (2, 'INVALID_TYPE', 1)
            """)
        conn.close()

    def test_assertion_status_check(self, test_db):
        """Invalid assertion_status should be rejected."""
        conn = sqlite3.connect(test_db[0])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO taxonomic_opinions (taxon_id, opinion_type, related_taxon_id, assertion_status)
                VALUES (2, 'PLACED_IN', 1, 'BOGUS')
            """)
        conn.close()

    def test_curation_confidence_check(self, test_db):
        """Invalid curation_confidence should be rejected."""
        conn = sqlite3.connect(test_db[0])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO taxonomic_opinions (taxon_id, opinion_type, related_taxon_id, curation_confidence)
                VALUES (2, 'PLACED_IN', 1, 'BOGUS')
            """)
        conn.close()

    def test_partial_unique_accepted_non_placed(self, test_db):
        """Partial unique index prevents two accepted for same taxon+type (non-PLACED_IN)."""
        conn = sqlite3.connect(test_db[0])
        # Insert first accepted VALID_AS (no trigger for VALID_AS)
        conn.execute("""
            INSERT INTO taxonomic_opinions (taxon_id, opinion_type, proposed_valid, is_accepted)
            VALUES (100, 'VALID_AS', 1, 1)
        """)
        conn.commit()
        # Second accepted VALID_AS for same taxon should fail (unique index, no trigger to deactivate)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO taxonomic_opinions (taxon_id, opinion_type, proposed_valid, is_accepted)
                VALUES (100, 'VALID_AS', 0, 1)
            """)
        conn.close()

    # --- Trigger tests ---

    def test_trigger_insert_sync_parent(self, test_db):
        """Inserting accepted PLACED_IN should update parent_id."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        # Phacopidae (id=10) currently parent_id=2 (Phacopida)
        cursor.execute("SELECT parent_id FROM taxonomic_ranks WHERE id = 10")
        assert cursor.fetchone()[0] == 2

        # Insert accepted PLACED_IN: Phacopidae → Ptychopariida (id=3)
        cursor.execute("""
            INSERT INTO taxonomic_opinions (taxon_id, opinion_type, related_taxon_id, is_accepted)
            VALUES (10, 'PLACED_IN', 3, 1)
        """)
        conn.commit()

        # parent_id should now be 3
        cursor.execute("SELECT parent_id FROM taxonomic_ranks WHERE id = 10")
        assert cursor.fetchone()[0] == 3
        conn.close()

    def test_trigger_update_sync_parent(self, test_db):
        """Updating is_accepted to 1 should update parent_id."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        # Phacopida (id=2) has accepted opinion pointing to Trilobita (id=1)
        # and alternative pointing to Ptychopariida (id=3)
        cursor.execute("SELECT parent_id FROM taxonomic_ranks WHERE id = 2")
        assert cursor.fetchone()[0] == 1

        # Accept the alternative opinion (id=2: Phacopida → Ptychopariida)
        cursor.execute("UPDATE taxonomic_opinions SET is_accepted = 1 WHERE id = 2")
        conn.commit()

        # parent_id should now be 3 (Ptychopariida)
        cursor.execute("SELECT parent_id FROM taxonomic_ranks WHERE id = 2")
        assert cursor.fetchone()[0] == 3

        # Previous accepted (id=1) should be deactivated
        cursor.execute("SELECT is_accepted FROM taxonomic_opinions WHERE id = 1")
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_trigger_deactivates_previous(self, test_db):
        """New accepted opinion should deactivate previous accepted."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        # Insert new accepted PLACED_IN for Phacopida (already has accepted id=1)
        cursor.execute("""
            INSERT INTO taxonomic_opinions (taxon_id, opinion_type, related_taxon_id, is_accepted)
            VALUES (2, 'PLACED_IN', 3, 1)
        """)
        conn.commit()

        # Old opinion (id=1) should now be is_accepted=0
        cursor.execute("SELECT is_accepted FROM taxonomic_opinions WHERE id = 1")
        assert cursor.fetchone()[0] == 0

        # New opinion should be the only accepted
        cursor.execute("""
            SELECT COUNT(*) FROM taxonomic_opinions
            WHERE taxon_id = 2 AND opinion_type = 'PLACED_IN' AND is_accepted = 1
        """)
        assert cursor.fetchone()[0] == 1
        conn.close()

    # --- API / Composite tests ---

    def test_opinions_named_query(self, client):
        """taxon_opinions named query should return opinions for a taxon."""
        response = client.get('/api/queries/taxon_opinions/execute?taxon_id=2')
        assert response.status_code == 200
        data = response.json()
        assert data['row_count'] == 2
        # Accepted should come first (ORDER BY is_accepted DESC)
        assert data['rows'][0]['is_accepted'] == 1
        assert data['rows'][0]['related_taxon_name'] == 'Trilobita'

    def test_composite_rank_detail_includes_opinions(self, client):
        """Composite rank_detail should include opinions for taxa with opinions."""
        response = client.get('/api/composite/rank_detail?id=2')
        assert response.status_code == 200
        data = response.json()
        assert 'opinions' in data
        assert len(data['opinions']) == 2
        # Accepted first
        assert data['opinions'][0]['is_accepted'] == 1

    def test_composite_rank_detail_no_opinions(self, client):
        """Taxa without opinions should have empty opinions list."""
        # Trilobita (id=1) has no opinions
        response = client.get('/api/composite/rank_detail?id=1')
        assert response.status_code == 200
        data = response.json()
        assert 'opinions' in data
        assert len(data['opinions']) == 0

    # --- Manifest tests ---

    def test_rank_detail_manifest_has_opinions_sub_query(self, client):
        """rank_detail manifest should have opinions in sub_queries."""
        response = client.get('/api/manifest')
        manifest = response.json()['manifest']
        rank_detail = manifest['views']['rank_detail']
        assert 'opinions' in rank_detail['sub_queries']
        assert rank_detail['sub_queries']['opinions']['query'] == 'taxon_opinions'

    def test_rank_detail_manifest_has_opinions_section(self, client):
        """rank_detail manifest should have opinions linked_table section."""
        response = client.get('/api/manifest')
        manifest = response.json()['manifest']
        sections = manifest['views']['rank_detail']['sections']
        opinion_sections = [s for s in sections if s.get('data_key') == 'opinions']
        assert len(opinion_sections) == 1
        assert opinion_sections[0]['type'] == 'linked_table'


# ---------------------------------------------------------------------------
# Taxon-Bibliography Junction
# ---------------------------------------------------------------------------

class TestTaxonBibliography:
    """Tests for taxon_bibliography junction table, queries, and manifest integration."""

    # --- Schema tests ---

    def test_table_exists(self, test_db):
        """taxon_bibliography table should exist."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='taxon_bibliography'")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_columns(self, test_db):
        """taxon_bibliography should have all expected columns."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(taxon_bibliography)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            'id', 'taxon_id', 'bibliography_id', 'relationship_type',
            'synonym_id', 'match_confidence', 'match_method', 'notes', 'created_at'
        }
        assert expected.issubset(columns)
        conn.close()

    def test_relationship_type_check(self, test_db):
        """Invalid relationship_type should be rejected."""
        conn = sqlite3.connect(test_db[0])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO taxon_bibliography (taxon_id, bibliography_id, relationship_type)
                VALUES (100, 10, 'INVALID')
            """)
        conn.close()

    def test_match_confidence_check(self, test_db):
        """Invalid match_confidence should be rejected."""
        conn = sqlite3.connect(test_db[0])
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO taxon_bibliography (taxon_id, bibliography_id, match_confidence)
                VALUES (100, 10, 'INVALID')
            """)
        conn.close()

    def test_unique_constraint(self, test_db):
        """Duplicate (taxon_id, bibliography_id, relationship_type, synonym_id) should be rejected."""
        conn = sqlite3.connect(test_db[0])
        # Existing row: (102, 12, 'fide', synonym_id=1) — insert duplicate with same synonym_id
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO taxon_bibliography (taxon_id, bibliography_id, relationship_type, synonym_id, match_confidence, match_method)
                VALUES (102, 12, 'fide', 1, 'high', 'fide_unique')
            """)
        conn.close()

    # --- Data tests ---

    def test_original_description_link(self, test_db):
        """Phacops should be linked to EMMRICH 1839 as original_description."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tb.relationship_type, tb.match_confidence, b.authors, b.year
            FROM taxon_bibliography tb
            JOIN bibliography b ON tb.bibliography_id = b.id
            WHERE tb.taxon_id = 100 AND tb.relationship_type = 'original_description'
        """)
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'original_description'
        assert row[1] == 'high'
        assert 'EMMRICH' in row[2]
        assert row[3] == 1839

    def test_fide_link(self, test_db):
        """Cryphops should have a fide link to CLARKSON 1969 via synonym."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tb.relationship_type, tb.synonym_id, b.authors, b.year
            FROM taxon_bibliography tb
            JOIN bibliography b ON tb.bibliography_id = b.id
            WHERE tb.taxon_id = 102 AND tb.relationship_type = 'fide'
        """)
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 'fide'
        assert row[1] == 1  # synonym_id
        assert 'CLARKSON' in row[2]
        assert row[3] == 1969

    def test_junction_row_count(self, test_db):
        """Should have 3 junction rows (2 original_description + 1 fide)."""
        conn = sqlite3.connect(test_db[0])
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM taxon_bibliography")
        assert cursor.fetchone()[0] == 3
        conn.close()

    # --- Named query tests ---

    def test_taxon_bibliography_list_query(self, client):
        """taxon_bibliography_list should return taxa linked to a bibliography entry."""
        response = client.get('/api/queries/taxon_bibliography_list/execute?bibliography_id=10')
        assert response.status_code == 200
        data = response.json()
        assert data['row_count'] == 1
        assert data['rows'][0]['name'] == 'Phacops'
        assert data['rows'][0]['relationship_type'] == 'original_description'

    def test_taxon_bibliography_query(self, client):
        """taxon_bibliography should return bibliography entries linked to a taxon."""
        response = client.get('/api/queries/taxon_bibliography/execute?taxon_id=101')
        assert response.status_code == 200
        data = response.json()
        assert data['row_count'] == 1
        assert 'RICHTER' in data['rows'][0]['authors']
        assert data['rows'][0]['relationship_type'] == 'original_description'

    # --- Composite detail tests ---

    def test_bibliography_detail_has_taxa(self, client):
        """Composite bibliography_detail should include linked taxa (not LIKE-based genera)."""
        response = client.get('/api/composite/bibliography_detail?id=11')
        assert response.status_code == 200
        data = response.json()
        assert 'taxa' in data
        assert len(data['taxa']) == 1
        assert data['taxa'][0]['name'] == 'Acuticryphops'
        assert data['taxa'][0]['relationship_type'] == 'original_description'

    def test_genus_detail_has_bibliography(self, client):
        """Composite genus_detail should include bibliography sub_query."""
        response = client.get('/api/composite/genus_detail?id=100')
        assert response.status_code == 200
        data = response.json()
        assert 'bibliography' in data
        assert len(data['bibliography']) == 1
        assert 'EMMRICH' in data['bibliography'][0]['authors']

    def test_rank_detail_has_bibliography(self, client):
        """Composite rank_detail should include bibliography sub_query (empty for ranks without links)."""
        # Phacopida (id=2) has no direct bibliography link in test data
        response = client.get('/api/composite/rank_detail?id=2')
        assert response.status_code == 200
        data = response.json()
        assert 'bibliography' in data

    # --- Manifest tests ---

    def test_bibliography_detail_manifest_uses_taxa(self, client):
        """bibliography_detail manifest should use taxon_bibliography_list (not bibliography_genera)."""
        response = client.get('/api/manifest')
        manifest = response.json()['manifest']
        bib_detail = manifest['views']['bibliography_detail']
        assert 'taxa' in bib_detail['sub_queries']
        assert bib_detail['sub_queries']['taxa']['query'] == 'taxon_bibliography_list'

    def test_genus_detail_manifest_has_bibliography(self, client):
        """genus_detail manifest should have bibliography in sub_queries."""
        response = client.get('/api/manifest')
        manifest = response.json()['manifest']
        genus_detail = manifest['views']['genus_detail']
        assert 'bibliography' in genus_detail['sub_queries']
        assert genus_detail['sub_queries']['bibliography']['query'] == 'taxon_bibliography'

    def test_rank_detail_manifest_has_bibliography(self, client):
        """rank_detail manifest should have bibliography in sub_queries."""
        response = client.get('/api/manifest')
        manifest = response.json()['manifest']
        rank_detail = manifest['views']['rank_detail']
        assert 'bibliography' in rank_detail['sub_queries']
        assert rank_detail['sub_queries']['bibliography']['query'] == 'taxon_bibliography'


# ---------------------------------------------------------------------------
# Group A Fix: Spelling variant duplicates resolved
# ---------------------------------------------------------------------------

class TestGroupAFix:
    """Verify spelling variant duplicates have been resolved in production DB."""

    DB_PATH = 'db/trilobase.db'

    def test_shirakiellidae_duplicate_deleted(self):
        """Empty Shirakiellidae duplicate (id=196) should be deleted."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM taxonomic_ranks WHERE id = 196')
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_dokimocephalidae_deleted(self):
        """Dokimocephalidae (id=210) should be deleted."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM taxonomic_ranks WHERE id = 210')
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_dokimokephalidae_has_genera(self):
        """Dokimokephalidae (id=134) should have 46 genera."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT genera_count FROM taxonomic_ranks WHERE id = 134')
        assert cursor.fetchone()[0] == 46
        conn.close()

    def test_chengkouaspidae_deleted(self):
        """Chengkouaspidae (id=205) should be deleted."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM taxonomic_ranks WHERE id = 205')
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_chengkouaspididae_has_genera(self):
        """Chengkouaspididae (id=36) should have 11 genera."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT genera_count FROM taxonomic_ranks WHERE id = 36')
        assert cursor.fetchone()[0] == 11
        conn.close()


# ---------------------------------------------------------------------------
# Agnostida Order creation
# ---------------------------------------------------------------------------

class TestAgnostidaOrder:
    """Verify Agnostida Order with order-level opinions (not family-level)."""

    DB_PATH = 'db/trilobase.db'

    def test_agnostida_order_exists(self):
        """Agnostida Order should exist with parent_id=NULL (excluded from Trilobita by A2011)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, parent_id, author, year, genera_count FROM taxonomic_ranks "
            "WHERE name = 'Agnostida' AND rank = 'Order'"
        )
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[1] is None  # parent_id = NULL (A2011 excluded from Trilobita)
        assert row[2] == 'SALTER'
        assert row[3] == '1864'
        assert row[4] == 162

    def test_agnostida_has_10_families(self):
        """Agnostida should have exactly 10 families (parent_id, no opinions needed)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM taxonomic_ranks WHERE parent_id = "
            "(SELECT id FROM taxonomic_ranks WHERE name = 'Agnostida' AND rank = 'Order') "
            "AND rank = 'Family'"
        )
        assert cursor.fetchone()[0] == 10
        conn.close()

    def test_agnostida_no_family_opinions(self):
        """No family-level PLACED_IN opinions for Agnostida (undisputed membership)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        agnostida_id = cursor.execute(
            "SELECT id FROM taxonomic_ranks WHERE name = 'Agnostida' AND rank = 'Order'"
        ).fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM taxonomic_opinions o "
            "JOIN taxonomic_ranks t ON o.taxon_id = t.id "
            "WHERE o.related_taxon_id = ? AND t.rank = 'Family'",
            (agnostida_id,)
        )
        assert cursor.fetchone()[0] == 0
        conn.close()

    def test_agnostida_order_opinions(self):
        """Agnostida should have 2 order-level opinions: JA2002 (not accepted) + A2011 (accepted)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        agnostida_id = cursor.execute(
            "SELECT id FROM taxonomic_ranks WHERE name = 'Agnostida' AND rank = 'Order'"
        ).fetchone()[0]
        cursor.execute(
            "SELECT related_taxon_id, is_accepted, bibliography_id FROM taxonomic_opinions "
            "WHERE taxon_id = ? AND opinion_type = 'PLACED_IN' ORDER BY is_accepted",
            (agnostida_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        assert len(rows) == 2
        # JA2002: PLACED_IN Trilobita, not accepted
        assert rows[0][0] == 1   # related_taxon_id = Trilobita
        assert rows[0][1] == 0   # not accepted
        # A2011: PLACED_IN NULL (excluded), accepted
        assert rows[1][0] is None  # excluded
        assert rows[1][1] == 1    # accepted
        assert rows[1][2] == 2131  # Adrain 2011 bibliography

    def test_order_uncertain_reduced(self):
        """Order Uncertain should have 68 families."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM taxonomic_ranks WHERE parent_id = 144 AND rank = 'Family'"
        )
        assert cursor.fetchone()[0] == 68
        conn.close()

    def test_total_opinions_count(self):
        """Total taxonomic opinions should be 6 (2 Eurekiidae + 2 Agnostida + 2 SPELLING_OF)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM taxonomic_opinions")
        assert cursor.fetchone()[0] == 6
        conn.close()


# ---------------------------------------------------------------------------
# SPELLING_OF Opinion Type for Orthographic Variants
# ---------------------------------------------------------------------------

class TestSpellingOfOpinions:
    """Verify SPELLING_OF opinion type and placeholder entries for orthographic variants."""

    DB_PATH = 'db/trilobase.db'

    def test_spelling_of_type_allowed(self, test_db):
        """SPELLING_OF should be accepted by CHECK constraint in test DB."""
        conn = sqlite3.connect(test_db[0])
        # Insert a placeholder taxon
        conn.execute(
            "INSERT INTO taxonomic_ranks (id, name, rank, is_placeholder, uid, uid_method, uid_confidence) "
            "VALUES (999, 'TestVariant', 'Family', 1, 'scoda:taxon:family:TestVariant', 'name', 'high')"
        )
        # Insert SPELLING_OF opinion — should not raise
        conn.execute(
            "INSERT INTO taxonomic_opinions (taxon_id, opinion_type, related_taxon_id, "
            "assertion_status, curation_confidence, is_accepted) "
            "VALUES (999, 'SPELLING_OF', 10, 'asserted', 'high', 1)"
        )
        conn.commit()
        row = conn.execute(
            "SELECT opinion_type FROM taxonomic_opinions WHERE taxon_id = 999"
        ).fetchone()
        assert row[0] == 'SPELLING_OF'
        conn.close()

    def test_dokimocephalidae_placeholder(self):
        """Dokimocephalidae should exist as placeholder (is_placeholder=1, genera_count=0)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, is_placeholder, genera_count, parent_id "
            "FROM taxonomic_ranks WHERE name = 'Dokimocephalidae' AND rank = 'Family'"
        )
        row = cursor.fetchone()
        conn.close()
        assert row is not None, "Dokimocephalidae placeholder not found"
        assert row[1] == 1  # is_placeholder
        assert row[2] == 0  # genera_count
        assert row[3] is None  # parent_id NULL

    def test_dokimocephalidae_opinion(self):
        """Dokimocephalidae should have SPELLING_OF opinion pointing to Dokimokephalidae (id=134)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT o.opinion_type, o.related_taxon_id, o.is_accepted, t.name "
            "FROM taxonomic_opinions o "
            "JOIN taxonomic_ranks t ON o.related_taxon_id = t.id "
            "WHERE o.taxon_id = ("
            "  SELECT id FROM taxonomic_ranks WHERE name = 'Dokimocephalidae' AND is_placeholder = 1"
            ") AND o.opinion_type = 'SPELLING_OF'"
        )
        row = cursor.fetchone()
        conn.close()
        assert row is not None, "SPELLING_OF opinion for Dokimocephalidae not found"
        assert row[0] == 'SPELLING_OF'
        assert row[1] == 134  # Dokimokephalidae
        assert row[2] == 1   # is_accepted
        assert row[3] == 'Dokimokephalidae'

    def test_chengkouaspidae_opinion(self):
        """Chengkouaspidae should have SPELLING_OF opinion pointing to Chengkouaspididae (id=36)."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT o.opinion_type, o.related_taxon_id, o.is_accepted, t.name "
            "FROM taxonomic_opinions o "
            "JOIN taxonomic_ranks t ON o.related_taxon_id = t.id "
            "WHERE o.taxon_id = ("
            "  SELECT id FROM taxonomic_ranks WHERE name = 'Chengkouaspidae' AND is_placeholder = 1"
            ") AND o.opinion_type = 'SPELLING_OF'"
        )
        row = cursor.fetchone()
        conn.close()
        assert row is not None, "SPELLING_OF opinion for Chengkouaspidae not found"
        assert row[0] == 'SPELLING_OF'
        assert row[1] == 36   # Chengkouaspididae
        assert row[2] == 1    # is_accepted
        assert row[3] == 'Chengkouaspididae'

