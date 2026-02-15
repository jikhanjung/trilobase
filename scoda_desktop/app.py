"""
SCODA Desktop Web Interface
FastAPI application for browsing SCODA data packages
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import json
import os
import sqlite3

from .scoda_package import get_db, get_registry, get_active_package_name

app = FastAPI(title="SCODA Desktop")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

VALID_ENTITY_TYPES = {'genus', 'family', 'order', 'suborder', 'superfamily', 'class'}
VALID_ANNOTATION_TYPES = {'note', 'correction', 'alternative', 'link'}


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

@app.get('/api/detail/{query_name}')
def api_generic_detail(query_name: str, request: Request):
    """Execute a named query and return the first row as flat JSON."""
    conn = get_db()
    params = dict(request.query_params)
    result = _execute_query(conn, query_name, params)
    conn.close()
    if result is None:
        return JSONResponse({'error': f'Query not found: {query_name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    if result['row_count'] == 0:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return result['rows'][0]


@app.get('/api/composite/{view_name}')
def api_composite_detail(view_name: str, request: Request):
    """Execute manifest-defined composite detail query."""
    entity_id = request.query_params.get('id')
    if not entity_id:
        return JSONResponse({'error': 'id parameter required'}, status_code=400)

    conn = get_db()
    manifest_data = _fetch_manifest(conn)
    if not manifest_data:
        conn.close()
        return JSONResponse({'error': 'No manifest found'}, status_code=404)

    views = manifest_data['manifest'].get('views', {})
    view = views.get(view_name)
    if not view or view.get('type') != 'detail' or 'source_query' not in view:
        conn.close()
        return JSONResponse({'error': f'Detail view not found: {view_name}'}, status_code=404)

    # Main query
    source_param = view.get('source_param', 'id')
    result = _execute_query(conn, view['source_query'], {source_param: entity_id})
    if result is None or result.get('row_count', 0) == 0:
        conn.close()
        return JSONResponse({'error': 'Not found'}, status_code=404)
    if 'error' in result:
        conn.close()
        return JSONResponse(result, status_code=400)

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
    return data



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


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    """Main page — serve Reference SPA if extracted, otherwise generic viewer."""
    spa_dir = _get_reference_spa_dir()
    if spa_dir:
        return FileResponse(os.path.join(spa_dir, 'index.html'))
    return templates.TemplateResponse(request, "index.html")



@app.get('/api/provenance')
def api_provenance():
    """Get data provenance information"""
    conn = get_db()
    result = _fetch_provenance(conn)
    conn.close()
    return result


@app.get('/api/display-intent')
def api_display_intent():
    """Get display intent hints for SCODA viewers"""
    conn = get_db()
    result = _fetch_display_intent(conn)
    conn.close()
    return result


@app.get('/api/queries')
def api_queries():
    """Get list of available named queries"""
    conn = get_db()
    result = _fetch_queries(conn)
    conn.close()
    return result


@app.get('/api/manifest')
def api_manifest():
    """Get UI manifest with declarative view definitions"""
    conn = get_db()
    result = _fetch_manifest(conn)
    conn.close()
    if result:
        return result
    return JSONResponse({'error': 'No manifest found'}, status_code=404)


@app.get('/api/queries/{name}/execute')
def api_query_execute(name: str, request: Request):
    """Execute a named query with optional parameters"""
    conn = get_db()
    params = dict(request.query_params)
    result = _execute_query(conn, name, params)
    conn.close()
    if result is None:
        return JSONResponse({'error': f'Query not found: {name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    return result



@app.get('/api/annotations/{entity_type}/{entity_id}')
def api_get_annotations(entity_type: str, entity_id: int):
    """Get annotations for a specific entity"""
    conn = get_db()
    result = _fetch_annotations(conn, entity_type, entity_id)
    conn.close()
    return result


class AnnotationCreate(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    annotation_type: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None


@app.post('/api/annotations')
def api_create_annotation(body: AnnotationCreate):
    """Create a new annotation"""
    data = body.model_dump()
    conn = get_db()
    result, status = _create_annotation(conn, data)
    conn.close()
    return JSONResponse(result, status_code=status)


@app.delete('/api/annotations/{annotation_id}')
def api_delete_annotation(annotation_id: int):
    """Delete an annotation"""
    conn = get_db()
    result, status = _delete_annotation(conn, annotation_id)
    conn.close()
    return JSONResponse(result, status_code=status)


@app.get('/{filename:path}')
def serve_spa_file(filename: str):
    """Serve Reference SPA asset files (app.js, style.css, etc.)."""
    spa_dir = _get_reference_spa_dir()
    if spa_dir and os.path.isfile(os.path.join(spa_dir, filename)):
        return FileResponse(os.path.join(spa_dir, filename))
    return JSONResponse(content='', status_code=404)


if __name__ == '__main__':
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=str, default=None,
                        help='Active package name (e.g., trilobase, paleocore)')
    args = parser.parse_args()
    if args.package:
        from .scoda_package import set_active_package
        set_active_package(args.package)
    uvicorn.run(app, host='0.0.0.0', port=8080)
