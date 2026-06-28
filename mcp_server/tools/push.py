"""MCP tools for Push Notifications."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def push_register_token(
        project_id: str,
        token: str,
        platform: str,
        device_id: str = "",
    ) -> str:
        """Register a device push token. platform: android|ios|web."""
        body: dict = {"token": token, "platform": platform}
        if device_id:
            body["device_id"] = device_id
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/push/tokens/",
            json=body,
        ))

    @mcp.tool()
    async def push_list_tokens(project_id: str) -> str:
        """List all registered device tokens for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/push/tokens/"))

    @mcp.tool()
    async def push_list_topics(project_id: str) -> str:
        """List all push notification topics for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/push/topics/"))

    @mcp.tool()
    async def push_create_topic(project_id: str, name: str, description: str = "") -> str:
        """Create a push notification topic for group messaging."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/push/topics/",
            json={"name": name, "description": description},
        ))

    @mcp.tool()
    async def push_send_notification(
        project_id: str,
        title: str,
        body: str,
        topic_id: str = "",
        token_id: str = "",
        data_json: str = "{}",
    ) -> str:
        """Send a push notification to a topic or specific device token."""
        payload: dict = {
            "title": title,
            "body": body,
            "data": json.loads(data_json),
        }
        if topic_id:
            payload["topic"] = topic_id
        if token_id:
            payload["token"] = token_id
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/push/notifications/",
            json=payload,
        ))

    @mcp.tool()
    async def push_list_notifications(project_id: str) -> str:
        """List sent push notifications for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/push/notifications/"))

    @mcp.tool()
    async def push_list_campaigns(project_id: str) -> str:
        """List push notification campaigns for a project."""
        return json.dumps(await _c.get(f"/api/projects/{project_id}/push/campaigns/"))

    @mcp.tool()
    async def push_create_campaign(
        project_id: str,
        name: str,
        title: str,
        body: str,
        scheduled_at: str = "",
    ) -> str:
        """Create a push notification campaign. scheduled_at: ISO datetime string."""
        payload: dict = {"name": name, "title": title, "body": body}
        if scheduled_at:
            payload["scheduled_at"] = scheduled_at
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/push/campaigns/",
            json=payload,
        ))
