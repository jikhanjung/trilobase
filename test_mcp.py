#!/usr/bin/env python3
"""
Comprehensive MCP Server Tests
Tests all 14 tools with realistic scenarios.
"""
import asyncio
import json
import pytest
import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


@pytest_asyncio.fixture
async def mcp_session():
    """Create MCP client session"""
    server_params = StdioServerParameters(
        command="python3",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.mark.asyncio
async def test_list_tools(mcp_session):
    """Test that all 14 tools are exposed"""
    result = await mcp_session.list_tools()
    tools = result.tools
    tool_names = [tool.name for tool in tools]

    expected = [
        "get_taxonomy_tree",
        "get_rank_detail",
        "get_family_genera",
        "get_genus_detail",
        "search_genera",
        "get_genera_by_country",
        "get_genera_by_formation",
        "execute_named_query",
        "get_metadata",
        "get_provenance",
        "list_available_queries",
        "get_annotations",
        "add_annotation",
        "delete_annotation"
    ]

    assert len(tool_names) == 14
    assert set(tool_names) == set(expected)


@pytest.mark.asyncio
async def test_get_taxonomy_tree(mcp_session):
    """Test taxonomy tree retrieval"""
    result = await mcp_session.call_tool("get_taxonomy_tree", {})
    data = json.loads(result.content[0].text)

    assert isinstance(data, list)
    assert len(data) > 0

    # Check tree structure
    node = data[0]
    assert "id" in node
    assert "name" in node
    assert "rank" in node
    assert "children" in node
    assert node["rank"] == "Class"


@pytest.mark.asyncio
async def test_search_genera(mcp_session):
    """Test genus search"""
    result = await mcp_session.call_tool("search_genera", {
        "name_pattern": "Paradoxides%",
        "limit": 10
    })
    data = json.loads(result.content[0].text)

    assert isinstance(data, list)
    assert len(data) > 0
    assert any(g["name"] == "Paradoxides" for g in data)

    # Check structure
    genus = data[0]
    assert "id" in genus
    assert "name" in genus
    assert "author" in genus
    assert "is_valid" in genus


@pytest.mark.asyncio
async def test_search_genera_valid_only(mcp_session):
    """Test genus search with valid_only filter"""
    result = await mcp_session.call_tool("search_genera", {
        "name_pattern": "%",
        "valid_only": True,
        "limit": 10
    })
    data = json.loads(result.content[0].text)

    assert isinstance(data, list)
    assert all(g["is_valid"] == 1 for g in data)


@pytest.mark.asyncio
async def test_get_genus_detail_evidence_pack(mcp_session):
    """Test genus detail with Evidence Pack structure"""
    # First search for a genus
    search_result = await mcp_session.call_tool("search_genera", {
        "name_pattern": "Paradoxides",
        "limit": 1
    })
    genera = json.loads(search_result.content[0].text)
    assert len(genera) > 0
    genus_id = genera[0]["id"]

    # Get detail
    result = await mcp_session.call_tool("get_genus_detail", {"genus_id": genus_id})
    evidence_pack = json.loads(result.content[0].text)

    # Verify Evidence Pack structure
    assert "genus" in evidence_pack
    assert "synonyms" in evidence_pack
    assert "formations" in evidence_pack
    assert "localities" in evidence_pack
    assert "references" in evidence_pack
    assert "provenance" in evidence_pack

    # Verify genus data
    genus = evidence_pack["genus"]
    assert genus["id"] == genus_id
    assert genus["name"] == "Paradoxides"
    assert "raw_entry" in genus  # Original data preserved

    # Verify provenance (SCODA principle)
    provenance = evidence_pack["provenance"]
    assert provenance["source"] == "Jell & Adrain, 2002"
    assert "canonical_version" in provenance


@pytest.mark.asyncio
async def test_get_genera_by_country(mcp_session):
    """Test country-based genus search"""
    result = await mcp_session.call_tool("get_genera_by_country", {
        "country": "China",
        "limit": 10
    })
    data = json.loads(result.content[0].text)

    assert isinstance(data, list)
    assert len(data) > 0

    # Check structure
    genus = data[0]
    assert "id" in genus
    assert "name" in genus
    assert "family" in genus


@pytest.mark.asyncio
async def test_get_genera_by_formation(mcp_session):
    """Test formation-based genus search"""
    # First get a formation name
    metadata_result = await mcp_session.call_tool("get_metadata", {})
    metadata = json.loads(metadata_result.content[0].text)
    assert metadata["statistics"]["formations"] > 0

    # Search with a common formation pattern
    result = await mcp_session.call_tool("get_genera_by_formation", {
        "formation": "Jince Formation",
        "limit": 10
    })
    data = json.loads(result.content[0].text)

    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_metadata(mcp_session):
    """Test metadata and statistics"""
    result = await mcp_session.call_tool("get_metadata", {})
    metadata = json.loads(result.content[0].text)

    # Check SCODA metadata
    assert "name" in metadata
    assert "version" in metadata
    assert "statistics" in metadata

    # Check statistics
    stats = metadata["statistics"]
    assert stats["class"] == 1
    assert stats["genus"] > 5000
    assert stats["valid_genera"] > 4000
    assert stats["synonyms"] > 1000
    assert stats["bibliography"] > 2000


@pytest.mark.asyncio
async def test_get_provenance(mcp_session):
    """Test data provenance information"""
    result = await mcp_session.call_tool("get_provenance", {})
    data = json.loads(result.content[0].text)

    assert isinstance(data, list)
    assert len(data) > 0

    # Check structure
    source = data[0]
    assert "source_type" in source
    assert "citation" in source
    assert "description" in source


@pytest.mark.asyncio
async def test_list_available_queries(mcp_session):
    """Test named queries list"""
    result = await mcp_session.call_tool("list_available_queries", {})
    data = json.loads(result.content[0].text)

    assert isinstance(data, list)
    assert len(data) > 0

    # Check structure
    query = data[0]
    assert "id" in query
    assert "name" in query
    assert "description" in query
    assert "params_json" in query


@pytest.mark.asyncio
async def test_execute_named_query(mcp_session):
    """Test named query execution"""
    # First get available queries
    list_result = await mcp_session.call_tool("list_available_queries", {})
    queries = json.loads(list_result.content[0].text)
    assert len(queries) > 0

    # Execute first query
    query_name = queries[0]["name"]
    result = await mcp_session.call_tool("execute_named_query", {
        "query_name": query_name,
        "params": {}
    })
    data = json.loads(result.content[0].text)

    assert "query" in data
    assert "columns" in data
    assert "rows" in data
    assert data["query"] == query_name


@pytest.mark.asyncio
async def test_get_rank_detail(mcp_session):
    """Test rank detail retrieval"""
    # Get tree first to find a rank ID
    tree_result = await mcp_session.call_tool("get_taxonomy_tree", {})
    tree = json.loads(tree_result.content[0].text)
    assert len(tree) > 0

    # Get detail for root (Class)
    rank_id = tree[0]["id"]
    result = await mcp_session.call_tool("get_rank_detail", {"rank_id": rank_id})
    data = json.loads(result.content[0].text)

    assert data["id"] == rank_id
    assert data["rank"] == "Class"
    assert "name" in data
    assert "children_counts" in data
    assert "children" in data


@pytest.mark.asyncio
async def test_get_family_genera(mcp_session):
    """Test family genera list"""
    # Find a family ID from tree
    tree_result = await mcp_session.call_tool("get_taxonomy_tree", {})
    tree = json.loads(tree_result.content[0].text)

    # Navigate to a family
    family_id = None
    for node in tree[0]["children"]:  # Orders
        if node["children"]:
            for subnode in node["children"]:  # Suborders/Superfamilies
                if subnode["children"]:
                    for family in subnode["children"]:  # Families
                        if family["rank"] == "Family":
                            family_id = family["id"]
                            break
                    if family_id:
                        break
            if family_id:
                break

    if family_id:
        result = await mcp_session.call_tool("get_family_genera", {"family_id": family_id})
        data = json.loads(result.content[0].text)

        assert "family" in data
        assert "genera" in data
        assert isinstance(data["genera"], list)


@pytest.mark.asyncio
async def test_annotations_lifecycle(mcp_session):
    """Test annotation create/read/delete lifecycle"""
    # Search for a genus
    search_result = await mcp_session.call_tool("search_genera", {
        "name_pattern": "Paradoxides",
        "limit": 1
    })
    genera = json.loads(search_result.content[0].text)
    assert len(genera) > 0
    genus_id = genera[0]["id"]
    genus_name = genera[0]["name"]

    # Create annotation
    create_result = await mcp_session.call_tool("add_annotation", {
        "entity_type": "genus",
        "entity_id": genus_id,
        "entity_name": genus_name,
        "annotation_type": "note",
        "content": "Test annotation from MCP",
        "author": "test_user"
    })
    annotation = json.loads(create_result.content[0].text)

    assert "id" in annotation
    assert annotation["entity_type"] == "genus"
    assert annotation["entity_id"] == genus_id
    assert annotation["content"] == "Test annotation from MCP"
    annotation_id = annotation["id"]

    # Read annotations
    read_result = await mcp_session.call_tool("get_annotations", {
        "entity_type": "genus",
        "entity_id": genus_id
    })
    annotations = json.loads(read_result.content[0].text)

    assert isinstance(annotations, list)
    assert any(a["id"] == annotation_id for a in annotations)

    # Delete annotation
    delete_result = await mcp_session.call_tool("delete_annotation", {
        "annotation_id": annotation_id
    })
    delete_data = json.loads(delete_result.content[0].text)

    assert "message" in delete_data

    # Verify deletion
    verify_result = await mcp_session.call_tool("get_annotations", {
        "entity_type": "genus",
        "entity_id": genus_id
    })
    remaining = json.loads(verify_result.content[0].text)

    assert not any(a["id"] == annotation_id for a in remaining)


@pytest.mark.asyncio
async def test_error_handling_invalid_genus(mcp_session):
    """Test error handling for invalid genus ID"""
    result = await mcp_session.call_tool("get_genus_detail", {"genus_id": 999999})
    data = json.loads(result.content[0].text)

    assert data is None or "error" in data


@pytest.mark.asyncio
async def test_error_handling_invalid_annotation_type(mcp_session):
    """Test error handling for invalid annotation type"""
    result = await mcp_session.call_tool("add_annotation", {
        "entity_type": "genus",
        "entity_id": 1,
        "entity_name": "Test",
        "annotation_type": "invalid_type",
        "content": "Test"
    })
    data = json.loads(result.content[0].text)

    assert "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
