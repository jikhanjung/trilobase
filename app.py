"""
Trilobase Web Interface
Flask application for browsing trilobite taxonomy database
"""

from flask import Flask, render_template, jsonify
import sqlite3
import os

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), 'trilobase.db')


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
