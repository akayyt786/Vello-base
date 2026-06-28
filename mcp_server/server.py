"""
OwnFirebase MCP Server — exposes all backend APIs as AI-callable tools.

Usage:
    # Run standalone (stdio transport for Claude Desktop / AI agents):
    python -m mcp_server.server

    # Or via installed script:
    ownfirebase-mcp

Configuration (environment variables):
    OWNFIREBASE_BASE_URL   Backend base URL (default: http://localhost:8000)
    OWNFIREBASE_TOKEN      JWT access token (optional; use auth_login tool instead)
"""

import os
from mcp.server.fastmcp import FastMCP

# ── Tool modules ─────────────────────────────────────────────────────────────
from mcp_server.tools import auth as _auth
from mcp_server.tools import projects as _projects
from mcp_server.tools import data as _data
from mcp_server.tools import storage as _storage
from mcp_server.tools import functions as _functions
from mcp_server.tools import push as _push
from mcp_server.tools import analytics as _analytics
from mcp_server.tools import remoteconfig as _remoteconfig
from mcp_server.tools import webhooks as _webhooks
from mcp_server.tools import billing as _billing
from mcp_server.tools import ai as _ai
from mcp_server.tools import rag as _rag
from mcp_server.tools import abtesting as _abtesting
from mcp_server.tools import enhanced_auth as _enhanced_auth
from mcp_server.tools import app_check as _app_check
from mcp_server.tools import social_auth as _social_auth
from mcp_server.tools import crashlytics as _crashlytics
import mcp_server.client as _client

# Apply env-var configuration before server starts
if os.environ.get("OWNFIREBASE_BASE_URL"):
    _client.set_base_url(os.environ["OWNFIREBASE_BASE_URL"])
if os.environ.get("OWNFIREBASE_TOKEN"):
    _client.set_token(os.environ["OWNFIREBASE_TOKEN"])

# ── Create FastMCP server ─────────────────────────────────────────────────────
mcp = FastMCP(
    "OwnFirebase",
    instructions="""
OwnFirebase MCP — Firebase-equivalent backend-as-a-service.

Quick start:
  1. auth_set_base_url("http://your-backend:8000")  — point to your backend
  2. auth_login("email", "password")                — authenticate (stores token)
  3. project_list()                                 — see your projects
  4. data_create_document(project_id, "users", '{"name": "Alice"}')

All tools return JSON strings. Project-scoped tools require a project_id UUID.
""",
)

# ── Register all tool modules ─────────────────────────────────────────────────
_auth.register(mcp)
_projects.register(mcp)
_data.register(mcp)
_storage.register(mcp)
_functions.register(mcp)
_push.register(mcp)
_analytics.register(mcp)
_remoteconfig.register(mcp)
_webhooks.register(mcp)
_billing.register(mcp)
_ai.register(mcp)
_rag.register(mcp)
_abtesting.register(mcp)
_enhanced_auth.register(mcp)
_app_check.register(mcp)
_social_auth.register(mcp)
_crashlytics.register(mcp)


def main() -> None:
    """Entry point for ownfirebase-mcp CLI and module execution."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
