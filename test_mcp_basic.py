#!/usr/bin/env python3
"""
Basic MCP Server Test
Tests that all 14 tools are properly implemented and connected.
"""
import asyncio
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def test_mcp_server():
    """Test MCP server basic functionality"""

    print("🚀 Starting MCP server test...")

    server_params = StdioServerParameters(
        command="python3",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            print("✅ Session initialized")

            # List all tools
            tools_result = await session.list_tools()
            tools = tools_result.tools
            tool_names = [tool.name for tool in tools]

            print(f"\n📋 Found {len(tool_names)} tools:")
            for i, name in enumerate(tool_names, 1):
                print(f"   {i:2d}. {name}")

            # Expected tools
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

            # Check all expected tools are present
            missing = set(expected) - set(tool_names)
            extra = set(tool_names) - set(expected)

            if missing:
                print(f"\n❌ Missing tools: {missing}")
                return False
            if extra:
                print(f"\n⚠️  Extra tools: {extra}")

            print("\n✅ All 14 expected tools are present")

            # Test a few basic tool calls
            print("\n🔧 Testing tool calls...")

            # Test 1: get_metadata
            try:
                result = await session.call_tool("get_metadata", {})
                data = json.loads(result.content[0].text)
                assert "statistics" in data
                print("   ✅ get_metadata")
            except Exception as e:
                print(f"   ❌ get_metadata: {e}")
                return False

            # Test 2: get_provenance
            try:
                result = await session.call_tool("get_provenance", {})
                data = json.loads(result.content[0].text)
                assert isinstance(data, list)
                print("   ✅ get_provenance")
            except Exception as e:
                print(f"   ❌ get_provenance: {e}")
                return False

            # Test 3: list_available_queries
            try:
                result = await session.call_tool("list_available_queries", {})
                data = json.loads(result.content[0].text)
                assert isinstance(data, list)
                print("   ✅ list_available_queries")
            except Exception as e:
                print(f"   ❌ list_available_queries: {e}")
                return False

            # Test 4: search_genera
            try:
                result = await session.call_tool("search_genera", {
                    "name_pattern": "Paradoxides%",
                    "limit": 5
                })
                data = json.loads(result.content[0].text)
                assert isinstance(data, list)
                assert len(data) > 0
                print(f"   ✅ search_genera (found {len(data)} genera)")
            except Exception as e:
                print(f"   ❌ search_genera: {e}")
                return False

            # Test 5: get_taxonomy_tree
            try:
                result = await session.call_tool("get_taxonomy_tree", {})
                data = json.loads(result.content[0].text)
                assert isinstance(data, list)
                assert len(data) > 0
                print(f"   ✅ get_taxonomy_tree")
            except Exception as e:
                print(f"   ❌ get_taxonomy_tree: {e}")
                return False

            print("\n🎉 All tests passed!")
            return True

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    exit(0 if success else 1)
