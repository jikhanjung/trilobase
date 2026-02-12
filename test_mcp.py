#!/usr/bin/env python3
"""
Comprehensive MCP Server Tests
Tests all 14 tools with realistic scenarios.
"""
import json
import pytest
from contextlib import asynccontextmanager
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


@asynccontextmanager
async def create_session():
    """Create a fresh MCP client session within the calling task."""
    server_params = StdioServerParameters(
        command="python3",
        args=["mcp_server.py"]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.mark.asyncio
async def test_list_tools():
    """Test that all 14 tools are exposed"""
    async with create_session() as session:
        result = await session.list_tools()
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
async def test_get_taxonomy_tree():
    """Test taxonomy tree retrieval"""
    async with create_session() as session:
        result = await session.call_tool("get_taxonomy_tree", {})
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0

        node = data[0]
        assert "id" in node
        assert "name" in node
        assert "rank" in node
        assert "children" in node
        assert node["rank"] == "Class"


@pytest.mark.asyncio
async def test_search_genera():
    """Test genus search"""
    async with create_session() as session:
        result = await session.call_tool("search_genera", {
            "name_pattern": "Paradoxides%",
            "limit": 10
        })
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0
        assert any(g["name"] == "Paradoxides" for g in data)

        genus = data[0]
        assert "id" in genus
        assert "name" in genus
        assert "author" in genus
        assert "is_valid" in genus


@pytest.mark.asyncio
async def test_search_genera_valid_only():
    """Test genus search with valid_only filter"""
    async with create_session() as session:
        result = await session.call_tool("search_genera", {
            "name_pattern": "%",
            "valid_only": True,
            "limit": 10
        })
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert all(g["is_valid"] == 1 for g in data)


@pytest.mark.asyncio
async def test_get_genus_detail_evidence_pack():
    """Test genus detail with Evidence Pack structure"""
    async with create_session() as session:
        search_result = await session.call_tool("search_genera", {
            "name_pattern": "Paradoxides",
            "limit": 1
        })
        genera = json.loads(search_result.content[0].text)
        assert len(genera) > 0
        genus_id = genera[0]["id"]

        result = await session.call_tool("get_genus_detail", {"genus_id": genus_id})
        evidence_pack = json.loads(result.content[0].text)

        assert "genus" in evidence_pack
        assert "synonyms" in evidence_pack
        assert "formations" in evidence_pack
        assert "localities" in evidence_pack
        assert "references" in evidence_pack
        assert "provenance" in evidence_pack

        genus = evidence_pack["genus"]
        assert genus["id"] == genus_id
        assert genus["name"] == "Paradoxides"
        assert "raw_entry" in genus

        provenance = evidence_pack["provenance"]
        assert provenance["source"] == "Jell & Adrain, 2002"
        assert "canonical_version" in provenance


@pytest.mark.asyncio
async def test_get_genera_by_country():
    """Test country-based genus search"""
    async with create_session() as session:
        result = await session.call_tool("get_genera_by_country", {
            "country": "China",
            "limit": 10
        })
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0

        genus = data[0]
        assert "id" in genus
        assert "name" in genus
        assert "family" in genus


@pytest.mark.asyncio
async def test_get_genera_by_formation():
    """Test formation-based genus search"""
    async with create_session() as session:
        metadata_result = await session.call_tool("get_metadata", {})
        metadata = json.loads(metadata_result.content[0].text)
        assert metadata["statistics"]["formations"] > 0

        result = await session.call_tool("get_genera_by_formation", {
            "formation": "Jince Formation",
            "limit": 10
        })
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_metadata():
    """Test metadata and statistics"""
    async with create_session() as session:
        result = await session.call_tool("get_metadata", {})
        metadata = json.loads(result.content[0].text)

        assert "name" in metadata
        assert "version" in metadata
        assert "statistics" in metadata

        stats = metadata["statistics"]
        assert stats["class"] == 1
        assert stats["genus"] > 5000
        assert stats["valid_genera"] > 4000
        assert stats["synonyms"] > 1000
        assert stats["bibliography"] > 2000


@pytest.mark.asyncio
async def test_get_provenance():
    """Test data provenance information"""
    async with create_session() as session:
        result = await session.call_tool("get_provenance", {})
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0

        source = data[0]
        assert "source_type" in source
        assert "citation" in source
        assert "description" in source


@pytest.mark.asyncio
async def test_list_available_queries():
    """Test named queries list"""
    async with create_session() as session:
        result = await session.call_tool("list_available_queries", {})
        data = json.loads(result.content[0].text)

        assert isinstance(data, list)
        assert len(data) > 0

        query = data[0]
        assert "id" in query
        assert "name" in query
        assert "description" in query
        assert "params_json" in query


@pytest.mark.asyncio
async def test_execute_named_query():
    """Test named query execution"""
    async with create_session() as session:
        list_result = await session.call_tool("list_available_queries", {})
        queries = json.loads(list_result.content[0].text)
        assert len(queries) > 0

        query_name = queries[0]["name"]
        result = await session.call_tool("execute_named_query", {
            "query_name": query_name,
            "params": {}
        })
        data = json.loads(result.content[0].text)

        assert "query" in data
        assert "columns" in data
        assert "rows" in data
        assert data["query"] == query_name


@pytest.mark.asyncio
async def test_get_rank_detail():
    """Test rank detail retrieval"""
    async with create_session() as session:
        tree_result = await session.call_tool("get_taxonomy_tree", {})
        tree = json.loads(tree_result.content[0].text)
        assert len(tree) > 0

        rank_id = tree[0]["id"]
        result = await session.call_tool("get_rank_detail", {"rank_id": rank_id})
        data = json.loads(result.content[0].text)

        assert data["id"] == rank_id
        assert data["rank"] == "Class"
        assert "name" in data
        assert "children_counts" in data
        assert "children" in data


@pytest.mark.asyncio
async def test_get_family_genera():
    """Test family genera list"""
    async with create_session() as session:
        tree_result = await session.call_tool("get_taxonomy_tree", {})
        tree = json.loads(tree_result.content[0].text)

        family_id = None
        for node in tree[0]["children"]:
            if node["children"]:
                for subnode in node["children"]:
                    if subnode["children"]:
                        for family in subnode["children"]:
                            if family["rank"] == "Family":
                                family_id = family["id"]
                                break
                        if family_id:
                            break
            if family_id:
                break

        if family_id:
            result = await session.call_tool("get_family_genera", {"family_id": family_id})
            data = json.loads(result.content[0].text)

            assert "family" in data
            assert "genera" in data
            assert isinstance(data["genera"], list)


@pytest.mark.asyncio
async def test_annotations_lifecycle():
    """Test annotation create/read/delete lifecycle"""
    async with create_session() as session:
        search_result = await session.call_tool("search_genera", {
            "name_pattern": "Paradoxides",
            "limit": 1
        })
        genera = json.loads(search_result.content[0].text)
        assert len(genera) > 0
        genus_id = genera[0]["id"]
        genus_name = genera[0]["name"]

        create_result = await session.call_tool("add_annotation", {
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

        read_result = await session.call_tool("get_annotations", {
            "entity_type": "genus",
            "entity_id": genus_id
        })
        annotations = json.loads(read_result.content[0].text)

        assert isinstance(annotations, list)
        assert any(a["id"] == annotation_id for a in annotations)

        delete_result = await session.call_tool("delete_annotation", {
            "annotation_id": annotation_id
        })
        delete_data = json.loads(delete_result.content[0].text)

        assert "message" in delete_data

        verify_result = await session.call_tool("get_annotations", {
            "entity_type": "genus",
            "entity_id": genus_id
        })
        remaining = json.loads(verify_result.content[0].text)

        assert not any(a["id"] == annotation_id for a in remaining)


@pytest.mark.asyncio
async def test_error_handling_invalid_genus():
    """Test error handling for invalid genus ID"""
    async with create_session() as session:
        result = await session.call_tool("get_genus_detail", {"genus_id": 999999})
        data = json.loads(result.content[0].text)

        assert data is None or "error" in data


@pytest.mark.asyncio
async def test_error_handling_invalid_annotation_type():
    """Test error handling for invalid annotation type"""
    async with create_session() as session:
        result = await session.call_tool("add_annotation", {
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
