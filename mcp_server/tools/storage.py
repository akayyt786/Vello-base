"""MCP tools for Cloud Storage (upload URLs, file management)."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def storage_get_upload_url(
        project_id: str,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Get a pre-signed upload URL for a file. Returns the upload URL and file metadata."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/storage/upload-url/",
            json={"path": path, "content_type": content_type},
        ))

    @mcp.tool()
    async def storage_confirm_upload(project_id: str, path: str) -> str:
        """Confirm that a file upload completed successfully."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/storage/confirm/",
            json={"path": path},
        ))

    @mcp.tool()
    async def storage_list_files(project_id: str, prefix: str = "") -> str:
        """List files in storage, optionally filtered by path prefix."""
        params = {}
        if prefix:
            params["prefix"] = prefix
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/storage/files/",
            params=params,
        ))

    @mcp.tool()
    async def storage_get_file(project_id: str, path: str) -> str:
        """Get metadata and download URL for a specific file."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/storage/files/{path}/"))

    @mcp.tool()
    async def storage_delete_file(project_id: str, path: str) -> str:
        """Delete a file from storage."""
        return json.dumps(await _c.delete(f"/api/projects/{project_id}/storage/files/{path}/"))
