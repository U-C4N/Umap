"""Official MCP SDK calls verify registration, errors, and native preview handling."""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

pytest.importorskip("mcp")

from umap_art.mcp_server import create_server


def test_registered_tools_and_errors_are_protocol_errors(tmp_path):
    async def scenario():
        server = create_server(tmp_path)
        try:
            tools = await server.list_tools()
            assert {tool.name for tool in tools} == {
                "find_map_location", "list_styles", "create_map", "inspect_map", "edit_map",
                "refresh_map_data", "render_map", "get_job", "cancel_job", "get_artifact"}
            styles = await server.call_tool("list_styles", {})
            assert not styles.is_error
            assert len(styles.structured_content["styles"]) == 2
            missing = await server.call_tool("inspect_map", {"map_id": "missing"})
            assert missing.is_error
            assert missing.structured_content["error"]["code"] == "MAP_NOT_FOUND"
            invalid = await server.call_tool("create_map", {"spec": {"area": {"center": [99, 999]}}})
            assert invalid.is_error
            assert invalid.structured_content["error"]["code"] == "INVALID_SPEC"
            unresolved = await server.call_tool("create_map", {"spec": {"area": {"place": "Paris"}}})
            assert unresolved.is_error
            assert unresolved.structured_content["error"]["code"] == "LOCATION_SELECTION_REQUIRED"
        finally:
            server.umap_workspace.close()
    asyncio.run(scenario())


def test_mcp_rejects_arbitrary_source_urls(tmp_path):
    async def scenario():
        server = create_server(tmp_path)
        try:
            result = await server.call_tool("create_map", {"spec": {
                "area": {"center": [29, 41]}, "source": {"overpass_url": "http://localhost/private"}}})
            assert result.is_error
            assert result.structured_content["error"]["code"] == "PROVIDER_NOT_ALLOWED"
        finally:
            server.umap_workspace.close()
    asyncio.run(scenario())


def test_search_candidate_is_persisted_and_selected_explicitly(tmp_path, monkeypatch):
    from umap_art.sources import photon
    monkeypatch.setattr(photon, "find_locations", lambda *args, **kwargs: [
        {"label": "Kadıköy, İstanbul", "center": [29.03, 40.99], "provider": "photon"},
        {"label": "Kadıköy, Yalova", "center": [29.23, 40.62], "provider": "photon"}])
    async def scenario():
        server = create_server(tmp_path)
        try:
            found = await server.call_tool("find_map_location", {"query": "Kadıköy"})
            values = found.structured_content["candidates"]
            assert len(values) == 2
            assert server.umap_workspace.resolve_candidate(values[0]["candidate_id"])["center"] == [29.03, 40.99]
            # Prevent acquisition; this test verifies the shared create contract only.
            monkeypatch.setattr(server.umap_workspace, "create_map", lambda spec, **kwargs: {"spec": spec})
            selected = await server.call_tool("create_map", {
                "spec": {"area": {"scale_denominator": 5000}}, "candidate_id": values[1]["candidate_id"]})
            assert selected.structured_content["spec"]["area"]["center"] == [29.23, 40.62]
        finally:
            server.umap_workspace.close()
    asyncio.run(scenario())


def test_real_stdio_roundtrip_and_shutdown_releases_workspace(tmp_path):
    from mcp.client import Client
    from mcp.client.stdio import StdioServerParameters

    from umap_art.workspace import Workspace
    async def scenario():
        params = StdioServerParameters(command=sys.executable,
            args=["-m", "umap_art.cli", "mcp", "--workspace", str(tmp_path)], env=dict(os.environ))
        async with asyncio.timeout(15):
            async with Client(params, read_timeout_seconds=10) as client:
                tools = await client.list_tools()
                assert len(tools.tools) == 10
                result = await client.call_tool("list_styles")
                assert not result.is_error
                assert len(result.structured_content["styles"]) == 2
    asyncio.run(scenario())
    with Workspace(tmp_path, start_worker=False):
        pass
