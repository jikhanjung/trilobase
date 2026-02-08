"""
Trilobase Web Interface
Flask application for browsing trilobite taxonomy database
"""

from flask import Flask, render_template, jsonify, request
import json
import sqlite3
import os
import sys

app = Flask(__name__)

# Determine DB paths based on execution mode
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    CANONICAL_DB = os.path.join(sys._MEIPASS, 'trilobase.db')
    OVERLAY_DB = os.path.join(os.path.dirname(sys.executable), 'trilobase_overlay.db')
else:
    # Running as normal Python script
    base_dir = os.path.dirname(__file__)
    CANONICAL_DB = os.path.join(base_dir, 'trilobase.db')
    OVERLAY_DB = os.path.join(base_dir, 'trilobase_overlay.db')


def _ensure_overlay_db():
    """Create overlay DB if it doesn't exist."""
    if os.path.exists(OVERLAY_DB):
        return

    # Get canonical version
    try:
        conn = sqlite3.connect(CANONICAL_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
        row = cursor.fetchone()
        version = row[0] if row else '1.0.0'
        conn.close()
    except Exception:
        version = '1.0.0'

    # Create overlay DB
    from scripts.init_overlay_db import create_overlay_db
    create_overlay_db(OVERLAY_DB, version)


def get_db():
    """Get database connection with overlay attached."""
    # Ensure overlay DB exists
    _ensure_overlay_db()

    # Connect to canonical DB
    conn = sqlite3.connect(CANONICAL_DB)
    conn.row_factory = sqlite3.Row

    # Attach overlay DB
    conn.execute(f"ATTACH DATABASE '{OVERLAY_DB}' AS overlay")

    return conn


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


@app.route('/')
def index():
    """Main page"""
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
        JOIN formations f ON gf.formation_id = f.id
        WHERE gf.genus_id = ?
    """, (genus_id,))
    formations = cursor.fetchall()

    # Get locations (via relation table)
    cursor.execute("""
        SELECT c.id, c.name as country, gl.region
        FROM genus_locations gl
        JOIN countries c ON gl.country_id = c.id
        WHERE gl.genus_id = ?
    """, (genus_id,))
    locations = cursor.fetchall()

    conn.close()

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
        'locations': [{
            'id': l['id'],
            'country': l['country'],
            'region': l['region']
        } for l in locations]
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

    cursor.execute("SELECT COUNT(*) as count FROM formations")
    stats['formations'] = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) as count FROM countries")
    stats['countries'] = cursor.fetchone()['count']

    conn.close()

    metadata['statistics'] = stats
    return jsonify(metadata)


@app.route('/api/provenance')
def api_provenance():
    """Get data provenance information"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, source_type, citation, description, year, url
        FROM provenance
        ORDER BY id
    """)
    sources = cursor.fetchall()

    conn.close()

    return jsonify([{
        'id': s['id'],
        'source_type': s['source_type'],
        'citation': s['citation'],
        'description': s['description'],
        'year': s['year'],
        'url': s['url']
    } for s in sources])


@app.route('/api/display-intent')
def api_display_intent():
    """Get display intent hints for SCODA viewers"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, entity, default_view, description, source_query, priority
        FROM ui_display_intent
        ORDER BY entity, priority
    """)
    intents = cursor.fetchall()
    conn.close()

    return jsonify([{
        'id': i['id'],
        'entity': i['entity'],
        'default_view': i['default_view'],
        'description': i['description'],
        'source_query': i['source_query'],
        'priority': i['priority']
    } for i in intents])


@app.route('/api/queries')
def api_queries():
    """Get list of available named queries"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, params_json, created_at
        FROM ui_queries
        ORDER BY name
    """)
    queries = cursor.fetchall()
    conn.close()

    return jsonify([{
        'id': q['id'],
        'name': q['name'],
        'description': q['description'],
        'params': q['params_json'],
        'created_at': q['created_at']
    } for q in queries])


@app.route('/api/manifest')
def api_manifest():
    """Get UI manifest with declarative view definitions"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, description, manifest_json, created_at
        FROM ui_manifest
        WHERE name = 'default'
    """)
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'No manifest found'}), 404

    return jsonify({
        'name': row['name'],
        'description': row['description'],
        'manifest': json.loads(row['manifest_json']),
        'created_at': row['created_at']
    })


@app.route('/api/queries/<name>/execute')
def api_query_execute(name):
    """Execute a named query with optional parameters"""
    conn = get_db()
    cursor = conn.cursor()

    # Look up the query
    cursor.execute("SELECT sql, params_json FROM ui_queries WHERE name = ?", (name,))
    query = cursor.fetchone()

    if not query:
        conn.close()
        return jsonify({'error': f'Query not found: {name}'}), 404

    # Build parameters from query string
    params = {}
    for key, value in request.args.items():
        params[key] = value

    # Execute the query
    try:
        cursor.execute(query['sql'], params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        return jsonify({
            'query': name,
            'columns': columns,
            'row_count': len(rows),
            'rows': [dict(row) for row in rows]
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400


VALID_ENTITY_TYPES = {'genus', 'family', 'order', 'suborder', 'superfamily', 'class'}
VALID_ANNOTATION_TYPES = {'note', 'correction', 'alternative', 'link'}


@app.route('/api/annotations/<entity_type>/<int:entity_id>')
def api_get_annotations(entity_type, entity_id):
    """Get annotations for a specific entity"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY created_at DESC, id DESC
    """, (entity_type, entity_id))
    annotations = cursor.fetchall()
    conn.close()

    return jsonify([{
        'id': a['id'],
        'entity_type': a['entity_type'],
        'entity_id': a['entity_id'],
        'entity_name': a['entity_name'],
        'annotation_type': a['annotation_type'],
        'content': a['content'],
        'author': a['author'],
        'created_at': a['created_at']
    } for a in annotations])


@app.route('/api/annotations', methods=['POST'])
def api_create_annotation():
    """Create a new annotation"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    entity_type = data.get('entity_type')
    entity_id = data.get('entity_id')
    annotation_type = data.get('annotation_type')
    content = data.get('content')
    author = data.get('author')

    if not content:
        return jsonify({'error': 'content is required'}), 400

    if entity_type not in VALID_ENTITY_TYPES:
        return jsonify({'error': f'Invalid entity_type. Must be one of: {", ".join(sorted(VALID_ENTITY_TYPES))}'}), 400

    if annotation_type not in VALID_ANNOTATION_TYPES:
        return jsonify({'error': f'Invalid annotation_type. Must be one of: {", ".join(sorted(VALID_ANNOTATION_TYPES))}'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Get entity_name from canonical DB
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
    conn.close()

    return jsonify({
        'id': annotation['id'],
        'entity_type': annotation['entity_type'],
        'entity_id': annotation['entity_id'],
        'entity_name': annotation['entity_name'],
        'annotation_type': annotation['annotation_type'],
        'content': annotation['content'],
        'author': annotation['author'],
        'created_at': annotation['created_at']
    }), 201


@app.route('/api/annotations/<int:annotation_id>', methods=['DELETE'])
def api_delete_annotation(annotation_id):
    """Delete an annotation"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Annotation not found'}), 404

    cursor.execute("DELETE FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Annotation deleted', 'id': annotation_id})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
