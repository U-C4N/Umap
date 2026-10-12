"""Optional official MCP SDK v2 adapter over the shared application services."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from pydantic import ValidationError

from .errors import UmapError
from .workspace import Workspace


def create_server(root: Path | str, *, provider_urls: dict[str, str] | None = None):
    """Create a local stdio server. Its lifespan owns and closes the workspace."""
    try:
        from mcp.server import MCPServer
        from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations
    except ImportError as exc:
        raise UmapError("MCP_NOT_INSTALLED", "Install MCP support with pip install 'umap-art[mcp]'") from exc

    workspace = Workspace(root, provider_urls=provider_urls)

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield {"workspace": workspace}
        finally:
            workspace.close()

    server = MCPServer(
        "Umap", version="0.1.0", lifespan=lifespan,
        instructions=("Create editable maps from keyless public data. Search ambiguous places first and "
                      "choose a candidate; use inspect_map before edits and pass base_revision. Long "
                      "operations return application job_id values. Poll get_job; use cancel_job to "
                      "stop. Data is pinned after acquisition. refresh_map_data explicitly updates it."))
    # Useful to embedded hosts and tests that construct a server without running its lifespan.
    server.umap_workspace = workspace

    def call(function, *args, **kwargs):
        try:
            value = function(*args, **kwargs)
            content = []
            if isinstance(value, dict) and "preview_base64" in value:
                value = dict(value)
                content.append(ImageContent(data=value.pop("preview_base64"), mimeType="image/png"))
            content.insert(0, TextContent(text=json.dumps(value, ensure_ascii=False)))
            return CallToolResult(content=content, structuredContent=value)
        except (UmapError, ValidationError) as exc:
            error = exc.to_dict() if isinstance(exc, UmapError) else {
                "code": "INVALID_SPEC", "message": str(exc)}
            return CallToolResult(content=[TextContent(text=json.dumps(error, ensure_ascii=False))],
                                  structuredContent={"error": error}, isError=True)

    readonly = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
    mutation = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)

    @server.tool(annotations=readonly)
    def find_map_location(query: str, country_code: str | None = None):
        """Find up to five places. Choose candidate_id; do not silently pick an ambiguous result."""
        def find():
            from .sources.photon import find_locations
            return {"candidates": workspace.remember_candidates(find_locations(
                query, cache_dir=workspace._safe(workspace.root / "cache"),
                endpoint=workspace._providers["photon_url"], country_code=country_code))}
        return call(find)

    @server.tool(annotations=readonly)
    def list_styles():
        """List bundled themes and the editable style fields."""
        from .styles import list_styles as styles
        return call(lambda: {"styles": styles(), "editable_fields": [
            "theme", "background", "layers", "order", "rules"]})

    @server.tool(annotations=mutation)
    def create_map(spec: dict, candidate_id: str | None = None, request_id: str | None = None):
        """Create a persistent map and acquisition job. Pass coordinates/bbox or a searched candidate."""
        def create():
            value = json.loads(json.dumps(spec))
            if candidate_id:
                candidate = workspace.resolve_candidate(candidate_id)
                area = value.setdefault("area", {})
                if area.get("bbox") or area.get("center"):
                    raise UmapError("INVALID_LOCATION", "Use candidate_id or coordinates/bbox, exclusively")
                area.pop("place", None)
                area["center"] = candidate["center"]
            elif value.get("area", {}).get("place"):
                raise UmapError("LOCATION_SELECTION_REQUIRED", "Call find_map_location and choose candidate_id")
            return workspace.create_map(value, request_id=request_id)
        return call(create)

    @server.tool(annotations=readonly)
    def inspect_map(map_id: str):
        """Inspect the latest revision, pinned data, recipe, and related jobs."""
        return call(workspace.inspect_map, map_id)

    @server.tool(annotations=mutation)
    def edit_map(map_id: str, base_revision: int, changes: dict | None = None,
                 restore_revision: int | None = None, request_id: str | None = None):
        """Patch title/subtitle/language/page/style/views or restore a revision, then queue preview."""
        return call(workspace.edit_map, map_id, base_revision, changes, restore_revision, request_id)

    @server.tool(annotations=mutation)
    def refresh_map_data(map_id: str, base_revision: int, request_id: str | None = None):
        """Acquire fresh online data. Commit only if base_revision still matches upon completion."""
        return call(workspace.refresh_map_data, map_id, base_revision, request_id)

    @server.tool(annotations=mutation)
    def render_map(map_id: str, revision: int | None = None, formats: list[str] | None = None,
                   preview: bool = False, request_id: str | None = None):
        """Render pinned data with zero network requests. preview produces small PNGs."""
        return call(workspace.render_map, map_id, revision, formats, preview, request_id)

    @server.tool(annotations=readonly)
    def get_job(job_id: str):
        """Read queued/running/succeeded/failed/cancelled/interrupted state and artifact IDs."""
        return call(workspace.get_job, job_id)

    @server.tool(annotations=mutation)
    def cancel_job(job_id: str):
        """Cancel a waiting or active job; successful artifacts remain available."""
        return call(workspace.cancel_job, job_id)

    @server.tool(annotations=readonly)
    def get_artifact(artifact_id: str, include_preview: bool = False):
        """Read artifact metadata and optionally a native MCP image for PNGs at most 1 MiB."""
        return call(workspace.get_artifact, artifact_id, include_preview)

    @server.resource("umap://artifacts/{artifact_id}", mime_type="application/octet-stream")
    def artifact_resource(artifact_id: str) -> bytes:
        """Read a registered artifact up to 16 MiB; get_artifact reports its original MIME type."""
        return workspace.read_artifact(artifact_id)

    @server.resource("umap://artifact-chunks/{artifact_id}/{offset}", mime_type="application/octet-stream")
    def artifact_chunk(artifact_id: str, offset: int) -> bytes:
        """Read up to 1 MiB at a byte offset. Reassemble chunks for larger artifacts."""
        return workspace.read_artifact_chunk(artifact_id, offset)

    return server


def run_server(root: Path | str, *, provider_urls: dict[str, str] | None = None):
    server = create_server(root, provider_urls=provider_urls)
    try:
        server.run(transport="stdio")
    finally:
        server.umap_workspace.close()
