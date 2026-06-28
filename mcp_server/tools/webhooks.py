"""MCP tools for Webhook endpoint management and delivery tracking."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def webhooks_list_endpoints(project_id: str) -> str:
        """List all webhook endpoints for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/webhooks/endpoints/"))

    @mcp.tool()
    async def webhooks_create_endpoint(
        project_id: str,
        url: str,
        events_json: str = '["*"]',
        description: str = "",
    ) -> str:
        """Create a webhook endpoint. events_json: JSON array of event types (or ['*'] for all).
        Available events: data.created, data.updated, data.deleted, auth.login, auth.register."""
        body: dict = {
            "url": url,
            "events": json.loads(events_json),
        }
        if description:
            body["description"] = description
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/webhooks/endpoints/",
            json=body,
        ))

    @mcp.tool()
    async def webhooks_get_endpoint(project_id: str, endpoint_id: str) -> str:
        """Get details of a specific webhook endpoint including its secret."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/webhooks/endpoints/{endpoint_id}/",
        ))

    @mcp.tool()
    async def webhooks_update_endpoint(
        project_id: str,
        endpoint_id: str,
        url: str = "",
        events_json: str = "",
        is_active: bool | None = None,
    ) -> str:
        """Update a webhook endpoint. Pass only fields to change."""
        body: dict = {}
        if url:
            body["url"] = url
        if events_json:
            body["events"] = json.loads(events_json)
        if is_active is not None:
            body["is_active"] = is_active
        return json.dumps(await _c.patch(
            f"/api/projects/{project_id}/webhooks/endpoints/{endpoint_id}/",
            json=body,
        ))

    @mcp.tool()
    async def webhooks_delete_endpoint(project_id: str, endpoint_id: str) -> str:
        """Delete a webhook endpoint."""
        return json.dumps(await _c.delete(
            f"/api/projects/{project_id}/webhooks/endpoints/{endpoint_id}/",
        ))

    @mcp.tool()
    async def webhooks_list_deliveries(project_id: str, endpoint_id: str) -> str:
        """List all webhook delivery attempts for an endpoint (status, latency, response)."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/webhooks/endpoints/{endpoint_id}/deliveries/",
        ))

    @mcp.tool()
    async def webhooks_list_available_events() -> str:
        """List all available webhook event types that can be subscribed to."""
        events = [
            "data.created", "data.updated", "data.deleted",
            "auth.login", "auth.register",
            "*",
        ]
        return json.dumps({"available_events": events})
