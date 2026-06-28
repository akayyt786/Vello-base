"""MCP tools for Remote Config parameter management."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    # ── Phase 6 simple key-value store ────────────────────────────────────────

    @mcp.tool()
    async def remoteconfig_list_params(project_id: str) -> str:
        """List all remote config parameters for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/remoteconfig/params/"))

    @mcp.tool()
    async def remoteconfig_create_param(
        project_id: str,
        key: str,
        value: str,
        param_type: str = "string",
        is_active: bool = True,
    ) -> str:
        """Create a remote config parameter. param_type: string|number|boolean|json."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/remoteconfig/params/",
            json={"key": key, "value": value, "param_type": param_type, "is_active": is_active},
        ))

    @mcp.tool()
    async def remoteconfig_update_param(
        project_id: str,
        param_id: str,
        value: str = "",
        is_active: bool | None = None,
    ) -> str:
        """Update a remote config parameter's value or active state."""
        body: dict = {}
        if value:
            body["value"] = value
        if is_active is not None:
            body["is_active"] = is_active
        return json.dumps(await _c.patch(
            f"/api/projects/{project_id}/remoteconfig/params/{param_id}/",
            json=body,
        ))

    @mcp.tool()
    async def remoteconfig_delete_param(project_id: str, param_id: str) -> str:
        """Delete a remote config parameter."""
        return json.dumps(await _c.delete(
            f"/api/projects/{project_id}/remoteconfig/params/{param_id}/",
        ))

    @mcp.tool()
    async def remoteconfig_fetch(project_id: str) -> str:
        """Fetch all active remote config values as a typed dict (number/boolean cast)."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/remoteconfig/fetch/"))

    # ── Phase 4 advanced config (conditions + experiments) ───────────────────

    @mcp.tool()
    async def remoteconfig_list_advanced(project_id: str) -> str:
        """List advanced remote config parameters (with conditions support)."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/config/parameters/"))

    @mcp.tool()
    async def remoteconfig_create_advanced(
        project_id: str,
        key: str,
        default_value: str,
        description: str = "",
    ) -> str:
        """Create an advanced remote config parameter with conditional overrides support."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/config/parameters/",
            json={"key": key, "default_value": default_value, "description": description},
        ))

    @mcp.tool()
    async def remoteconfig_list_conditions(project_id: str, config_id: str) -> str:
        """List conditions for an advanced remote config parameter."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/config/parameters/{config_id}/conditions/",
        ))

    @mcp.tool()
    async def remoteconfig_create_condition(
        project_id: str,
        config_id: str,
        condition_type: str,
        condition_value: str,
        override_value: str,
    ) -> str:
        """Add a conditional override to a remote config parameter."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/config/parameters/{config_id}/conditions/",
            json={
                "condition_type": condition_type,
                "condition_value": condition_value,
                "override_value": override_value,
            },
        ))
