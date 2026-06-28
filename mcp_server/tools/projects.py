"""MCP tools for project and membership management."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def project_list() -> str:
        """List all projects the authenticated user is a member of."""
        return json.dumps(await _c.get("/api/v1/projects/"))

    @mcp.tool()
    async def project_create(name: str, slug: str) -> str:
        """Create a new project. slug must be unique URL-safe string."""
        return json.dumps(await _c.post("/api/v1/projects/", json={"name": name, "slug": slug}))

    @mcp.tool()
    async def project_get(project_id: str) -> str:
        """Get details of a specific project by its UUID."""
        return json.dumps(await _c.get(f"/api/v1/projects/{project_id}/"))

    @mcp.tool()
    async def project_update(project_id: str, name: str = "", slug: str = "") -> str:
        """Update project name and/or slug. Pass only fields to change."""
        body: dict = {}
        if name:
            body["name"] = name
        if slug:
            body["slug"] = slug
        return json.dumps(await _c.patch(f"/api/v1/projects/{project_id}/", json=body))

    @mcp.tool()
    async def project_delete(project_id: str) -> str:
        """Delete a project permanently. Requires owner role."""
        return json.dumps(await _c.delete(f"/api/v1/projects/{project_id}/"))

    @mcp.tool()
    async def membership_list() -> str:
        """List all project memberships for the authenticated user."""
        return json.dumps(await _c.get("/api/v1/memberships/"))

    @mcp.tool()
    async def membership_add(project_id: str, email: str, role: str = "viewer") -> str:
        """Add a member to a project. role: owner|editor|viewer."""
        return json.dumps(await _c.post(
            "/api/v1/memberships/",
            json={"project": project_id, "email": email, "role": role},
        ))

    @mcp.tool()
    async def membership_remove(membership_id: str) -> str:
        """Remove a member from a project by membership ID."""
        return json.dumps(await _c.delete(f"/api/v1/memberships/{membership_id}/"))

    @mcp.tool()
    async def rules_get(project_id: str) -> str:
        """Get security rules for a project."""
        return json.dumps(await _c.get(f"/api/v1/projects/{project_id}/rules/"))

    @mcp.tool()
    async def rules_update(project_id: str, rules_json: str) -> str:
        """Update security rules for a project. rules_json is a JSON string."""
        return json.dumps(await _c.post(
            f"/api/v1/projects/{project_id}/rules/",
            json=json.loads(rules_json),
        ))

    @mcp.tool()
    async def rules_test(project_id: str, operation: str, path: str, auth_uid: str = "") -> str:
        """Test whether a security rule allows an operation on a path."""
        return json.dumps(await _c.post(
            f"/api/v1/projects/{project_id}/rules/test/",
            json={"operation": operation, "path": path, "auth": {"uid": auth_uid}},
        ))
