"""MCP tools for Social Authentication (Google, GitHub sign-in)."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def social_auth_google(id_token: str) -> str:
        """Sign in with Google using an ID token from the Google Sign-In SDK."""
        data = await _c.post(
            "/api/v1/auth/social/google/",
            json={"id_token": id_token},
        )
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    @mcp.tool()
    async def social_auth_github(code: str) -> str:
        """Sign in with GitHub using an OAuth authorization code."""
        data = await _c.post(
            "/api/v1/auth/social/github/",
            json={"code": code},
        )
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    @mcp.tool()
    async def social_auth_linked_accounts() -> str:
        """List all linked social accounts for the authenticated user."""
        return json.dumps(await _c.get("/api/v1/auth/social/linked/"))

    @mcp.tool()
    async def social_auth_unlink_account(linked_account_id: str) -> str:
        """Unlink a social auth account from the authenticated user."""
        return json.dumps(await _c.delete(
            f"/api/v1/auth/social/linked/{linked_account_id}/",
        ))
