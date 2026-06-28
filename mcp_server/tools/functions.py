"""MCP tools for Cloud Functions."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def functions_list(project_id: str) -> str:
        """List all cloud functions in a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/functions/"))

    @mcp.tool()
    async def functions_get(project_id: str, name: str) -> str:
        """Get details of a specific cloud function."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/functions/{name}/"))

    @mcp.tool()
    async def functions_create(
        project_id: str,
        name: str,
        runtime: str,
        code: str,
        trigger_type: str = "http",
    ) -> str:
        """Create a new cloud function. runtime: python3.11|nodejs20. trigger_type: http|firestore."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/functions/",
            json={"name": name, "runtime": runtime, "code": code, "trigger_type": trigger_type},
        ))

    @mcp.tool()
    async def functions_update(project_id: str, name: str, code: str) -> str:
        """Update the code of an existing cloud function."""
        return json.dumps(await _c.patch(
            f"/api/projects/{project_id}/functions/{name}/",
            json={"code": code},
        ))

    @mcp.tool()
    async def functions_delete(project_id: str, name: str) -> str:
        """Delete a cloud function."""
        return json.dumps(await _c.delete(f"/api/projects/{project_id}/functions/{name}/"))

    @mcp.tool()
    async def functions_invoke(project_id: str, name: str, payload_json: str = "{}") -> str:
        """Invoke a cloud function. payload_json is a JSON string of input data."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/functions/{name}/invoke/",
            json=json.loads(payload_json),
        ))

    @mcp.tool()
    async def functions_logs(project_id: str, name: str, limit: int = 50) -> str:
        """Get execution logs for a cloud function."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/functions/{name}/logs/",
            params={"limit": limit},
        ))
