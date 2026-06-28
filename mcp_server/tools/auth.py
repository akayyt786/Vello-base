"""MCP tools for authentication (Phase 1 + Phase 5 enhanced auth)."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def auth_register(email: str, password: str) -> str:
        """Register a new user account. Returns JWT access + refresh tokens."""
        data = await _c.post("/api/v1/auth/register/", json={"email": email, "password": password})
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    @mcp.tool()
    async def auth_login(email: str, password: str) -> str:
        """Login with email + password. Stores JWT token for subsequent calls."""
        data = await _c.post("/api/v1/auth/login/", json={"email": email, "password": password})
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    @mcp.tool()
    async def auth_refresh(refresh_token: str) -> str:
        """Refresh JWT access token using a refresh token."""
        data = await _c.post("/api/v1/auth/refresh/", json={"refresh": refresh_token})
        if "access" in data:
            _c.set_token(data["access"])
        return json.dumps(data)

    @mcp.tool()
    async def auth_me() -> str:
        """Get the currently authenticated user's profile."""
        return json.dumps(await _c.get("/api/v1/auth/me/"))

    @mcp.tool()
    async def auth_logout(refresh_token: str) -> str:
        """Logout — blacklist the refresh token."""
        return json.dumps(await _c.post("/api/v1/auth/logout/", json={"refresh": refresh_token}))

    @mcp.tool()
    async def auth_anonymous_signin() -> str:
        """Sign in anonymously (no email/password). Returns JWT tokens."""
        data = await _c.post("/api/v1/auth/anonymous-signin/", json={})
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    @mcp.tool()
    async def auth_set_custom_claims(user_id: str, claims: str) -> str:
        """Set custom JWT claims for a user. claims is a JSON string dict."""
        return json.dumps(await _c.post(
            "/api/v1/auth/set-custom-claims/",
            json={"user_id": user_id, "claims": json.loads(claims)},
        ))

    @mcp.tool()
    async def auth_set_token(access_token: str, refresh_token: str = "") -> str:
        """Manually set the JWT token (useful if you already have one)."""
        _c.set_token(access_token, refresh_token)
        return json.dumps({"status": "token set"})

    @mcp.tool()
    async def auth_set_base_url(base_url: str) -> str:
        """Set the OwnFirebase backend base URL (default: http://localhost:8000)."""
        _c.set_base_url(base_url)
        return json.dumps({"status": "base_url set", "base_url": base_url})
