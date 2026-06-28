"""MCP tools for Crashlytics crash reporting and Performance Monitoring."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    # ── Crash Reporting ───────────────────────────────────────────────────────

    @mcp.tool()
    async def crashlytics_list_groups(project_id: str) -> str:
        """List crash groups (unique crash signatures) for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/crashlytics/groups/"))

    @mcp.tool()
    async def crashlytics_get_group(project_id: str, group_id: str) -> str:
        """Get details of a crash group including occurrence count and stack trace."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/crashlytics/groups/{group_id}/",
        ))

    @mcp.tool()
    async def crashlytics_list_reports(
        project_id: str,
        group_id: str = "",
        limit: int = 20,
    ) -> str:
        """List individual crash reports. Optionally filter by crash group."""
        params: dict = {"limit": limit}
        if group_id:
            params["group"] = group_id
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/crashlytics/reports/",
            params=params,
        ))

    @mcp.tool()
    async def crashlytics_report_crash(
        project_id: str,
        error_message: str,
        stack_trace: str,
        platform: str = "android",
        app_version: str = "",
        user_id: str = "",
    ) -> str:
        """Submit a crash report from a client app."""
        body: dict = {
            "error_message": error_message,
            "stack_trace": stack_trace,
            "platform": platform,
        }
        if app_version:
            body["app_version"] = app_version
        if user_id:
            body["user_id"] = user_id
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/crashlytics/reports/",
            json=body,
        ))

    @mcp.tool()
    async def crashlytics_get_summary(project_id: str) -> str:
        """Get crash summary statistics: total crashes, affected users, crash-free rate."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/crashlytics/summary/",
        ))

    # ── Performance Monitoring ────────────────────────────────────────────────

    @mcp.tool()
    async def perf_list_traces(project_id: str, limit: int = 20) -> str:
        """List performance traces for a project."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/crashlytics/traces/",
            params={"limit": limit},
        ))

    @mcp.tool()
    async def perf_record_trace(
        project_id: str,
        name: str,
        duration_ms: int,
        attributes_json: str = "{}",
    ) -> str:
        """Record a performance trace (e.g. app startup time, network request latency)."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/crashlytics/traces/",
            json={
                "name": name,
                "duration_ms": duration_ms,
                "attributes": json.loads(attributes_json),
            },
        ))

    @mcp.tool()
    async def perf_list_network_requests(project_id: str, limit: int = 20) -> str:
        """List recorded network request performance metrics."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/crashlytics/network/",
            params={"limit": limit},
        ))
