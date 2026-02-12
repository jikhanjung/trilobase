import sqlite3
import os
import sys
import argparse
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
import json
import asyncio
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
import uvicorn

from scoda_package import get_db, ensure_overlay_db

def row_to_dict(row):
    return dict(row)

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

def search_genera(name_pattern: str, valid_only: bool = False, limit: int = 50) -> list[dict]:
    """Search for genera by name pattern, optionally filtering by validity and limiting results."""
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT id, name, author, year, is_valid, family, temporal_code, type_species
        FROM taxonomic_ranks
        WHERE rank = 'Genus' AND name LIKE ?
    """
    params = [name_pattern]

    if valid_only:
        query += " AND is_valid = 1"

    query += " ORDER BY name LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    genera = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return genera

def build_genus_evidence_pack(genus_id: int) -> dict:
    """Build evidence pack for a genus (structured, bounded output for LLM)."""
    conn = get_db()
    cursor = conn.cursor()

    # Get genus basic info
    cursor.execute("""
        SELECT tr.*, parent.name as family_name
        FROM taxonomic_ranks tr
        LEFT JOIN taxonomic_ranks parent ON tr.parent_id = parent.id
        WHERE tr.id = ? AND tr.rank = 'Genus'
    """, (genus_id,))
    genus = cursor.fetchone()

    if not genus:
        return None

    # Get synonyms
    cursor.execute("""
        SELECT jr.name as junior_name, s.synonym_type, s.senior_taxon_name,
               s.fide_author, s.fide_year
        FROM synonyms s
        JOIN taxonomic_ranks jr ON s.junior_taxon_id = jr.id
        WHERE jr.id = ? OR s.senior_taxon_id = ?
    """, (genus_id, genus_id)) # Check both junior and senior side for completeness
    synonyms = [row_to_dict(row) for row in cursor.fetchall()]

    # Get formations
    cursor.execute("""
        SELECT f.name, f.country, gf.is_type_locality
        FROM genus_formations gf
        JOIN formations f ON gf.formation_id = f.id
        WHERE gf.genus_id = ?
    """, (genus_id,))
    formations = [row_to_dict(row) for row in cursor.fetchall()]

    # Get locations
    cursor.execute("""
        SELECT c.name as country, gl.region, gl.is_type_locality
        FROM genus_locations gl
        JOIN countries c ON gl.country_id = c.id
        WHERE gl.genus_id = ?
    """, (genus_id,))
    locations = [row_to_dict(row) for row in cursor.fetchall()]

    # Get metadata (provenance)
    cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
    version_row = cursor.fetchone()
    version = version_row[0] if version_row else '1.0.0'
    
    # Get references for the genus author/year
    references = []
    if genus['author'] and genus['year']:
        cursor.execute("""
            SELECT raw_entry FROM bibliography
            WHERE authors LIKE ? AND year = ?
        """, (f"%{genus['author']}%", genus['year']))
        for ref_row in cursor.fetchall():
            references.append(ref_row['raw_entry'])


    conn.close()

    # Build Evidence Pack
    return {
        "genus": {
            "id": genus["id"],
            "name": genus["name"],
            "author": genus["author"],
            "year": genus["year"],
            "is_valid": bool(genus["is_valid"]),
            "family": genus["family_name"],
            "type_species": genus["type_species"],
            "raw_entry": genus["raw_entry"]
        },
        "synonyms": synonyms,
        "formations": formations,
        "localities": locations,
        "references": references,
        "provenance": {
            "source": "Jell & Adrain, 2002",
            "canonical_version": version,
            "extraction_date": "2026-02-04" # This should be dynamic or from metadata
        }
    }

def get_metadata() -> dict:
    """Get SCODA artifact metadata and database statistics."""
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
    return metadata

def get_genera_by_country(country_name: str, limit: int = 50) -> list[dict]:
    """Get a list of genera found in a specific country."""
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT tr.id, tr.name, tr.author, tr.year, tr.is_valid, tr.family
        FROM taxonomic_ranks tr
        JOIN genus_locations gl ON tr.id = gl.genus_id
        JOIN countries c ON gl.country_id = c.id
        WHERE tr.rank = 'Genus' AND c.name = ?
        ORDER BY tr.name
        LIMIT ?
    """
    cursor.execute(query, (country_name, limit))
    genera = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return genera

def get_genera_by_formation(formation_name: str, limit: int = 50) -> list[dict]:
    """Get a list of genera found in a specific geological formation."""
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT tr.id, tr.name, tr.author, tr.year, tr.is_valid, tr.family
        FROM taxonomic_ranks tr
        JOIN genus_formations gf ON tr.id = gf.genus_id
        JOIN formations f ON gf.formation_id = f.id
        WHERE tr.rank = 'Genus' AND f.name = ?
        ORDER BY tr.name
        LIMIT ?
    """
    cursor.execute(query, (formation_name, limit))
    genera = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return genera

def execute_named_query(query_name: str, params: dict = None) -> list[dict] | dict:
    """Execute a predefined named SQL query from the ui_queries table."""
    conn = get_db()
    cursor = conn.cursor()

    if params is None:
        params = {}

    # Look up the query
    cursor.execute("SELECT sql, params_json FROM ui_queries WHERE name = ?", (query_name,))
    query_row = cursor.fetchone()

    if not query_row:
        conn.close()
        return {"error": f"Named query '{query_name}' not found."}

    sql_query = query_row['sql']
    
    # Merge default params from DB with provided params
    db_params = json.loads(query_row['params_json']) if query_row['params_json'] else {}
    merged_params = {**db_params, **params}

    # Execute the query
    try:
        cursor.execute(sql_query, merged_params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        # Return structured results
        return {
            'query': query_name,
            'columns': columns,
            'row_count': len(rows),
            'rows': [row_to_dict(row) for row in rows]
        }
    except Exception as e:
        conn.close()
        return {"error": f"Error executing named query '{query_name}': {str(e)}"}

VALID_ENTITY_TYPES = {'genus', 'family', 'order', 'suborder', 'superfamily', 'class'}
VALID_ANNOTATION_TYPES = {'note', 'correction', 'alternative', 'link'}

def get_annotations(entity_type: str, entity_id: int) -> list[dict]:
    """Retrieve user annotations for a specific entity."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY created_at DESC, id DESC
    """, (entity_type, entity_id))
    annotations = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return annotations

def add_annotation(entity_type: str, entity_id: int, entity_name: str, annotation_type: str, content: str, author: str = None) -> dict:
    """Add a new user annotation to an entity. This writes to the local overlay database."""
    conn = get_db()
    cursor = conn.cursor()

    if entity_type not in VALID_ENTITY_TYPES:
        return {"error": f"Invalid entity_type. Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"}

    if annotation_type not in VALID_ANNOTATION_TYPES:
        return {"error": f"Invalid annotation_type. Must be one of: {', '.join(sorted(VALID_ANNOTATION_TYPES))}"}

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
    annotation = row_to_dict(cursor.fetchone())
    conn.close()

    return annotation

def delete_annotation(annotation_id: int) -> dict:
    """Delete a user annotation by its ID."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    if not cursor.fetchone():
        conn.close()
        return {"error": f"Annotation with ID {annotation_id} not found."}

    cursor.execute("DELETE FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    conn.close()
    return {"message": f"Annotation with ID {annotation_id} deleted."}

def get_rank_detail(rank_id: int) -> dict:
    """Get detailed information for a specific taxonomic rank (Class, Order, Family, Genus, etc.) by its ID."""
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
        return {"error": f"Rank with ID {rank_id} not found."}

    # Get children counts by rank
    cursor.execute("""
        SELECT rank, COUNT(*) as count
        FROM taxonomic_ranks
        WHERE parent_id = ?
        GROUP BY rank
    """, (rank_id,))
    children_counts = [row_to_dict(row) for row in cursor.fetchall()]

    # Get direct children list (limit 20)
    cursor.execute("""
        SELECT id, name, rank, author, genera_count
        FROM taxonomic_ranks
        WHERE parent_id = ?
        ORDER BY name
        LIMIT 20
    """, (rank_id,))
    children = [row_to_dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        'id': rank['id'],
        'name': rank['name'],
        'rank': rank['rank'],
        'author': rank['author'],
        'year': rank['year'],
        'genera_count': rank['genera_count'],
        'notes': rank['notes'],
        'parent_name': rank['parent_name'],
        'parent_rank': rank['parent_rank'],
        'children_counts': children_counts,
        'children': children
    }

def get_family_genera(family_id: int) -> dict:
    """Get genera list for a specific family."""
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
        return {"error": "Family not found"}

    # Get genera
    cursor.execute("""
        SELECT id, name, author, year, type_species, location, is_valid
        FROM taxonomic_ranks
        WHERE parent_id = ? AND rank = 'Genus'
        ORDER BY name
    """, (family_id,))
    genera = cursor.fetchall()

    conn.close()

    return {
        'family': {
            'id': family['id'],
            'name': family['name'],
            'author': family['author'],
            'genera_count': family['genera_count']
        },
        'genera': [row_to_dict(g) for g in genera]
    }

def get_provenance() -> list[dict]:
    """Get data provenance information."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, source_type, citation, description, year, url
        FROM provenance
        ORDER BY id
    """)
    sources = cursor.fetchall()

    conn.close()

    return [row_to_dict(s) for s in sources]

def list_available_queries() -> list[dict]:
    """Get list of available named queries."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, params_json, created_at
        FROM ui_queries
        ORDER BY name
    """)
    queries = cursor.fetchall()
    conn.close()

    return [row_to_dict(q) for q in queries]

app = Server("trilobase")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_taxonomy_tree",
            description="Retrieve the full taxonomic hierarchy tree from Class down to Family.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_rank_detail",
            description="Get detailed information for a specific taxonomic rank (Class, Order, Family, Genus, etc.) by its ID.",
            inputSchema={
                "type": "object",
                "properties": {"rank_id": {"type": "integer", "description": "The ID of the taxonomic rank to retrieve."}},
                "required": ["rank_id"]
            }
        ),
        Tool(
            name="get_family_genera",
            description="Get a list of all genera belonging to a specific Family ID.",
            inputSchema={
                "type": "object",
                "properties": {"family_id": {"type": "integer", "description": "The ID of the family."}},
                "required": ["family_id"]
            }
        ),
        Tool(
            name="get_genus_detail",
            description="Get detailed information for a specific genus including synonyms, formations, and locations. Returns an evidence pack with full provenance.",
            inputSchema={
                "type": "object",
                "properties": {"genus_id": {"type": "integer", "description": "The ID of the genus to retrieve."}},
                "required": ["genus_id"]
            }
        ),
        Tool(
            name="search_genera",
            description="Search for genera by name pattern, optionally filtering by validity and limiting results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name_pattern": {"type": "string", "description": "A SQL LIKE pattern for the genus name (e.g., 'Paradoxides%')."},
                    "valid_only": {"type": "boolean", "description": "If true, only return valid genera. Defaults to false.", "default": False},
                    "limit": {"type": "integer", "description": "Maximum number of results to return. Defaults to 50.", "default": 50}
                },
                "required": ["name_pattern"]
            }
        ),
        Tool(
            name="get_genera_by_country",
            description="Get a list of genera found in a specific country.",
            inputSchema={
                "type": "object",
                "properties": {
                    "country": {"type": "string", "description": "The name of the country."},
                    "limit": {"type": "integer", "description": "Maximum number of results to return. Defaults to 50.", "default": 50}
                },
                "required": ["country"]
            }
        ),
        Tool(
            name="get_genera_by_formation",
            description="Get a list of genera found in a specific geological formation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "formation": {"type": "string", "description": "The name of the geological formation."},
                    "limit": {"type": "integer", "description": "Maximum number of results to return. Defaults to 50.", "default": 50}
                },
                "required": ["formation"]
            }
        ),
        Tool(
            name="execute_named_query",
            description="Execute a predefined named SQL query from the ui_queries table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_name": {"type": "string", "description": "The name of the query to execute (e.g., 'taxonomy_tree', 'family_genera')."},
                    "params": {"type": "object", "description": "A dictionary of parameters to pass to the query.", "additionalProperties": True, "default": {}}
                },
                "required": ["query_name"]
            }
        ),
        Tool(
            name="get_metadata",
            description="Get general metadata and statistics about the database.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_provenance",
            description="Get provenance information about the data sources.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="list_available_queries",
            description="List all available named queries stored in the database.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_annotations",
            description="Retrieve user annotations for a specific entity (genus, family, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "description": "The type of entity (e.g., 'genus', 'family', 'order')."},
                    "entity_id": {"type": "integer", "description": "The ID of the entity."}
                },
                "required": ["entity_type", "entity_id"]
            }
        ),
        Tool(
            name="add_annotation",
            description="Add a new user annotation to an entity. This writes to the local overlay database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "description": "The type of entity (e.g., 'genus', 'family', 'order')."},
                    "entity_id": {"type": "integer", "description": "The ID of the entity."},
                    "entity_name": {"type": "string", "description": "The name of the entity for matching across releases."},
                    "annotation_type": {"type": "string", "description": "The type of annotation (e.g., 'note', 'correction', 'alternative', 'link')."},
                    "content": {"type": "string", "description": "The content of the annotation."},
                    "author": {"type": "string", "description": "Optional: The author of the annotation."}
                },
                "required": ["entity_type", "entity_id", "entity_name", "annotation_type", "content"]
            }
        ),
        Tool(
            name="delete_annotation",
            description="Delete a user annotation by its ID.",
            inputSchema={
                "type": "object",
                "properties": {"annotation_id": {"type": "integer", "description": "The ID of the annotation to delete."}},
                "required": ["annotation_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "get_taxonomy_tree":
        tree = build_tree()
        return [TextContent(type="text", text=json.dumps(tree, indent=2))]
    elif name == "search_genera":
        name_pattern = arguments.get("name_pattern")
        valid_only = arguments.get("valid_only", False)
        limit = arguments.get("limit", 50)
        genera = search_genera(name_pattern, valid_only, limit)
        return [TextContent(type="text", text=json.dumps(genera, indent=2))]
    elif name == "get_genus_detail":
        genus_id = arguments.get("genus_id")
        evidence_pack = build_genus_evidence_pack(genus_id)
        if not evidence_pack:
            return [TextContent(type="text", text=json.dumps({"error": f"Genus with ID {genus_id} not found."}, indent=2))]
        return [TextContent(type="text", text=json.dumps(evidence_pack, indent=2))]
    elif name == "get_metadata":
        metadata = get_metadata()
        return [TextContent(type="text", text=json.dumps(metadata, indent=2))]
    elif name == "get_genera_by_country":
        country_name = arguments.get("country")
        limit = arguments.get("limit", 50)
        genera = get_genera_by_country(country_name, limit)
        return [TextContent(type="text", text=json.dumps(genera, indent=2))]
    elif name == "get_genera_by_formation":
        formation_name = arguments.get("formation")
        limit = arguments.get("limit", 50)
        genera = get_genera_by_formation(formation_name, limit)
        return [TextContent(type="text", text=json.dumps(genera, indent=2))]
    elif name == "execute_named_query":
        query_name = arguments.get("query_name")
        params = arguments.get("params")
        result = execute_named_query(query_name, params)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "get_annotations":
        entity_type = arguments.get("entity_type")
        entity_id = arguments.get("entity_id")
        annotations = get_annotations(entity_type, entity_id)
        return [TextContent(type="text", text=json.dumps(annotations, indent=2))]
    elif name == "add_annotation":
        entity_type = arguments.get("entity_type")
        entity_id = arguments.get("entity_id")
        entity_name = arguments.get("entity_name")
        annotation_type = arguments.get("annotation_type")
        content = arguments.get("content")
        author = arguments.get("author")
        result = add_annotation(entity_type, entity_id, entity_name, annotation_type, content, author)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "delete_annotation":
        annotation_id = arguments.get("annotation_id")
        result = delete_annotation(annotation_id)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "get_rank_detail":
        rank_id = arguments.get("rank_id")
        result = get_rank_detail(rank_id)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "get_family_genera":
        family_id = arguments.get("family_id")
        result = get_family_genera(family_id)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "get_provenance":
        result = get_provenance()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "list_available_queries":
        result = list_available_queries()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    # Fallback for unknown tools
    return [TextContent(type="text", text=json.dumps({"error": f"Tool '{name}' not implemented."}))]

async def run_stdio():
    """Run MCP server in stdio mode (for Claude Desktop spawning)."""
    ensure_overlay_db()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

def run_sse(host: str = "localhost", port: int = 8081):
    """Run MCP server in SSE mode (HTTP server for persistent connections)."""
    ensure_overlay_db()

    # Create SSE transport
    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        """Handle SSE connections."""
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )
        return Response()

    async def handle_messages(request):
        """Handle message POST requests."""
        return await sse.handle_post_message(request.scope, request.receive, request._send)

    async def health_check(request):
        """Simple health check endpoint."""
        return Response(
            content=json.dumps({
                "status": "ok",
                "service": "trilobase-mcp",
                "mode": "sse"
            }),
            media_type="application/json"
        )

    # Create Starlette app
    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
            Route("/health", endpoint=health_check),
        ]
    )

    print(f"🚀 Trilobase MCP Server (SSE mode) starting on http://{host}:{port}")
    print(f"   SSE endpoint: http://{host}:{port}/sse")
    print(f"   Health check: http://{host}:{port}/health")

    uvicorn.run(starlette_app, host=host, port=port, log_level="info")

def main():
    """Main entry point - parse args and run in appropriate mode."""
    parser = argparse.ArgumentParser(description="Trilobase MCP Server")
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="Server mode: stdio (for Claude Desktop) or sse (HTTP server)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind SSE server to (SSE mode only)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port for SSE server (SSE mode only)"
    )

    args = parser.parse_args()

    if args.mode == "stdio":
        asyncio.run(run_stdio())
    else:
        # SSE mode runs synchronously with uvicorn
        run_sse(args.host, args.port)

if __name__ == "__main__":
    main()
