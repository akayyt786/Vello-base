"""MCP tools for Analytics (Phase 4 events + Phase 6 SDK batch ingest)."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    # ── Phase 6 SDK: event tracking ──────────────────────────────────────────

    @mcp.tool()
    async def analytics_track_event(
        project_id: str,
        event_name: str,
        properties_json: str = "{}",
        timestamp: str = "",
        anonymous_id: str = "",
        session_id: str = "",
        platform: str = "",
        app_version: str = "",
    ) -> str:
        """Track a single analytics event. Returns the created event with its ID."""
        body: dict = {
            "event_name": event_name,
            "properties": json.loads(properties_json),
            "timestamp": timestamp or "2024-01-01T00:00:00Z",
        }
        if anonymous_id:
            body["anonymous_id"] = anonymous_id
        if session_id:
            body["session_id"] = session_id
        if platform:
            body["platform"] = platform
        if app_version:
            body["app_version"] = app_version
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/analytics/track/",
            json=body,
        ))

    @mcp.tool()
    async def analytics_batch_track(project_id: str, events_json: str) -> str:
        """Batch-track up to 500 analytics events. events_json: JSON array of event objects."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/analytics/batch/",
            json={"events": json.loads(events_json)},
        ))

    @mcp.tool()
    async def analytics_get_summary(project_id: str, days: int = 7) -> str:
        """Get analytics summary: total_events, unique_users, by_event breakdown."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/analytics/sdk-summary/",
            params={"days": days},
        ))

    @mcp.tool()
    async def analytics_list_events(
        project_id: str,
        event_name: str = "",
        limit: int = 50,
    ) -> str:
        """List raw analytics events, optionally filtered by event_name."""
        params: dict = {"limit": limit}
        if event_name:
            params["event_name"] = event_name
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/analytics/sdk-events/",
            params=params,
        ))

    # ── Phase 4: structured events ────────────────────────────────────────────

    @mcp.tool()
    async def analytics_log_event(
        project_id: str,
        event_name: str,
        user_id: str,
        event_params_json: str = "{}",
        platform: str = "web",
        occurred_at: str = "",
    ) -> str:
        """Log a structured analytics event (Phase 4 API with geo + device metadata)."""
        body: dict = {
            "event_name": event_name,
            "user_id": user_id,
            "event_params": json.loads(event_params_json),
            "platform": platform,
        }
        if occurred_at:
            body["occurred_at"] = occurred_at
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/analytics/events/",
            json=body,
        ))

    @mcp.tool()
    async def analytics_set_user_property(
        project_id: str,
        user_id: str,
        name: str,
        value: str,
    ) -> str:
        """Set a user property for analytics segmentation."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/analytics/user-properties/",
            json={"user_id": user_id, "name": name, "value": value},
        ))

    @mcp.tool()
    async def analytics_list_conversion_events(project_id: str) -> str:
        """List all conversion events configured for a project."""
        return json.dumps(await _c.get(
            f"/api/projects/{project_id}/analytics/conversion-events/",
        ))

    @mcp.tool()
    async def analytics_add_conversion_event(project_id: str, event_name: str) -> str:
        """Mark an event name as a conversion event for analytics tracking."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/analytics/conversion-events/",
            json={"event_name": event_name},
        ))

    @mcp.tool()
    async def analytics_query(
        project_id: str,
        metric: str,
        start_date: str,
        end_date: str,
        group_by: str = "",
    ) -> str:
        """Run an analytics query with date range and optional group-by dimension."""
        body: dict = {"metric": metric, "start_date": start_date, "end_date": end_date}
        if group_by:
            body["group_by"] = group_by
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/analytics/query/",
            json=body,
        ))
