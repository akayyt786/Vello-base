"""MCP tools for App Check — device attestation and token verification."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def app_check_list_configs(project_id: str) -> str:
        """List App Check provider configurations for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/app-check/config/"))

    @mcp.tool()
    async def app_check_create_config(
        project_id: str,
        platform: str,
        provider: str,
        config_json: str = "{}",
    ) -> str:
        """Create an App Check config. platform: android|ios|web. provider: play_integrity|device_check|recaptcha."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/app-check/config/",
            json={"platform": platform, "provider": provider, **json.loads(config_json)},
        ))

    @mcp.tool()
    async def app_check_exchange_token(
        project_id: str,
        platform: str,
        attestation_token: str,
    ) -> str:
        """Exchange a platform attestation token for an App Check token."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/app-check/exchange/",
            json={"platform": platform, "token": attestation_token},
        ))

    @mcp.tool()
    async def app_check_verify_token(project_id: str, app_check_token: str) -> str:
        """Verify an App Check token. Returns is_valid and token metadata."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/app-check/verify/",
            json={"token": app_check_token},
        ))

    @mcp.tool()
    async def app_check_list_debug_tokens(project_id: str) -> str:
        """List debug tokens for App Check (development only)."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/app-check/debug-tokens/"))

    @mcp.tool()
    async def app_check_create_debug_token(project_id: str, display_name: str) -> str:
        """Create a debug token for App Check testing in development."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/app-check/debug-tokens/",
            json={"display_name": display_name},
        ))

    @mcp.tool()
    async def app_check_revoke_token(project_id: str, token_id: str) -> str:
        """Revoke an App Check token."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/app-check/tokens/{token_id}/revoke/",
            json={},
        ))
