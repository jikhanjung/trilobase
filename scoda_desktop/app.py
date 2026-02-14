"""
Trilobase Web Interface
Flask application for browsing trilobite taxonomy database
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import os
import sqlite3

from .scoda_package import get_db, get_paleocore_db_path, get_registry, get_active_package_name

app = Flask(__name__)

VALID_ENTITY_TYPES = {'genus', 'family', 'order', 'suborder', 'superfamily', 'class'}
VALID_ANNOTATION_TYPES = {'note', 'correction', 'alternative', 'link'}


@app.after_request
def add_cors_headers(response):
    """Allow cross-origin requests for custom SPA support."""
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    return response


# ---------------------------------------------------------------------------
# Core helper functions (shared by legacy and namespaced routes)
# ---------------------------------------------------------------------------

def _fetch_manifest(conn):
    """Fetch UI manifest from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, description, manifest_json, created_at
        FROM ui_manifest
        WHERE name = 'default'
    """)
    row = cursor.fetchone()
    if not row:
        return None

    # Include package info from artifact_metadata
    cursor.execute("SELECT key, value FROM artifact_metadata")
    meta = {r['key']: r['value'] for r in cursor.fetchall()}

    return {
        'name': row['name'],
        'description': row['description'],
        'manifest': json.loads(row['manifest_json']),
        'created_at': row['created_at'],
        'package': {
            'name': meta.get('name', ''),
            'artifact_id': meta.get('artifact_id', ''),
            'version': meta.get('version', ''),
            'description': meta.get('description', ''),
        }
    }


def _fetch_metadata(conn):
    """Fetch artifact metadata from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM artifact_metadata")
    return {row['key']: row['value'] for row in cursor.fetchall()}


def _fetch_provenance(conn):
    """Fetch provenance from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, source_type, citation, description, year, url
        FROM provenance ORDER BY id
    """)
    return [{
        'id': s['id'],
        'source_type': s['source_type'],
        'citation': s['citation'],
        'description': s['description'],
        'year': s['year'],
        'url': s['url']
    } for s in cursor.fetchall()]


def _fetch_display_intent(conn):
    """Fetch display intent from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, entity, default_view, description, source_query, priority
        FROM ui_display_intent ORDER BY entity, priority
    """)
    return [{
        'id': i['id'],
        'entity': i['entity'],
        'default_view': i['default_view'],
        'description': i['description'],
        'source_query': i['source_query'],
        'priority': i['priority']
    } for i in cursor.fetchall()]


def _fetch_queries(conn):
    """Fetch named queries list from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, description, params_json, created_at
        FROM ui_queries ORDER BY name
    """)
    return [{
        'id': q['id'],
        'name': q['name'],
        'description': q['description'],
        'params': q['params_json'],
        'created_at': q['created_at']
    } for q in cursor.fetchall()]


def _execute_query(conn, query_name, params):
    """Execute a named query and return result dict or error tuple."""
    cursor = conn.cursor()
    cursor.execute("SELECT sql, params_json FROM ui_queries WHERE name = ?", (query_name,))
    query = cursor.fetchone()
    if not query:
        return None
    try:
        cursor.execute(query['sql'], params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return {
            'query': query_name,
            'columns': columns,
            'row_count': len(rows),
            'rows': [dict(row) for row in rows]
        }
    except Exception as e:
        return {'error': str(e)}


def _fetch_annotations(conn, entity_type, entity_id):
    """Fetch annotations for an entity."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY created_at DESC, id DESC
    """, (entity_type, entity_id))
    return [{
        'id': a['id'],
        'entity_type': a['entity_type'],
        'entity_id': a['entity_id'],
        'entity_name': a['entity_name'],
        'annotation_type': a['annotation_type'],
        'content': a['content'],
        'author': a['author'],
        'created_at': a['created_at']
    } for a in cursor.fetchall()]


def _create_annotation(conn, data):
    """Create an annotation. Returns (result_dict, status_code)."""
    entity_type = data.get('entity_type')
    entity_id = data.get('entity_id')
    annotation_type = data.get('annotation_type')
    content = data.get('content')
    author = data.get('author')

    if not content:
        return {'error': 'content is required'}, 400
    if entity_type not in VALID_ENTITY_TYPES:
        return {'error': f'Invalid entity_type. Must be one of: {", ".join(sorted(VALID_ENTITY_TYPES))}'}, 400
    if annotation_type not in VALID_ANNOTATION_TYPES:
        return {'error': f'Invalid annotation_type. Must be one of: {", ".join(sorted(VALID_ANNOTATION_TYPES))}'}, 400

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM taxonomic_ranks WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        entity_name = row['name'] if row else None
    except Exception:
        entity_name = None

    cursor.execute("""
        INSERT INTO overlay.user_annotations (entity_type, entity_id, entity_name, annotation_type, content, author)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (entity_type, entity_id, entity_name, annotation_type, content, author))
    conn.commit()

    annotation_id = cursor.lastrowid
    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations WHERE id = ?
    """, (annotation_id,))
    annotation = cursor.fetchone()

    return {
        'id': annotation['id'],
        'entity_type': annotation['entity_type'],
        'entity_id': annotation['entity_id'],
        'entity_name': annotation['entity_name'],
        'annotation_type': annotation['annotation_type'],
        'content': annotation['content'],
        'author': annotation['author'],
        'created_at': annotation['created_at']
    }, 201


def _delete_annotation(conn, annotation_id):
    """Delete an annotation. Returns (result_dict, status_code)."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    if not cursor.fetchone():
        return {'error': 'Annotation not found'}, 404

    cursor.execute("DELETE FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    return {'message': 'Annotation deleted', 'id': annotation_id}, 200


# ---------------------------------------------------------------------------
# Generic detail endpoint (named query → first row as flat JSON)
# ---------------------------------------------------------------------------

@app.route('/api/detail/<query_name>')
def api_generic_detail(query_name):
    """Execute a named query and return the first row as flat JSON."""
    conn = get_db()
    params = {k: v for k, v in request.args.items()}
    result = _execute_query(conn, query_name, params)
    conn.close()
    if result is None:
        return jsonify({'error': f'Query not found: {query_name}'}), 404
    if 'error' in result:
        return jsonify(result), 400
    if result['row_count'] == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(result['rows'][0])


@app.route('/api/composite/<view_name>')
def api_composite_detail(view_name):
    """Execute manifest-defined composite detail query."""
    entity_id = request.args.get('id')
    if not entity_id:
        return jsonify({'error': 'id parameter required'}), 400

    conn = get_db()
    manifest_data = _fetch_manifest(conn)
    if not manifest_data:
        conn.close()
        return jsonify({'error': 'No manifest found'}), 404

    views = manifest_data['manifest'].get('views', {})
    view = views.get(view_name)
    if not view or view.get('type') != 'detail' or 'source_query' not in view:
        conn.close()
        return jsonify({'error': f'Detail view not found: {view_name}'}), 404

    # Main query
    source_param = view.get('source_param', 'id')
    result = _execute_query(conn, view['source_query'], {source_param: entity_id})
    if result is None or result.get('row_count', 0) == 0:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    if 'error' in result:
        conn.close()
        return jsonify(result), 400

    data = dict(result['rows'][0])

    # Sub-queries
    for key, sub_def in view.get('sub_queries', {}).items():
        params = {}
        for param_name, value_source in sub_def.get('params', {}).items():
            if value_source == 'id':
                params[param_name] = entity_id
            elif value_source.startswith('result.'):
                field = value_source[7:]
                params[param_name] = data.get(field, '')
            else:
                params[param_name] = value_source
        sub_result = _execute_query(conn, sub_def['query'], params)
        data[key] = sub_result['rows'] if sub_result and 'rows' in sub_result else []

    conn.close()
    return jsonify(data)


# ---------------------------------------------------------------------------
# Legacy routes (unchanged API surface)
# ---------------------------------------------------------------------------

def build_tree(parent_id=None):
    """Recursively build taxonomy tree (Class to Family)"""
    conn = get_db()
    cursor = conn.cursor()

    if parent_id is None:
        # Start with Class (root)
        cursor.execute("""
            SELECT id, name, rank, author, genera_count
            FROM taxonomic_ranks
            WHERE rank = 'Class'
        """)
    else:
        # Get children of parent
        cursor.execute("""
            SELECT id, name, rank, author, genera_count
            FROM taxonomic_ranks
            WHERE parent_id = ? AND rank != 'Genus'
            ORDER BY name
        """, (parent_id,))

    rows = cursor.fetchall()
    result = []

    for row in rows:
        node = {
            'id': row['id'],
            'name': row['name'],
            'rank': row['rank'],
            'author': row['author'],
            'genera_count': row['genera_count'] or 0,
            'children': build_tree(row['id'])
        }
        result.append(node)

    conn.close()
    return result


def _get_reference_spa_dir():
    """Check if a Reference SPA has been extracted for the active package.

    Returns the SPA directory path if extracted, None otherwise.
    """
    pkg_name = get_active_package_name()
    if not pkg_name:
        return None
    try:
        registry = get_registry()
        entry = registry.get_package(pkg_name)
        pkg = entry.get('manifest')
        if not pkg or not pkg.get('has_reference_spa'):
            return None
        # Look for <name>_spa/ directory next to the .scoda file
        scoda_path = entry.get('db_path')
        if not scoda_path:
            return None
        # The scan dir is where .scoda files live
        scan_dir = registry._scan_dir
        if not scan_dir:
            return None
        spa_dir = os.path.join(scan_dir, f'{pkg_name}_spa')
        if os.path.isdir(spa_dir) and os.path.isfile(os.path.join(spa_dir, 'index.html')):
            return spa_dir
    except (KeyError, AttributeError):
        pass
    return None


@app.route('/')
def index():
    """Main page — serve Reference SPA if extracted, otherwise generic viewer."""
    spa_dir = _get_reference_spa_dir()
    if spa_dir:
        return send_from_directory(spa_dir, 'index.html')
    return render_template('index.html')


@app.route('/api/tree')
def api_tree():
    """Get full taxonomy tree (Class to Family)"""
    tree = build_tree()
    return jsonify(tree)


@app.route('/api/family/<int:family_id>/genera')
def api_family_genera(family_id):
    """Get genera list for a specific family"""
    conn = get_db()
    cursor = conn.cursor()

    # Get family info
    cursor.execute("""
        SELECT id, name, author, genera_count
        FROM taxonomic_ranks
        WHERE id = ? AND rank = 'Family'
    """, (family_id,))
    family = cursor.fetchone()

    if not family:
        conn.close()
        return jsonify({'error': 'Family not found'}), 404

    # Get genera
    cursor.execute("""
        SELECT id, name, author, year, type_species, location, is_valid
        FROM taxonomic_ranks
        WHERE parent_id = ? AND rank = 'Genus'
        ORDER BY name
    """, (family_id,))
    genera = cursor.fetchall()

    conn.close()

    return jsonify({
        'family': {
            'id': family['id'],
            'name': family['name'],
            'author': family['author'],
            'genera_count': family['genera_count']
        },
        'genera': [{
            'id': g['id'],
            'name': g['name'],
            'author': g['author'],
            'year': g['year'],
            'type_species': g['type_species'],
            'location': g['location'],
            'is_valid': g['is_valid']
        } for g in genera]
    })


@app.route('/api/rank/<int:rank_id>')
def api_rank_detail(rank_id):
    """Get detailed info for a taxonomic rank (Class, Order, etc.)"""
    conn = get_db()
    cursor = conn.cursor()

    # Get rank info
    cursor.execute("""
        SELECT tr.*,
               parent.name as parent_name,
               parent.rank as parent_rank
        FROM taxonomic_ranks tr
        LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id
        WHERE tr.id = ?
    """, (rank_id,))
    rank = cursor.fetchone()

    if not rank:
        conn.close()
        return jsonify({'error': 'Rank not found'}), 404

    # Get children counts by rank
    cursor.execute("""
        SELECT rank, COUNT(*) as count
        FROM taxonomic_ranks
        WHERE parent_id = ?
        GROUP BY rank
    """, (rank_id,))
    children_counts = cursor.fetchall()

    # Get direct children list (limit 20)
    cursor.execute("""
        SELECT id, name, rank, author, genera_count
        FROM taxonomic_ranks
        WHERE parent_id = ?
        ORDER BY name
        LIMIT 20
    """, (rank_id,))
    children = cursor.fetchall()

    conn.close()

    return jsonify({
        'id': rank['id'],
        'name': rank['name'],
        'rank': rank['rank'],
        'author': rank['author'],
        'year': rank['year'],
        'genera_count': rank['genera_count'],
        'notes': rank['notes'],
        'parent_name': rank['parent_name'],
        'parent_rank': rank['parent_rank'],
        'children_counts': [{
            'rank': c['rank'],
            'count': c['count']
        } for c in children_counts],
        'children': [{
            'id': c['id'],
            'name': c['name'],
            'rank': c['rank'],
            'author': c['author']
        } for c in children]
    })


@app.route('/api/genus/<int:genus_id>')
def api_genus_detail(genus_id):
    """Get detailed info for a specific genus"""
    conn = get_db()
    cursor = conn.cursor()

    # Get genus info
    cursor.execute("""
        SELECT tr.*,
               parent.name as family_name
        FROM taxonomic_ranks tr
        LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id
        WHERE tr.id = ? AND tr.rank = 'Genus'
    """, (genus_id,))
    genus = cursor.fetchone()

    if not genus:
        conn.close()
        return jsonify({'error': 'Genus not found'}), 404

    # Build taxonomy hierarchy (walk up parent chain)
    hierarchy = []
    parent_id = genus['parent_id']
    while parent_id:
        cursor.execute("""
            SELECT id, name, rank, author, parent_id
            FROM taxonomic_ranks WHERE id = ?
        """, (parent_id,))
        parent = cursor.fetchone()
        if not parent:
            break
        hierarchy.append({
            'id': parent['id'],
            'name': parent['name'],
            'rank': parent['rank'],
            'author': parent['author']
        })
        parent_id = parent['parent_id']
    hierarchy.reverse()  # Class → Order → ... → Family

    # Get synonyms
    cursor.execute("""
        SELECT s.*,
               senior.name as senior_name
        FROM synonyms s
        LEFT JOIN taxonomic_ranks senior ON s.senior_taxon_id = senior.id
        WHERE s.junior_taxon_id = ?
    """, (genus_id,))
    synonyms = cursor.fetchall()

    # Get formations (via relation table)
    cursor.execute("""
        SELECT f.id, f.name, f.formation_type, f.country, f.period
        FROM genus_formations gf
        JOIN pc.formations f ON gf.formation_id = f.id
        WHERE gf.genus_id = ?
    """, (genus_id,))
    formations = cursor.fetchall()

    # Get locations (via geographic_regions hierarchy)
    cursor.execute("""
        SELECT gr.id as region_id, gr.name as region_name, gr.level,
               parent.id as country_id, parent.name as country_name
        FROM genus_locations gl
        JOIN pc.geographic_regions gr ON gl.region_id = gr.id
        LEFT JOIN pc.geographic_regions parent ON gr.parent_id = parent.id
        WHERE gl.genus_id = ?
    """, (genus_id,))
    locations = cursor.fetchall()

    # Get ICS chronostrat mappings for temporal_code
    temporal_ics = []
    if genus['temporal_code']:
        cursor.execute("""
            SELECT ic.id, ic.name, ic.rank, m.mapping_type
            FROM pc.temporal_ics_mapping m
            JOIN pc.ics_chronostrat ic ON m.ics_id = ic.id
            WHERE m.temporal_code = ?
        """, (genus['temporal_code'],))
        temporal_ics = cursor.fetchall()

    conn.close()

    location_list = []
    for l in locations:
        if l['level'] == 'country':
            # region_id가 country를 직접 가리킴 (region 없음)
            location_list.append({
                'region_id': None,
                'region_name': None,
                'country_id': l['region_id'],
                'country_name': l['region_name']
            })
        else:
            location_list.append({
                'region_id': l['region_id'],
                'region_name': l['region_name'],
                'country_id': l['country_id'],
                'country_name': l['country_name']
            })

    return jsonify({
        'id': genus['id'],
        'name': genus['name'],
        'author': genus['author'],
        'year': genus['year'],
        'year_suffix': genus['year_suffix'],
        'type_species': genus['type_species'],
        'type_species_author': genus['type_species_author'],
        'formation': genus['formation'],
        'location': genus['location'],
        'family': genus['family'],
        'family_name': genus['family_name'],
        'hierarchy': hierarchy,
        'temporal_code': genus['temporal_code'],
        'is_valid': genus['is_valid'],
        'notes': genus['notes'],
        'raw_entry': genus['raw_entry'],
        'synonyms': [{
            'id': s['id'],
            'senior_taxon_id': s['senior_taxon_id'],
            'senior_name': s['senior_name'] or s['senior_taxon_name'],
            'synonym_type': s['synonym_type'],
            'fide_author': s['fide_author'],
            'fide_year': s['fide_year']
        } for s in synonyms],
        'formations': [{
            'id': f['id'],
            'name': f['name'],
            'type': f['formation_type'],
            'country': f['country'],
            'period': f['period']
        } for f in formations],
        'locations': location_list,
        'temporal_ics_mapping': [{
            'id': t['id'],
            'name': t['name'],
            'rank': t['rank'],
            'mapping_type': t['mapping_type']
        } for t in temporal_ics]
    })


@app.route('/api/metadata')
def api_metadata():
    """Get SCODA artifact metadata and database statistics"""
    conn = get_db()
    cursor = conn.cursor()

    # Get metadata key-value pairs
    cursor.execute("SELECT key, value FROM artifact_metadata")
    metadata = {row['key']: row['value'] for row in cursor.fetchall()}

    # Get database statistics
    stats = {}
    for rank in ['Class', 'Order', 'Suborder', 'Superfamily', 'Family', 'Genus']:
        cursor.execute(
            "SELECT COUNT(*) as count FROM taxonomic_ranks WHERE rank = ?",
            (rank,))
        stats[rank.lower()] = cursor.fetchone()['count']

    cursor.execute(
        "SELECT COUNT(*) as count FROM taxonomic_ranks WHERE rank = 'Genus' AND is_valid = 1")
    stats['valid_genera'] = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM synonyms")
    stats['synonyms'] = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM bibliography")
    stats['bibliography'] = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM pc.formations")
    stats['formations'] = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM pc.geographic_regions WHERE level = 'country'")
    stats['countries'] = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM pc.geographic_regions WHERE level = 'region'")
    stats['regions'] = cursor.fetchone()['count']

    # Check PaleoCore availability
    databases = cursor.execute("PRAGMA database_list").fetchall()
    paleocore_attached = 'pc' in [row['name'] for row in databases]

    conn.close()

    metadata['statistics'] = stats
    metadata['paleocore_attached'] = paleocore_attached
    return jsonify(metadata)


@app.route('/api/provenance')
def api_provenance():
    """Get data provenance information"""
    conn = get_db()
    result = _fetch_provenance(conn)
    conn.close()
    return jsonify(result)


@app.route('/api/display-intent')
def api_display_intent():
    """Get display intent hints for SCODA viewers"""
    conn = get_db()
    result = _fetch_display_intent(conn)
    conn.close()
    return jsonify(result)


@app.route('/api/queries')
def api_queries():
    """Get list of available named queries"""
    conn = get_db()
    result = _fetch_queries(conn)
    conn.close()
    return jsonify(result)


@app.route('/api/manifest')
def api_manifest():
    """Get UI manifest with declarative view definitions"""
    conn = get_db()
    result = _fetch_manifest(conn)
    conn.close()
    return jsonify(result) if result else (jsonify({'error': 'No manifest found'}), 404)


@app.route('/api/queries/<name>/execute')
def api_query_execute(name):
    """Execute a named query with optional parameters"""
    conn = get_db()
    params = {key: value for key, value in request.args.items()}
    result = _execute_query(conn, name, params)
    conn.close()
    if result is None:
        return jsonify({'error': f'Query not found: {name}'}), 404
    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route('/api/country/<int:country_id>')
def api_country_detail(country_id):
    """Get detailed info for a country (geographic_regions level='country')"""
    conn = get_db()
    cursor = conn.cursor()

    # Get country from geographic_regions
    cursor.execute("""
        SELECT gr.id, gr.name, gr.level, gr.cow_ccode,
               COUNT(DISTINCT gl.genus_id) as taxa_count
        FROM pc.geographic_regions gr
        LEFT JOIN genus_locations gl ON gl.region_id = gr.id
            OR gl.region_id IN (SELECT id FROM pc.geographic_regions WHERE parent_id = gr.id)
        WHERE gr.id = ? AND gr.level = 'country'
        GROUP BY gr.id
    """, (country_id,))
    country = cursor.fetchone()

    if not country:
        conn.close()
        return jsonify({'error': 'Country not found'}), 404

    # Get child regions
    cursor.execute("""
        SELECT gr.id, gr.name,
               COUNT(DISTINCT gl.genus_id) as taxa_count
        FROM pc.geographic_regions gr
        LEFT JOIN genus_locations gl ON gl.region_id = gr.id
        WHERE gr.parent_id = ? AND gr.level = 'region'
        GROUP BY gr.id
        ORDER BY taxa_count DESC, gr.name
    """, (country_id,))
    regions = cursor.fetchall()

    # Get related genera (country itself + all child regions)
    cursor.execute("""
        SELECT DISTINCT tr.id, tr.name, tr.author, tr.year, tr.is_valid,
               gr.name as region_name, gr.id as region_id
        FROM genus_locations gl
        JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
        JOIN pc.geographic_regions gr ON gl.region_id = gr.id
        WHERE gl.region_id = ? OR gl.region_id IN (
            SELECT id FROM pc.geographic_regions WHERE parent_id = ?
        )
        ORDER BY tr.name
    """, (country_id, country_id))
    genera = cursor.fetchall()

    conn.close()

    return jsonify({
        'id': country['id'],
        'name': country['name'],
        'cow_ccode': country['cow_ccode'],
        'taxa_count': country['taxa_count'],
        'regions': [{
            'id': r['id'],
            'name': r['name'],
            'taxa_count': r['taxa_count']
        } for r in regions],
        'genera': [{
            'id': g['id'],
            'name': g['name'],
            'author': g['author'],
            'year': g['year'],
            'region': g['region_name'],
            'region_id': g['region_id'],
            'is_valid': g['is_valid']
        } for g in genera]
    })


@app.route('/api/region/<int:region_id>')
def api_region_detail(region_id):
    """Get detailed info for a region (geographic_regions level='region')"""
    conn = get_db()
    cursor = conn.cursor()

    # Get region from geographic_regions
    cursor.execute("""
        SELECT gr.id, gr.name, gr.level,
               COUNT(DISTINCT gl.genus_id) as taxa_count,
               parent.id as country_id, parent.name as country_name
        FROM pc.geographic_regions gr
        LEFT JOIN pc.geographic_regions parent ON gr.parent_id = parent.id
        LEFT JOIN genus_locations gl ON gl.region_id = gr.id
        WHERE gr.id = ? AND gr.level = 'region'
        GROUP BY gr.id
    """, (region_id,))
    region = cursor.fetchone()

    if not region:
        conn.close()
        return jsonify({'error': 'Region not found'}), 404

    # Get related genera
    cursor.execute("""
        SELECT tr.id, tr.name, tr.author, tr.year, tr.is_valid
        FROM genus_locations gl
        JOIN taxonomic_ranks tr ON gl.genus_id = tr.id
        WHERE gl.region_id = ?
        ORDER BY tr.name
    """, (region_id,))
    genera = cursor.fetchall()

    conn.close()

    return jsonify({
        'id': region['id'],
        'name': region['name'],
        'taxa_count': region['taxa_count'],
        'parent': {
            'id': region['country_id'],
            'name': region['country_name']
        },
        'genera': [{
            'id': g['id'],
            'name': g['name'],
            'author': g['author'],
            'year': g['year'],
            'is_valid': g['is_valid']
        } for g in genera]
    })


@app.route('/api/chronostrat/<int:ics_id>')
def api_chronostrat_detail(ics_id):
    """Get detailed info for an ICS chronostratigraphic unit"""
    conn = get_db()
    cursor = conn.cursor()

    # Get chronostrat unit
    cursor.execute("""
        SELECT id, name, rank, parent_id, start_mya, start_uncertainty,
               end_mya, end_uncertainty, short_code, color, ratified_gssp
        FROM pc.ics_chronostrat WHERE id = ?
    """, (ics_id,))
    unit = cursor.fetchone()

    if not unit:
        conn.close()
        return jsonify({'error': 'Chronostratigraphic unit not found'}), 404

    # Get parent
    parent = None
    if unit['parent_id']:
        cursor.execute("""
            SELECT id, name, rank FROM pc.ics_chronostrat WHERE id = ?
        """, (unit['parent_id'],))
        p = cursor.fetchone()
        if p:
            parent = {'id': p['id'], 'name': p['name'], 'rank': p['rank']}

    # Get children
    cursor.execute("""
        SELECT id, name, rank, start_mya, end_mya, color
        FROM pc.ics_chronostrat WHERE parent_id = ?
        ORDER BY display_order
    """, (ics_id,))
    children = cursor.fetchall()

    # Get mapped temporal codes
    cursor.execute("""
        SELECT temporal_code, mapping_type
        FROM pc.temporal_ics_mapping WHERE ics_id = ?
        ORDER BY temporal_code
    """, (ics_id,))
    mappings = cursor.fetchall()

    # Get related genera via temporal_ics_mapping
    cursor.execute("""
        SELECT DISTINCT tr.id, tr.name, tr.author, tr.year, tr.is_valid, tr.temporal_code
        FROM pc.temporal_ics_mapping tim
        JOIN taxonomic_ranks tr ON tr.temporal_code = tim.temporal_code
        WHERE tim.ics_id = ? AND tr.rank = 'Genus'
        ORDER BY tr.name
    """, (ics_id,))
    genera = cursor.fetchall()

    conn.close()

    return jsonify({
        'id': unit['id'],
        'name': unit['name'],
        'rank': unit['rank'],
        'start_mya': unit['start_mya'],
        'start_uncertainty': unit['start_uncertainty'],
        'end_mya': unit['end_mya'],
        'end_uncertainty': unit['end_uncertainty'],
        'short_code': unit['short_code'],
        'color': unit['color'],
        'ratified_gssp': unit['ratified_gssp'],
        'parent': parent,
        'children': [{
            'id': c['id'],
            'name': c['name'],
            'rank': c['rank'],
            'start_mya': c['start_mya'],
            'end_mya': c['end_mya'],
            'color': c['color']
        } for c in children],
        'mappings': [{
            'temporal_code': m['temporal_code'],
            'mapping_type': m['mapping_type']
        } for m in mappings],
        'genera': [{
            'id': g['id'],
            'name': g['name'],
            'author': g['author'],
            'year': g['year'],
            'is_valid': g['is_valid'],
            'temporal_code': g['temporal_code']
        } for g in genera]
    })


@app.route('/api/formation/<int:formation_id>')
def api_formation_detail(formation_id):
    """Get detailed info for a specific formation with related genera"""
    conn = get_db()
    cursor = conn.cursor()

    # Get formation info
    cursor.execute("""
        SELECT f.id, f.name, f.normalized_name, f.formation_type,
               f.country, f.region, f.period,
               COUNT(DISTINCT gf2.genus_id) as taxa_count
        FROM pc.formations f
        LEFT JOIN genus_formations gf2 ON gf2.formation_id = f.id
        WHERE f.id = ?
        GROUP BY f.id
    """, (formation_id,))
    formation = cursor.fetchone()

    if not formation:
        conn.close()
        return jsonify({'error': 'Formation not found'}), 404

    # Get related genera
    cursor.execute("""
        SELECT tr.id, tr.name, tr.author, tr.year, tr.is_valid
        FROM genus_formations gf
        JOIN taxonomic_ranks tr ON gf.genus_id = tr.id
        WHERE gf.formation_id = ?
        ORDER BY tr.name
    """, (formation_id,))
    genera = cursor.fetchall()

    conn.close()

    return jsonify({
        'id': formation['id'],
        'name': formation['name'],
        'normalized_name': formation['normalized_name'],
        'formation_type': formation['formation_type'],
        'country': formation['country'],
        'region': formation['region'],
        'period': formation['period'],
        'taxa_count': formation['taxa_count'],
        'genera': [{
            'id': g['id'],
            'name': g['name'],
            'author': g['author'],
            'year': g['year'],
            'is_valid': g['is_valid']
        } for g in genera]
    })


@app.route('/api/bibliography/<int:bib_id>')
def api_bibliography_detail(bib_id):
    """Get detailed info for a specific bibliography entry with related genera"""
    conn = get_db()
    cursor = conn.cursor()

    # Get bibliography info
    cursor.execute("""
        SELECT id, authors, year, year_suffix, title, journal, volume, pages,
               publisher, city, editors, book_title, reference_type, raw_entry
        FROM bibliography WHERE id = ?
    """, (bib_id,))
    bib = cursor.fetchone()

    if not bib:
        conn.close()
        return jsonify({'error': 'Bibliography entry not found'}), 404

    # Find related genera by matching author last name + year
    genera = []
    if bib['authors'] and bib['year']:
        # Extract first author's last name (before comma)
        first_author = bib['authors'].split(',')[0].strip()
        if first_author:
            cursor.execute("""
                SELECT id, name, author, year, is_valid
                FROM taxonomic_ranks
                WHERE rank = 'Genus' AND author LIKE ? AND year = ?
                ORDER BY name
            """, (f'%{first_author}%', bib['year']))
            genera = cursor.fetchall()

    conn.close()

    return jsonify({
        'id': bib['id'],
        'authors': bib['authors'],
        'year': bib['year'],
        'year_suffix': bib['year_suffix'],
        'title': bib['title'],
        'journal': bib['journal'],
        'volume': bib['volume'],
        'pages': bib['pages'],
        'publisher': bib['publisher'],
        'city': bib['city'],
        'editors': bib['editors'],
        'book_title': bib['book_title'],
        'reference_type': bib['reference_type'],
        'raw_entry': bib['raw_entry'],
        'genera': [{
            'id': g['id'],
            'name': g['name'],
            'author': g['author'],
            'year': g['year'],
            'is_valid': g['is_valid']
        } for g in genera]
    })


@app.route('/api/paleocore/status')
def api_paleocore_status():
    """Get PaleoCore DB status and verify cross-DB access"""
    conn = get_db()
    cursor = conn.cursor()

    # Check if pc schema is attached
    databases = cursor.execute("PRAGMA database_list").fetchall()
    db_names = [row['name'] for row in databases]
    has_paleocore = 'pc' in db_names

    result = {
        'attached': has_paleocore,
        'paleocore_path': get_paleocore_db_path(),
    }

    if has_paleocore:
        # Get PaleoCore metadata
        try:
            cursor.execute("SELECT key, value FROM pc.artifact_metadata")
            result['metadata'] = {row['key']: row['value'] for row in cursor.fetchall()}
        except Exception:
            result['metadata'] = None

        # Count records in PaleoCore tables
        pc_tables = {}
        for table in ['countries', 'geographic_regions', 'cow_states',
                       'country_cow_mapping', 'formations', 'temporal_ranges',
                       'ics_chronostrat', 'temporal_ics_mapping']:
            try:
                count = cursor.execute(f"SELECT COUNT(*) FROM pc.{table}").fetchone()[0]
                pc_tables[table] = count
            except Exception:
                pc_tables[table] = None
        result['tables'] = pc_tables

        # Cross-DB query test: join trilobase genus_locations with pc.countries
        try:
            cursor.execute("""
                SELECT COUNT(*) as cnt
                FROM genus_locations gl
                JOIN pc.countries c ON gl.country_id = c.id
            """)
            result['cross_db_join_test'] = {
                'query': 'genus_locations JOIN pc.countries',
                'matched_rows': cursor.fetchone()['cnt'],
                'status': 'OK'
            }
        except Exception as e:
            result['cross_db_join_test'] = {
                'status': 'FAIL',
                'error': str(e)
            }

    conn.close()
    return jsonify(result)


@app.route('/api/annotations/<entity_type>/<int:entity_id>')
def api_get_annotations(entity_type, entity_id):
    """Get annotations for a specific entity"""
    conn = get_db()
    result = _fetch_annotations(conn, entity_type, entity_id)
    conn.close()
    return jsonify(result)


@app.route('/api/annotations', methods=['POST'])
def api_create_annotation():
    """Create a new annotation"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    conn = get_db()
    result, status = _create_annotation(conn, data)
    conn.close()
    return jsonify(result), status


@app.route('/api/annotations/<int:annotation_id>', methods=['DELETE'])
def api_delete_annotation(annotation_id):
    """Delete an annotation"""
    conn = get_db()
    result, status = _delete_annotation(conn, annotation_id)
    conn.close()
    return jsonify(result), status


@app.route('/<path:filename>')
def serve_spa_file(filename):
    """Serve Reference SPA asset files (app.js, style.css, etc.)."""
    spa_dir = _get_reference_spa_dir()
    if spa_dir and os.path.isfile(os.path.join(spa_dir, filename)):
        return send_from_directory(spa_dir, filename)
    return '', 404


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=str, default=None,
                        help='Active package name (e.g., trilobase, paleocore)')
    args = parser.parse_args()
    if args.package:
        from .scoda_package import set_active_package
        set_active_package(args.package)
    app.run(debug=True, host='0.0.0.0', port=8080)
