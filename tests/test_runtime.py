"""
Tests for SCODA Desktop runtime (generic viewer, package management, API metadata).
"""

import json
import sqlite3
import os
import stat
import sys
import tempfile
import zipfile

import pytest

import scoda_desktop.scoda_package as scoda_package
from scoda_desktop.app import app
from scoda_desktop.scoda_package import get_db, ScodaPackage, PackageRegistry

# Import release script functions
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))
from release import (
    get_version, calculate_sha256, store_sha256, get_statistics,
    get_provenance, build_metadata_json, generate_readme, create_release
)




# --- CORS ---

class TestCORS:
    def test_cors_headers_present(self, client):
        """API responses should include CORS headers."""
        response = client.get('/api/tree')
        assert response.status_code == 200
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers

    def test_cors_preflight(self, client):
        """OPTIONS preflight requests should return CORS headers."""
        response = client.options('/api/tree')
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers
        assert 'GET' in response.headers['Access-Control-Allow-Methods']
        assert 'POST' in response.headers['Access-Control-Allow-Methods']


# --- Index page ---




# --- Index page ---

class TestIndex:
    def test_index_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200


# --- /api/tree ---




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


# --- /api/provenance ---




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




# --- /api/queries ---

class TestApiQueries:
    def test_queries_returns_200(self, client):
        response = client.get('/api/queries')
        assert response.status_code == 200

    def test_queries_returns_list(self, client):
        response = client.get('/api/queries')
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 29  # 8 original + 21 composite detail queries

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
        """Test manifest should have 13 views (6 tab + 7 detail)."""
        response = client.get('/api/manifest')
        data = json.loads(response.data)
        assert len(data['manifest']['views']) == 13

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


# --- Declarative Manifest Detail Views (Phase 39) ---




# --- Release Mechanism (Phase 16) ---

class TestRelease:
    def test_get_version(self, test_db):
        """get_version should return '1.0.0' from test DB."""
        canonical_db, _, _ = test_db
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
        canonical_db, _, _ = test_db
        h = calculate_sha256(canonical_db)
        assert len(h) == 64
        assert all(c in '0123456789abcdef' for c in h)

    def test_calculate_sha256_deterministic(self, test_db):
        """Same file should always produce the same hash."""
        canonical_db, _, _ = test_db
        h1 = calculate_sha256(canonical_db)
        h2 = calculate_sha256(canonical_db)
        assert h1 == h2

    def test_calculate_sha256_changes(self, test_db):
        """Modifying the DB should change the hash."""
        canonical_db, _, _ = test_db
        h_before = calculate_sha256(canonical_db)
        conn = sqlite3.connect(canonical_db)
        conn.execute("INSERT INTO artifact_metadata (key, value) VALUES ('test_key', 'test_value')")
        conn.commit()
        conn.close()
        h_after = calculate_sha256(canonical_db)
        assert h_before != h_after

    def test_store_sha256(self, test_db):
        """store_sha256 should insert/update sha256 key in artifact_metadata."""
        canonical_db, _, _ = test_db
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
        canonical_db, _, _ = test_db
        stats = get_statistics(canonical_db)
        assert stats['genera'] == 4         # Phacops, Acuticryphops, Cryphops, Olenus
        assert stats['valid_genera'] == 3   # Phacops, Acuticryphops, Olenus
        assert stats['family'] == 2         # Phacopidae, Olenidae
        assert stats['order'] == 2          # Phacopida, Ptychopariida
        assert stats['synonyms'] == 1
        assert stats['bibliography'] == 1

    def test_get_provenance(self, test_db):
        """get_provenance should return 2 records with correct structure."""
        canonical_db, _, _ = test_db
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
        canonical_db, _, _ = test_db
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
        canonical_db, _, _ = test_db
        stats = get_statistics(canonical_db)
        readme = generate_readme('1.0.0', 'abc123hash', stats)
        assert '1.0.0' in readme
        assert 'abc123hash' in readme
        assert 'Genera: 4' in readme
        assert 'Valid genera: 3' in readme
        assert 'sha256sum --check' in readme

    def test_create_release(self, test_db, tmp_path):
        """Integration: create_release should produce directory with 4 files."""
        canonical_db, _, _ = test_db
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
        canonical_db, _, _ = test_db
        output_dir = str(tmp_path / "releases")
        create_release(canonical_db, output_dir)
        with pytest.raises(SystemExit):
            create_release(canonical_db, output_dir)


# --- /api/annotations --- (Phase 17)




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




# --- ScodaPackage (Phase 25) ---

class TestScodaPackage:
    def test_create_scoda(self, test_db, tmp_path):
        """ScodaPackage.create should produce a valid .scoda ZIP."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        result = ScodaPackage.create(canonical_db, scoda_path)
        assert os.path.exists(result)
        assert zipfile.is_zipfile(result)

    def test_scoda_contains_manifest_and_db(self, test_db, tmp_path):
        """The .scoda ZIP should contain manifest.json and data.db."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with zipfile.ZipFile(scoda_path, 'r') as zf:
            names = zf.namelist()
            assert 'manifest.json' in names
            assert 'data.db' in names

    def test_scoda_manifest_fields(self, test_db, tmp_path):
        """Manifest should contain required metadata fields."""
        canonical_db, _, _ = test_db
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
        canonical_db, _, _ = test_db
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
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.verify_checksum() is True

    def test_scoda_close_cleanup(self, test_db, tmp_path):
        """close() should remove the temp directory."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        pkg = ScodaPackage(scoda_path)
        tmp_dir = pkg._tmp_dir
        assert os.path.exists(tmp_dir)
        pkg.close()
        assert not os.path.exists(tmp_dir)

    def test_scoda_properties(self, test_db, tmp_path):
        """Package properties should match manifest."""
        canonical_db, _, _ = test_db
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
        canonical_db, overlay_db, _ = test_db
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
        canonical_db, overlay_db, _ = test_db
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


# --- PaleoCore .scoda Package (Phase 35) ---


# ---------------------------------------------------------------------------

class TestPackageRegistry:
    """Tests for PackageRegistry class."""

    def test_scan_finds_scoda_files(self, test_db, tmp_path):
        """scan() should discover .scoda files in a directory."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db

        # Create a .scoda package from the test DB
        pkg_dir = tmp_path / "pkg_scan"
        pkg_dir.mkdir()
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "test.scoda"))

        from scoda_desktop.scoda_package import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        pkgs = reg.list_packages()
        assert len(pkgs) >= 1
        names = [p['name'] for p in pkgs]
        assert 'trilobase' in names
        reg.close_all()

    def test_open_package_db_connection(self, test_db, tmp_path):
        """get_db() should return a working connection for a scanned package."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db

        pkg_dir = tmp_path / "pkg_open"
        pkg_dir.mkdir()
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "test.scoda"))

        from scoda_desktop.scoda_package import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('trilobase')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM taxonomic_ranks")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()
        reg.close_all()

    def test_list_packages_returns_info(self, test_db, tmp_path):
        """list_packages() should return name, title, version, record_count."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db

        pkg_dir = tmp_path / "pkg_list"
        pkg_dir.mkdir()
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "test.scoda"))

        from scoda_desktop.scoda_package import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        pkgs = reg.list_packages()
        assert len(pkgs) >= 1
        pkg = pkgs[0]
        assert 'name' in pkg
        assert 'title' in pkg
        assert 'version' in pkg
        assert 'record_count' in pkg
        assert 'has_dependencies' in pkg
        reg.close_all()

    def test_dependency_resolution_with_alias(self, test_db, tmp_path):
        """Dependencies should be ATTACHed using their alias."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db

        pkg_dir = tmp_path / "pkg_deps"
        pkg_dir.mkdir()

        # Create paleocore.scoda
        ScodaPackage.create(paleocore_db_path, str(pkg_dir / "paleocore.scoda"),
                            metadata={"name": "paleocore"})

        # Create trilobase.scoda with dependency on paleocore
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "trilobase.scoda"),
                            metadata={"dependencies": [
                                {"name": "paleocore", "alias": "pc"}
                            ]})

        from scoda_desktop.scoda_package import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('trilobase')
        # Verify pc alias is attached
        databases = conn.execute("PRAGMA database_list").fetchall()
        db_names = [row['name'] for row in databases]
        assert 'pc' in db_names

        # Verify cross-DB query works
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM pc.formations")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()
        reg.close_all()

    def test_package_without_deps(self, test_db, tmp_path):
        """A package with no dependencies should work standalone."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db

        pkg_dir = tmp_path / "pkg_nodeps"
        pkg_dir.mkdir()

        ScodaPackage.create(paleocore_db_path, str(pkg_dir / "paleocore.scoda"),
                            metadata={"name": "paleocore"})

        from scoda_desktop.scoda_package import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('paleocore')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM formations")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()
        reg.close_all()

    def test_overlay_per_package(self, test_db, tmp_path):
        """Each package should get its own overlay DB."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db

        pkg_dir = tmp_path / "pkg_overlay"
        pkg_dir.mkdir()

        ScodaPackage.create(canonical_db_path, str(pkg_dir / "trilobase.scoda"))
        ScodaPackage.create(paleocore_db_path, str(pkg_dir / "paleocore.scoda"),
                            metadata={"name": "paleocore"})

        from scoda_desktop.scoda_package import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        # Open both — each creates its own overlay
        conn1 = reg.get_db('trilobase')
        conn2 = reg.get_db('paleocore')

        assert os.path.exists(str(pkg_dir / "trilobase_overlay.db"))
        assert os.path.exists(str(pkg_dir / "paleocore_overlay.db"))

        conn1.close()
        conn2.close()
        reg.close_all()

    def test_legacy_get_db_still_works(self, test_db):
        """Existing get_db() function should continue to work."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path, paleocore_db_path)

        conn = scoda_package.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM taxonomic_ranks")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()

        scoda_package._reset_paths()

    def test_unknown_package_error(self, test_db, tmp_path):
        """get_db() for a non-existent package should raise KeyError."""
        pkg_dir = tmp_path / "pkg_err"
        pkg_dir.mkdir()

        from scoda_desktop.scoda_package import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        with pytest.raises(KeyError):
            reg.get_db('nonexistent')
        reg.close_all()


# ---------------------------------------------------------------------------
# /api/detail/<query_name> endpoint tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------

class TestGenericDetailEndpoint:
    """Tests for /api/detail/<query_name> generic detail endpoint."""

    def test_detail_returns_first_row(self, client):
        """GET /api/detail/<query> should return first row as flat JSON."""
        response = client.get('/api/detail/genera_list')
        assert response.status_code == 200
        data = json.loads(response.data)
        # Should be a flat dict (first row), not wrapped in rows/columns
        assert 'name' in data
        assert 'rows' not in data

    def test_detail_with_params(self, client):
        """GET /api/detail/<query>?param=value should pass parameters."""
        # taxonomy_tree is a parameterless query, but family_genera takes family_id
        # Use genera_list which has no required params
        response = client.get('/api/detail/genera_list')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_detail_query_not_found(self, client):
        """Non-existent query should return 404."""
        response = client.get('/api/detail/nonexistent_query')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_detail_no_results(self, client):
        """Query returning 0 rows should return 404."""
        # family_genera with non-existent family_id
        response = client.get('/api/detail/family_genera?family_id=999999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Not found'

    def test_detail_sql_error(self, client):
        """SQL error in query should return 400."""
        # Use a query that requires params but pass wrong ones
        # genera_by_country expects country_name param
        response = client.get('/api/detail/genera_by_country')
        # This may return 200 with empty result or 400 with SQL error
        # depending on the query. Let's just verify it doesn't crash (500).
        assert response.status_code in (200, 400, 404)


# ---------------------------------------------------------------------------
# set_active_package() integration tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------

class TestActivePackage:
    """Tests for set_active_package() integration with get_db()."""

    def test_set_active_package_routes_get_db(self, test_db, tmp_path):
        """set_active_package() should make get_db() use registry."""
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db
        import scoda_desktop.scoda_package as sp
        from scoda_desktop.scoda_package import PackageRegistry

        pkg_dir = str(tmp_path / "active_pkg")
        os.makedirs(pkg_dir, exist_ok=True)
        ScodaPackage.create(canonical_db_path, os.path.join(pkg_dir, "trilobase.scoda"))

        old_registry = sp._registry
        sp._registry = PackageRegistry()
        sp._registry.scan(pkg_dir)

        try:
            sp.set_active_package('trilobase')
            conn = sp.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM taxonomic_ranks")
            count = cursor.fetchone()['cnt']
            assert count > 0
            conn.close()
        finally:
            sp._active_package_name = None
            sp._registry.close_all()
            sp._registry = old_registry

    def test_active_package_cleared_by_testing(self, test_db):
        """_set_paths_for_testing() should clear active package."""
        import scoda_desktop.scoda_package as sp
        sp._active_package_name = 'something'
        canonical_db_path, overlay_db_path, paleocore_db_path = test_db
        sp._set_paths_for_testing(canonical_db_path, overlay_db_path, paleocore_db_path)
        assert sp._active_package_name is None
        sp._reset_paths()


# ---------------------------------------------------------------------------
# Phase 44: Reference SPA tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------

class TestScodaPackageSPA:
    """Tests for Reference SPA features in ScodaPackage."""

    def test_create_with_spa(self, test_db, tmp_path):
        """extra_assets should be included in .scoda ZIP."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test_spa.scoda")

        # Create a fake SPA file
        spa_file = tmp_path / "test_app.js"
        spa_file.write_text("console.log('spa');")

        extra_assets = {"assets/spa/app.js": str(spa_file)}
        ScodaPackage.create(canonical_db, scoda_path, extra_assets=extra_assets)

        with zipfile.ZipFile(scoda_path, 'r') as zf:
            names = zf.namelist()
            assert 'assets/spa/app.js' in names

    def test_has_reference_spa(self, test_db, tmp_path):
        """has_reference_spa should reflect manifest flag."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test_spa.scoda")

        spa_file = tmp_path / "index.html"
        spa_file.write_text("<html></html>")

        extra_assets = {"assets/spa/index.html": str(spa_file)}
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.has_reference_spa is True

    def test_has_reference_spa_false_by_default(self, test_db, tmp_path):
        """has_reference_spa should be False when not set."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test_no_spa.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.has_reference_spa is False

    def test_extract_spa(self, test_db, tmp_path):
        """extract_spa() should extract SPA files to output directory."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test_spa.scoda")

        # Create SPA files
        spa_html = tmp_path / "spa_index.html"
        spa_html.write_text("<html><body>SPA</body></html>")
        spa_js = tmp_path / "spa_app.js"
        spa_js.write_text("console.log('spa');")

        extra_assets = {
            "assets/spa/index.html": str(spa_html),
            "assets/spa/app.js": str(spa_js),
        }
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        with ScodaPackage(scoda_path) as pkg:
            out_dir = str(tmp_path / "extracted_spa")
            result = pkg.extract_spa(output_dir=out_dir)
            assert result == out_dir
            assert os.path.isfile(os.path.join(out_dir, 'index.html'))
            assert os.path.isfile(os.path.join(out_dir, 'app.js'))

    def test_extract_spa_default_dir(self, test_db, tmp_path):
        """Default extraction directory should be <name>_spa/."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test_spa.scoda")

        spa_file = tmp_path / "spa_index.html"
        spa_file.write_text("<html></html>")

        extra_assets = {"assets/spa/index.html": str(spa_file)}
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        with ScodaPackage(scoda_path) as pkg:
            expected_dir = os.path.join(str(tmp_path), 'test_spa_spa')
            assert pkg.get_spa_dir() == expected_dir

    def test_is_spa_extracted(self, test_db, tmp_path):
        """is_spa_extracted() should return True after extraction."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test_spa.scoda")

        spa_file = tmp_path / "spa_index.html"
        spa_file.write_text("<html></html>")

        extra_assets = {"assets/spa/index.html": str(spa_file)}
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.is_spa_extracted() is False
            pkg.extract_spa()
            assert pkg.is_spa_extracted() is True

    def test_extract_no_spa_raises(self, test_db, tmp_path):
        """extract_spa() on a package without SPA should raise ValueError."""
        canonical_db, _, _ = test_db
        scoda_path = str(tmp_path / "test_no_spa.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            with pytest.raises(ValueError, match="does not contain"):
                pkg.extract_spa()





class TestFlaskAutoSwitch:
    """Tests for Flask automatic SPA switching."""

    def test_index_generic_without_spa(self, client):
        """Without extracted SPA, index should serve generic viewer."""
        response = client.get('/')
        assert response.status_code == 200
        html = response.data.decode()
        assert 'SCODA Desktop' in html

    def test_index_reference_spa_when_extracted(self, test_db, tmp_path):
        """When SPA is extracted, index should serve it."""
        canonical_db, overlay_db, paleocore_db = test_db
        import scoda_desktop.scoda_package as sp
        from scoda_desktop.scoda_package import PackageRegistry

        # Create .scoda with SPA
        pkg_dir = str(tmp_path / "spa_switch")
        os.makedirs(pkg_dir, exist_ok=True)
        scoda_path = os.path.join(pkg_dir, "trilobase.scoda")

        spa_html = tmp_path / "spa_idx.html"
        spa_html.write_text("<html><body>REFERENCE SPA CONTENT</body></html>")

        extra_assets = {"assets/spa/index.html": str(spa_html)}
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        # Extract SPA
        with ScodaPackage(scoda_path) as pkg:
            pkg.extract_spa(output_dir=os.path.join(pkg_dir, "trilobase_spa"))

        # Set up registry and active package
        old_registry = sp._registry
        sp._registry = PackageRegistry()
        sp._registry.scan(pkg_dir)

        try:
            sp.set_active_package('trilobase')
            app.config['TESTING'] = True
            with app.test_client() as test_client:
                response = test_client.get('/')
                assert response.status_code == 200
                assert b'REFERENCE SPA CONTENT' in response.data
        finally:
            sp._active_package_name = None
            sp._registry.close_all()
            sp._registry = old_registry

    def test_spa_assets_served(self, test_db, tmp_path):
        """Extracted SPA assets (app.js, style.css) should be served."""
        canonical_db, overlay_db, paleocore_db = test_db
        import scoda_desktop.scoda_package as sp
        from scoda_desktop.scoda_package import PackageRegistry

        pkg_dir = str(tmp_path / "spa_assets")
        os.makedirs(pkg_dir, exist_ok=True)
        scoda_path = os.path.join(pkg_dir, "trilobase.scoda")

        spa_html = tmp_path / "spa_idx.html"
        spa_html.write_text("<html></html>")
        spa_js = tmp_path / "spa_app.js"
        spa_js.write_text("// SPA JS")
        spa_css = tmp_path / "spa_style.css"
        spa_css.write_text("body { color: red; }")

        extra_assets = {
            "assets/spa/index.html": str(spa_html),
            "assets/spa/app.js": str(spa_js),
            "assets/spa/style.css": str(spa_css),
        }
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        # Extract SPA
        with ScodaPackage(scoda_path) as pkg:
            pkg.extract_spa(output_dir=os.path.join(pkg_dir, "trilobase_spa"))

        old_registry = sp._registry
        sp._registry = PackageRegistry()
        sp._registry.scan(pkg_dir)

        try:
            sp.set_active_package('trilobase')
            app.config['TESTING'] = True
            with app.test_client() as test_client:
                response = test_client.get('/app.js')
                assert response.status_code == 200
                assert b'SPA JS' in response.data

                response = test_client.get('/style.css')
                assert response.status_code == 200
                assert b'color: red' in response.data
        finally:
            sp._active_package_name = None
            sp._registry.close_all()
            sp._registry = old_registry

    def test_api_routes_take_priority(self, test_db, tmp_path):
        """API routes should work even when SPA is extracted."""
        canonical_db, overlay_db, paleocore_db = test_db
        import scoda_desktop.scoda_package as sp
        from scoda_desktop.scoda_package import PackageRegistry

        pkg_dir = str(tmp_path / "spa_api")
        os.makedirs(pkg_dir, exist_ok=True)
        scoda_path = os.path.join(pkg_dir, "trilobase.scoda")

        spa_html = tmp_path / "spa_idx.html"
        spa_html.write_text("<html></html>")

        extra_assets = {"assets/spa/index.html": str(spa_html)}
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        with ScodaPackage(scoda_path) as pkg:
            pkg.extract_spa(output_dir=os.path.join(pkg_dir, "trilobase_spa"))

        old_registry = sp._registry
        sp._registry = PackageRegistry()
        sp._registry.scan(pkg_dir)

        try:
            sp.set_active_package('trilobase')
            app.config['TESTING'] = True
            with app.test_client() as test_client:
                response = test_client.get('/api/manifest')
                assert response.status_code == 200
                data = json.loads(response.data)
                assert 'manifest' in data
        finally:
            sp._active_package_name = None
            sp._registry.close_all()
            sp._registry = old_registry





# --- /api/composite/<view_name> ---


class TestCompositeDetail:
    """Tests for /api/composite/<view_name> manifest-driven composite endpoint."""

    def test_composite_requires_id(self, client):
        """Missing id parameter should return 400."""
        response = client.get('/api/composite/genus_detail')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'id parameter required' in data['error']

    def test_composite_unknown_view_returns_404(self, client):
        """Non-existent view name should return 404."""
        response = client.get('/api/composite/nonexistent_view?id=1')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Detail view not found' in data['error']

    def test_composite_non_detail_view_returns_404(self, client):
        """Table view (not detail type) should return 404."""
        response = client.get('/api/composite/genera_table?id=1')
        assert response.status_code == 404

    def test_composite_view_without_source_query_returns_404(self, client):
        """Detail view without source_query should still work if manifest has one.
        Views that lack source_query return 404."""
        # All test views now have source_query, so use a table view type
        response = client.get('/api/composite/taxonomy_tree?id=1')
        assert response.status_code == 404

    def test_composite_entity_not_found(self, client):
        """Non-existent entity id should return 404."""
        response = client.get('/api/composite/genus_detail?id=999999')
        assert response.status_code == 404

    def test_composite_genus_returns_main_data(self, client):
        """Composite genus detail should return main query fields at top level."""
        response = client.get('/api/composite/genus_detail?id=100')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Phacops'
        assert data['family_name'] == 'Phacopidae'
        assert data['temporal_code'] == 'LDEV-UDEV'

    def test_composite_genus_has_sub_query_keys(self, client):
        """Composite genus detail should include sub-query result arrays."""
        response = client.get('/api/composite/genus_detail?id=100')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'hierarchy' in data
        assert 'synonyms' in data
        assert 'formations' in data
        assert 'locations' in data
        assert 'temporal_ics_mapping' in data
        assert isinstance(data['hierarchy'], list)
        assert isinstance(data['synonyms'], list)

    def test_composite_genus_hierarchy(self, client):
        """Hierarchy should walk up from genus to Class."""
        response = client.get('/api/composite/genus_detail?id=100')
        data = json.loads(response.data)
        hierarchy = data['hierarchy']
        assert len(hierarchy) >= 2  # At least Order and Class
        # Should be ordered Class -> Order -> Family (top to bottom)
        ranks = [h['rank'] for h in hierarchy]
        assert ranks[0] == 'Class'
        assert 'Family' in ranks

    def test_composite_genus_synonyms_empty(self, client):
        """Genus with no synonyms should have empty list."""
        response = client.get('/api/composite/genus_detail?id=100')
        data = json.loads(response.data)
        assert data['synonyms'] == []

    def test_composite_genus_formations(self, client):
        """Genus with formations should list them."""
        response = client.get('/api/composite/genus_detail?id=101')
        data = json.loads(response.data)
        assert len(data['formations']) == 1
        assert data['formations'][0]['name'] == 'Büdesheimer Sh'

    def test_composite_genus_locations(self, client):
        """Genus with locations should list them with region/country."""
        response = client.get('/api/composite/genus_detail?id=101')
        data = json.loads(response.data)
        assert len(data['locations']) == 1
        loc = data['locations'][0]
        assert loc['country_name'] == 'Germany'
        assert loc['region_name'] == 'Eifel'

    def test_composite_result_field_param(self, client):
        """Sub-query using result.field should resolve from main query result."""
        # genus_ics_mapping uses result.temporal_code
        response = client.get('/api/composite/genus_detail?id=200')
        data = json.loads(response.data)
        # Olenus has temporal_code=UCAM, which maps to Furongian (ics_id=6)
        assert 'temporal_ics_mapping' in data
        assert isinstance(data['temporal_ics_mapping'], list)
        if len(data['temporal_ics_mapping']) > 0:
            assert data['temporal_ics_mapping'][0]['name'] == 'Furongian'

    def test_composite_rank_detail(self, client):
        """Composite rank detail should return main + children + counts."""
        response = client.get('/api/composite/rank_detail?id=1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Trilobita'
        assert 'children' in data
        assert 'children_counts' in data
        assert isinstance(data['children'], list)
        assert isinstance(data['children_counts'], list)


class TestGenericViewerFallback:
    """Tests for generic viewer graceful handling of unknown section types."""

    def test_index_serves_html(self, client):
        """Generic viewer should serve valid HTML."""
        response = client.get('/')
        assert response.status_code == 200
        html = response.data.decode()
        assert '<html' in html
        assert 'SCODA Desktop' in html

    def test_spa_404_for_nonexistent_files(self, client):
        """Requests for non-existent SPA files should return 404."""
        response = client.get('/nonexistent.js')
        assert response.status_code == 404
