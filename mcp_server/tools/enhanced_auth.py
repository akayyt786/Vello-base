"""MCP tools for Enhanced Authentication — phone OTP, MFA TOTP, magic links."""

import json
from mcp.server.fastmcp import FastMCP
import mcp_server.client as _c


def register(mcp: FastMCP) -> None:

    # ── Phone OTP ─────────────────────────────────────────────────────────────

    @mcp.tool()
    async def auth_phone_send_otp(phone: str) -> str:
        """Send an OTP code to a phone number for phone-based sign-in."""
        return json.dumps(await _c.post(
            "/api/v1/auth/phone/send-otp/",
            json={"phone": phone},
        ))

    @mcp.tool()
    async def auth_phone_verify_otp(phone: str, code: str) -> str:
        """Verify the OTP code sent to a phone number. Returns JWT tokens on success."""
        data = await _c.post(
            "/api/v1/auth/phone/verify-otp/",
            json={"phone": phone, "code": code},
        )
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    # ── TOTP MFA ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def auth_mfa_enroll_totp() -> str:
        """Start TOTP MFA enrollment. Returns QR code URI and secret for authenticator app."""
        return json.dumps(await _c.post("/api/v1/auth/mfa/enroll/totp/", json={}))

    @mcp.tool()
    async def auth_mfa_confirm_totp(code: str, device_id: str) -> str:
        """Confirm TOTP enrollment by verifying the first code from the authenticator app."""
        return json.dumps(await _c.post(
            "/api/v1/auth/mfa/confirm/totp/",
            json={"code": code, "device_id": device_id},
        ))

    @mcp.tool()
    async def auth_mfa_verify_totp(code: str, device_id: str) -> str:
        """Verify a TOTP code during login (second factor). Returns JWT on success."""
        data = await _c.post(
            "/api/v1/auth/mfa/verify/totp/",
            json={"code": code, "device_id": device_id},
        )
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    # ── SMS MFA ───────────────────────────────────────────────────────────────

    @mcp.tool()
    async def auth_mfa_enroll_sms(phone: str) -> str:
        """Start SMS MFA enrollment with a phone number."""
        return json.dumps(await _c.post(
            "/api/v1/auth/mfa/enroll/sms/",
            json={"phone": phone},
        ))

    @mcp.tool()
    async def auth_mfa_verify_sms(code: str, device_id: str) -> str:
        """Verify SMS MFA code during login."""
        data = await _c.post(
            "/api/v1/auth/mfa/verify/sms/",
            json={"code": code, "device_id": device_id},
        )
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    # ── Magic Links ───────────────────────────────────────────────────────────

    @mcp.tool()
    async def auth_magic_link_send(email: str) -> str:
        """Send a passwordless magic link to an email address."""
        return json.dumps(await _c.post(
            "/api/v1/auth/magic-link/send/",
            json={"email": email},
        ))

    @mcp.tool()
    async def auth_magic_link_verify(token: str) -> str:
        """Verify a magic link token. Returns JWT tokens on success."""
        data = await _c.post(
            "/api/v1/auth/magic-link/verify/",
            json={"token": token},
        )
        if "access" in data:
            _c.set_token(data["access"], data.get("refresh", ""))
        return json.dumps(data)

    # ── Account management ────────────────────────────────────────────────────

    @mcp.tool()
    async def auth_upgrade_anonymous(email: str, password: str) -> str:
        """Upgrade an anonymous account to a permanent account with email + password."""
        return json.dumps(await _c.post(
            "/api/v1/auth/upgrade/",
            json={"email": email, "password": password},
        ))

    @mcp.tool()
    async def auth_set_password(current_password: str, new_password: str) -> str:
        """Change the authenticated user's password."""
        return json.dumps(await _c.post(
            "/api/v1/auth/set-password/",
            json={"current_password": current_password, "new_password": new_password},
        ))

    @mcp.tool()
    async def auth_mfa_list_devices() -> str:
        """List all MFA devices enrolled for the authenticated user."""
        return json.dumps(await _c.get("/api/v1/auth/mfa/devices/"))

    @mcp.tool()
    async def auth_mfa_delete_device(device_id: str) -> str:
        """Remove an MFA device (TOTP or SMS) from the authenticated user's account."""
        return json.dumps(await _c.delete(f"/api/v1/auth/mfa/devices/{device_id}/"))

    @mcp.tool()
    async def auth_issue_custom_token(project_id: str, uid: str, claims_json: str = "{}") -> str:
        """Issue a custom JWT token for a user with optional custom claims."""
        return json.dumps(await _c.post(
            f"/api/projects/{project_id}/auth/custom-token/",
            json={"uid": uid, "claims": json.loads(claims_json)},
        ))
