"""
Tests for the OwnFirebase MCP server.

These tests import tool modules and verify:
- Tools are registered on the FastMCP instance
- Tool functions call the correct backend paths
- Auth token state is managed correctly
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from mcp.server.fastmcp import FastMCP


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def fresh_mcp():
    """A fresh FastMCP instance for tool registration tests."""
    return FastMCP("test")


@pytest.fixture(autouse=True)
def reset_client():
    """Reset client state before each test."""
    import mcp_server.client as c
    c._token = None
    c._refresh_token = None
    c._base_url = "http://localhost:8000"
    yield


# ─────────────────────────────────────────────────────────────────────────────
# Test: tool registration
# ─────────────────────────────────────────────────────────────────────────────

class TestToolRegistration:

    def test_auth_tools_registered(self, fresh_mcp):
        from mcp_server.tools import auth
        auth.register(fresh_mcp)
        tool_names = {t.name for t in fresh_mcp._tool_manager.list_tools()}
        assert "auth_login" in tool_names
        assert "auth_register" in tool_names
        assert "auth_me" in tool_names
        assert "auth_logout" in tool_names
        assert "auth_set_token" in tool_names
        assert "auth_set_base_url" in tool_names

    def test_project_tools_registered(self, fresh_mcp):
        from mcp_server.tools import projects
        projects.register(fresh_mcp)
        tool_names = {t.name for t in fresh_mcp._tool_manager.list_tools()}
        assert "project_list" in tool_names
        assert "project_create" in tool_names
        assert "project_get" in tool_names
        assert "project_delete" in tool_names

    def test_data_tools_registered(self, fresh_mcp):
        from mcp_server.tools import data
        data.register(fresh_mcp)
        tool_names = {t.name for t in fresh_mcp._tool_manager.list_tools()}
        assert "data_list_collections" in tool_names
        assert "data_create_document" in tool_names
        assert "data_query" in tool_names

    def test_analytics_tools_registered(self, fresh_mcp):
        from mcp_server.tools import analytics
        analytics.register(fresh_mcp)
        tool_names = {t.name for t in fresh_mcp._tool_manager.list_tools()}
        assert "analytics_track_event" in tool_names
        assert "analytics_batch_track" in tool_names
        assert "analytics_get_summary" in tool_names

    def test_all_modules_register_without_error(self, fresh_mcp):
        from mcp_server.tools import (
            auth, projects, data, storage, functions, push,
            analytics, remoteconfig, webhooks, billing,
            ai, rag, abtesting, enhanced_auth, app_check,
            social_auth, crashlytics,
        )
        for module in (
            auth, projects, data, storage, functions, push,
            analytics, remoteconfig, webhooks, billing,
            ai, rag, abtesting, enhanced_auth, app_check,
            social_auth, crashlytics,
        ):
            module.register(fresh_mcp)
        tool_names = {t.name for t in fresh_mcp._tool_manager.list_tools()}
        assert len(tool_names) >= 60


# ─────────────────────────────────────────────────────────────────────────────
# Test: client state management
# ─────────────────────────────────────────────────────────────────────────────

class TestClientState:

    def test_set_token(self):
        import mcp_server.client as c
        c.set_token("abc123", "refresh456")
        assert c.get_token() == "abc123"
        assert c._refresh_token == "refresh456"

    def test_set_base_url(self):
        import mcp_server.client as c
        c.set_base_url("https://api.example.com/")
        assert c._base_url == "https://api.example.com"

    def test_headers_include_bearer(self):
        import mcp_server.client as c
        c.set_token("mytoken")
        headers = c._headers()
        assert headers["Authorization"] == "Bearer mytoken"

    def test_headers_no_auth_when_no_token(self):
        import mcp_server.client as c
        c._token = None
        headers = c._headers()
        assert "Authorization" not in headers


# ─────────────────────────────────────────────────────────────────────────────
# Test: tool logic (mocked HTTP)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestAuthTools:

    async def test_login_stores_token(self, fresh_mcp):
        import mcp_server.client as c
        from mcp_server.tools import auth
        auth.register(fresh_mcp)

        fake_response = {"access": "access_tok", "refresh": "refresh_tok", "user": {"id": "1"}}
        with patch("mcp_server.client.post", new=AsyncMock(return_value=fake_response)):
            tools = {t.name: t for t in fresh_mcp._tool_manager.list_tools()}
            result = await tools["auth_login"].fn(email="a@b.com", password="pass")
            data = json.loads(result)
            assert data["access"] == "access_tok"
        assert c.get_token() == "access_tok"

    async def test_auth_set_base_url_tool(self, fresh_mcp):
        from mcp_server.tools import auth
        auth.register(fresh_mcp)
        tools = {t.name: t for t in fresh_mcp._tool_manager.list_tools()}
        result = await tools["auth_set_base_url"].fn(base_url="https://myserver.com")
        data = json.loads(result)
        assert data["status"] == "base_url set"
        import mcp_server.client as c
        assert c._base_url == "https://myserver.com"


@pytest.mark.asyncio
class TestDataTools:

    async def test_create_document_calls_correct_path(self, fresh_mcp):
        from mcp_server.tools import data
        data.register(fresh_mcp)

        captured = {}
        async def mock_post(path, **kwargs):
            captured["path"] = path
            captured["json"] = kwargs.get("json", {})
            return {"id": "doc123"}

        with patch("mcp_server.client.post", new=mock_post):
            tools = {t.name: t for t in fresh_mcp._tool_manager.list_tools()}
            result = await tools["data_create_document"].fn(
                project_id="proj-uuid",
                collection="users",
                data_json='{"name": "Alice"}',
            )
        assert "proj-uuid" in captured["path"]
        assert "users" in captured["path"]
        data_dict = json.loads(result)
        assert data_dict["id"] == "doc123"

    async def test_data_query_posts_to_correct_endpoint(self, fresh_mcp):
        from mcp_server.tools import data
        data.register(fresh_mcp)

        captured = {}
        async def mock_post(path, **kwargs):
            captured["path"] = path
            return {"results": []}

        with patch("mcp_server.client.post", new=mock_post):
            tools = {t.name: t for t in fresh_mcp._tool_manager.list_tools()}
            await tools["data_query"].fn(
                project_id="proj-uuid",
                collection="items",
                filters_json='[["price", ">", 10]]',
            )
        assert "query" in captured["path"]


@pytest.mark.asyncio
class TestWebhookTools:

    async def test_create_endpoint(self, fresh_mcp):
        from mcp_server.tools import webhooks
        webhooks.register(fresh_mcp)

        captured = {}
        async def mock_post(path, **kwargs):
            captured["path"] = path
            captured["json"] = kwargs.get("json", {})
            return {"id": "ep123", "secret": "abc"}

        with patch("mcp_server.client.post", new=mock_post):
            tools = {t.name: t for t in fresh_mcp._tool_manager.list_tools()}
            result = await tools["webhooks_create_endpoint"].fn(
                project_id="proj-uuid",
                url="https://example.com/hook",
                events_json='["data.created"]',
            )
        assert "proj-uuid" in captured["path"]
        assert captured["json"]["url"] == "https://example.com/hook"
        assert captured["json"]["events"] == ["data.created"]


@pytest.mark.asyncio
class TestBillingTools:

    async def test_get_tiers_no_auth_needed(self, fresh_mcp):
        from mcp_server.tools import billing
        billing.register(fresh_mcp)

        async def mock_get(path, **kwargs):
            assert path == "/api/billing/tiers/"
            return {"free": {}, "starter": {}, "pro": {}, "enterprise": {}}

        with patch("mcp_server.client.get", new=mock_get):
            tools = {t.name: t for t in fresh_mcp._tool_manager.list_tools()}
            result = await tools["billing_list_tiers"].fn()
        data = json.loads(result)
        assert "free" in data
        assert "enterprise" in data


@pytest.mark.asyncio
class TestAnalyticsTools:

    async def test_track_event_sends_correct_body(self, fresh_mcp):
        from mcp_server.tools import analytics
        analytics.register(fresh_mcp)

        captured = {}
        async def mock_post(path, **kwargs):
            captured["path"] = path
            captured["json"] = kwargs.get("json", {})
            return {"id": "evt123"}

        with patch("mcp_server.client.post", new=mock_post):
            tools = {t.name: t for t in fresh_mcp._tool_manager.list_tools()}
            await tools["analytics_track_event"].fn(
                project_id="proj-uuid",
                event_name="page_view",
                properties_json='{"url": "/home"}',
                timestamp="2025-01-01T00:00:00Z",
            )
        assert "track" in captured["path"]
        assert captured["json"]["event_name"] == "page_view"
        assert captured["json"]["properties"] == {"url": "/home"}
