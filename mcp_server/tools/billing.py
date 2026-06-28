"""MCP tools for Billing subscriptions and quota management."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def billing_get_subscription(project_id: str) -> str:
        """Get the current billing subscription for a project (tier, limits, billing_email)."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/billing/subscription/"))

    @mcp.tool()
    async def billing_update_subscription(
        project_id: str,
        billing_email: str = "",
        tier: str = "",
    ) -> str:
        """Update billing subscription fields (billing_email, tier)."""
        body: dict = {}
        if billing_email:
            body["billing_email"] = billing_email
        if tier:
            body["tier"] = tier
        return json.dumps(await _c.patch(
            f"/api/projects/{project_id}/billing/subscription/",
            json=body,
        ))

    @mcp.tool()
    async def billing_get_usage(project_id: str) -> str:
        """Get current month quota usage: api_calls, storage_bytes, bandwidth_bytes with percentages."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/billing/usage/"))

    @mcp.tool()
    async def billing_list_tiers() -> str:
        """List all billing tiers and their limits (free/starter/pro/enterprise). No auth required."""
        return json.dumps(await _c.get("/api/billing/tiers/"))
