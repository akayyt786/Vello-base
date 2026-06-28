"""
Phase 5: Enhanced Auth tests.

Covers PhoneOTP, MFA (TOTP + SMS), Magic Link, and Custom Tokens.
All SMS and email sending is mocked to avoid real external calls.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
import pyotp
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from enhanced_auth.models import (
    PhoneVerification,
    MFADevice,
    MFASMSCode,
    MagicLink,
    CustomToken,
)


# ---------------------------------------------------------------------------
# Module-level helpers / fixtures
# ---------------------------------------------------------------------------

def make_client(user):
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Custom-Token-specific fixtures (kept module-level for reuse across tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def ct_owner(db):
    """Project owner for custom-token tests."""
    u = User.objects.create_user("ct_owner@ex.com", "ct_owner@ex.com", "pass")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def ct_editor(db):
    """User with editor role."""
    u = User.objects.create_user("ct_editor@ex.com", "ct_editor@ex.com", "pass")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def ct_viewer(db):
    """User with viewer role."""
    u = User.objects.create_user("ct_viewer@ex.com", "ct_viewer@ex.com", "pass")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def ct_project(db, ct_owner, ct_editor, ct_viewer):
    """Project with owner, editor, and viewer memberships."""
    p = Project.objects.create(
        name="CT Project",
        slug="ct-project",
        owner=ct_owner,
        is_active=True,
    )
    ProjectMembership.objects.create(project=p, user=ct_owner, role="owner")
    ProjectMembership.objects.create(project=p, user=ct_editor, role="editor")
    ProjectMembership.objects.create(project=p, user=ct_viewer, role="viewer")
    return p


@pytest.fixture
def ct_editor_client(ct_editor):
    return make_client(ct_editor)


@pytest.fixture
def ct_viewer_client(ct_viewer):
    return make_client(ct_viewer)


@pytest.fixture
def ct_owner_client(ct_owner):
    return make_client(ct_owner)


# ---------------------------------------------------------------------------
# TestPhoneOTP
# ---------------------------------------------------------------------------

SEND_OTP_URL = "/api/v1/auth/phone/send-otp/"
VERIFY_OTP_URL = "/api/v1/auth/phone/verify-otp/"


class TestPhoneOTP:

    @patch("enhanced_auth.views.send_sms")
    def test_send_otp_success(self, mock_sms, authenticated_client):
        """Authenticated user sends OTP to a valid E.164 number — 200."""
        mock_sms.return_value = None
        resp = authenticated_client.post(
            SEND_OTP_URL,
            {"phone_number": "+12125551234"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone_number"] == "+12125551234"
        assert "detail" in data
        mock_sms.assert_called_once()

    @patch("enhanced_auth.views.send_sms")
    def test_send_otp_invalid_format(self, mock_sms, authenticated_client):
        """Number without leading '+' fails E.164 validation — 400."""
        resp = authenticated_client.post(
            SEND_OTP_URL,
            {"phone_number": "12125551234"},
            format="json",
        )
        assert resp.status_code == 400
        mock_sms.assert_not_called()

    def test_send_otp_requires_auth(self, api_client):
        """Unauthenticated request returns 401."""
        resp = api_client.post(
            SEND_OTP_URL,
            {"phone_number": "+12125551234"},
            format="json",
        )
        assert resp.status_code == 401

    def test_verify_otp_success(self, authenticated_client, test_user, db):
        """Correct OTP code returns 200 with verified status."""
        pv = PhoneVerification.objects.create(
            user=test_user,
            phone_number="+12125551234",
            otp_code="987654",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        resp = authenticated_client.post(
            VERIFY_OTP_URL,
            {"phone_number": "+12125551234", "otp_code": "987654"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Phone verified" in data["detail"]
        pv.refresh_from_db()
        assert pv.status == PhoneVerification.STATUS_VERIFIED

    def test_verify_otp_wrong_code(self, authenticated_client, test_user, db):
        """Submitting the wrong OTP code returns 400."""
        PhoneVerification.objects.create(
            user=test_user,
            phone_number="+12125550001",
            otp_code="111111",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        resp = authenticated_client.post(
            VERIFY_OTP_URL,
            {"phone_number": "+12125550001", "otp_code": "999999"},
            format="json",
        )
        assert resp.status_code == 400
        assert "Invalid OTP" in resp.json()["error"]

    def test_verify_otp_no_pending(self, authenticated_client):
        """Verifying when no OTP was ever sent returns 400."""
        resp = authenticated_client.post(
            VERIFY_OTP_URL,
            {"phone_number": "+19999999999", "otp_code": "000000"},
            format="json",
        )
        assert resp.status_code == 400
        assert "No pending OTP" in resp.json()["error"]

    def test_verify_otp_expired(self, authenticated_client, test_user, db):
        """An OTP whose expires_at is in the past returns 400."""
        PhoneVerification.objects.create(
            user=test_user,
            phone_number="+12125550002",
            otp_code="222222",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        resp = authenticated_client.post(
            VERIFY_OTP_URL,
            {"phone_number": "+12125550002", "otp_code": "222222"},
            format="json",
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["error"].lower()

    def test_verify_otp_too_many_attempts(self, authenticated_client, test_user, db):
        """
        Reaching MAX_OTP_ATTEMPTS (5) returns 429.
        Pre-load attempts=4 so the next increment hits the limit.
        """
        pv = PhoneVerification.objects.create(
            user=test_user,
            phone_number="+12125550003",
            otp_code="333333",
            attempts=4,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        resp = authenticated_client.post(
            VERIFY_OTP_URL,
            {"phone_number": "+12125550003", "otp_code": "000000"},
            format="json",
        )
        assert resp.status_code == 429
        assert "Too many attempts" in resp.json()["error"]
        pv.refresh_from_db()
        assert pv.status == PhoneVerification.STATUS_EXPIRED


# ---------------------------------------------------------------------------
# TestMFATOTP
# ---------------------------------------------------------------------------

ENROLL_TOTP_URL = "/api/v1/auth/mfa/enroll/totp/"
CONFIRM_TOTP_URL = "/api/v1/auth/mfa/confirm/totp/"
VERIFY_TOTP_URL = "/api/v1/auth/mfa/verify/totp/"
LIST_DEVICES_URL = "/api/v1/auth/mfa/devices/"


class TestMFATOTP:

    def test_enroll_totp_success(self, authenticated_client):
        """Enrolling TOTP returns device_id, secret, and provisioning_uri — 201."""
        resp = authenticated_client.post(
            ENROLL_TOTP_URL,
            {"name": "My Authenticator"},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "device_id" in data
        assert "secret" in data
        assert "provisioning_uri" in data
        assert "otpauth://" in data["provisioning_uri"]

    def test_enroll_totp_requires_auth(self, api_client):
        """Unauthenticated enrollment attempt returns 401."""
        resp = api_client.post(
            ENROLL_TOTP_URL,
            {"name": "Hacker Device"},
            format="json",
        )
        assert resp.status_code == 401

    def test_confirm_totp_valid_code(self, authenticated_client, test_user, db):
        """Correct TOTP code activates the device — 200."""
        secret = pyotp.random_base32()
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_TOTP,
            name="Test TOTP",
            totp_secret=secret,
            is_active=False,
        )
        valid_code = pyotp.TOTP(secret).now()
        resp = authenticated_client.post(
            CONFIRM_TOTP_URL,
            {"device_id": str(device.id), "totp_code": valid_code},
            format="json",
        )
        assert resp.status_code == 200
        device.refresh_from_db()
        assert device.is_active is True
        assert device.confirmed_at is not None

    def test_confirm_totp_invalid_code(self, authenticated_client, test_user, db):
        """Wrong TOTP code returns 400 and leaves device inactive."""
        secret = pyotp.random_base32()
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_TOTP,
            name="Test TOTP Bad",
            totp_secret=secret,
            is_active=False,
        )
        resp = authenticated_client.post(
            CONFIRM_TOTP_URL,
            {"device_id": str(device.id), "totp_code": "000000"},
            format="json",
        )
        assert resp.status_code == 400
        assert "Invalid TOTP" in resp.json()["error"]
        device.refresh_from_db()
        assert device.is_active is False

    def test_confirm_totp_wrong_device(self, authenticated_client, test_user2, db):
        """
        Trying to confirm a device that belongs to another user returns 404.
        authenticated_client is test_user; the device belongs to test_user2.
        """
        secret = pyotp.random_base32()
        other_device = MFADevice.objects.create(
            user=test_user2,
            method=MFADevice.METHOD_TOTP,
            name="Other User Device",
            totp_secret=secret,
            is_active=False,
        )
        valid_code = pyotp.TOTP(secret).now()
        resp = authenticated_client.post(
            CONFIRM_TOTP_URL,
            {"device_id": str(other_device.id), "totp_code": valid_code},
            format="json",
        )
        assert resp.status_code == 404

    def test_verify_totp_success(self, authenticated_client, test_user, db):
        """Valid TOTP code on an active device returns access + refresh JWT — 200."""
        secret = pyotp.random_base32()
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_TOTP,
            name="Active TOTP",
            totp_secret=secret,
            is_active=True,
            confirmed_at=timezone.now(),
        )
        valid_code = pyotp.TOTP(secret).now()
        resp = authenticated_client.post(
            VERIFY_TOTP_URL,
            {"device_id": str(device.id), "totp_code": valid_code},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data
        assert "refresh" in data

    def test_verify_totp_inactive_device(self, authenticated_client, test_user, db):
        """Attempting to verify with an unconfirmed (inactive) device returns 404."""
        secret = pyotp.random_base32()
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_TOTP,
            name="Inactive TOTP",
            totp_secret=secret,
            is_active=False,
        )
        valid_code = pyotp.TOTP(secret).now()
        resp = authenticated_client.post(
            VERIFY_TOTP_URL,
            {"device_id": str(device.id), "totp_code": valid_code},
            format="json",
        )
        assert resp.status_code == 404

    def test_list_mfa_devices(self, authenticated_client, test_user, db):
        """GET /mfa/devices/ returns only the authenticated user's active devices."""
        active = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_TOTP,
            name="Active Device",
            totp_secret=pyotp.random_base32(),
            is_active=True,
            confirmed_at=timezone.now(),
        )
        # inactive device — should NOT appear
        MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_TOTP,
            name="Inactive Device",
            totp_secret=pyotp.random_base32(),
            is_active=False,
        )
        resp = authenticated_client.get(LIST_DEVICES_URL)
        assert resp.status_code == 200
        data = resp.json()
        ids = [d["id"] for d in data]
        assert str(active.id) in ids
        # Only active devices are listed
        assert all(d["is_active"] for d in data)


# ---------------------------------------------------------------------------
# TestMFASMS
# ---------------------------------------------------------------------------

ENROLL_SMS_URL = "/api/v1/auth/mfa/enroll/sms/"
CONFIRM_SMS_URL = "/api/v1/auth/mfa/confirm/sms/"
VERIFY_SMS_URL = "/api/v1/auth/mfa/verify/sms/"
DEVICE_DELETE_URL = "/api/v1/auth/mfa/devices/{device_id}/"
SEND_SMS_CODE_URL = "/api/v1/auth/mfa/send-sms-code/{device_id}/"


class TestMFASMS:

    @patch("enhanced_auth.views.send_sms")
    def test_enroll_sms_success(self, mock_sms, authenticated_client):
        """Enrolling an SMS MFA device returns device_id — 201."""
        mock_sms.return_value = None
        resp = authenticated_client.post(
            ENROLL_SMS_URL,
            {"phone_number": "+12125550100", "name": "My Phone"},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "device_id" in data
        mock_sms.assert_called_once()

    @patch("enhanced_auth.views.send_sms")
    def test_enroll_sms_invalid_phone(self, mock_sms, authenticated_client):
        """Non-E.164 phone number during SMS enrollment returns 400."""
        resp = authenticated_client.post(
            ENROLL_SMS_URL,
            {"phone_number": "2125550100", "name": "Bad Phone"},
            format="json",
        )
        assert resp.status_code == 400
        mock_sms.assert_not_called()

    def test_confirm_sms_valid_code(self, authenticated_client, test_user, db):
        """Correct SMS code activates the device — 200."""
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_SMS,
            name="SMS Device",
            phone_number="+12125550200",
            is_active=False,
        )
        MFASMSCode.objects.create(
            device=device,
            code="456789",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        resp = authenticated_client.post(
            CONFIRM_SMS_URL,
            {"device_id": str(device.id), "code": "456789"},
            format="json",
        )
        assert resp.status_code == 200
        device.refresh_from_db()
        assert device.is_active is True
        assert device.confirmed_at is not None

    def test_confirm_sms_wrong_code(self, authenticated_client, test_user, db):
        """Wrong SMS code returns 400 and leaves device inactive."""
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_SMS,
            name="SMS Device Wrong",
            phone_number="+12125550201",
            is_active=False,
        )
        MFASMSCode.objects.create(
            device=device,
            code="654321",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        resp = authenticated_client.post(
            CONFIRM_SMS_URL,
            {"device_id": str(device.id), "code": "000000"},
            format="json",
        )
        assert resp.status_code == 400
        assert "Invalid code" in resp.json()["error"]
        device.refresh_from_db()
        assert device.is_active is False

    def test_confirm_sms_expired(self, authenticated_client, test_user, db):
        """Expired SMS code returns 400."""
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_SMS,
            name="SMS Device Expired",
            phone_number="+12125550202",
            is_active=False,
        )
        MFASMSCode.objects.create(
            device=device,
            code="111222",
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        resp = authenticated_client.post(
            CONFIRM_SMS_URL,
            {"device_id": str(device.id), "code": "111222"},
            format="json",
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["error"].lower()

    def test_delete_mfa_device(self, authenticated_client, test_user, db):
        """DELETE /mfa/devices/<id>/ returns 204 and removes the device."""
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_TOTP,
            name="To Be Deleted",
            totp_secret=pyotp.random_base32(),
            is_active=True,
            confirmed_at=timezone.now(),
        )
        url = DEVICE_DELETE_URL.format(device_id=str(device.id))
        resp = authenticated_client.delete(url)
        assert resp.status_code == 204
        assert not MFADevice.objects.filter(id=device.id).exists()

    @patch("enhanced_auth.views.send_sms")
    def test_send_sms_code_active_device(self, mock_sms, authenticated_client, test_user, db):
        """POSTing to send-sms-code sends a new code to an active SMS device — 200."""
        mock_sms.return_value = None
        device = MFADevice.objects.create(
            user=test_user,
            method=MFADevice.METHOD_SMS,
            name="Active SMS",
            phone_number="+12125550300",
            is_active=True,
            confirmed_at=timezone.now(),
        )
        url = SEND_SMS_CODE_URL.format(device_id=str(device.id))
        resp = authenticated_client.post(url)
        assert resp.status_code == 200
        assert "detail" in resp.json()
        mock_sms.assert_called_once()
        # Verify the phone number passed to send_sms matches the device
        called_phone = mock_sms.call_args[0][0]
        assert called_phone == "+12125550300"
        # A new MFASMSCode should have been created
        assert MFASMSCode.objects.filter(device=device).exists()


# ---------------------------------------------------------------------------
# TestMagicLink
# ---------------------------------------------------------------------------

SEND_MAGIC_LINK_URL = "/api/v1/auth/magic-link/send/"
VERIFY_MAGIC_LINK_URL = "/api/v1/auth/magic-link/verify/"


class TestMagicLink:

    @patch("enhanced_auth.views.send_magic_link_email")
    def test_send_magic_link_registered_email(self, mock_email, api_client, test_user, db):
        """Sending to a registered email returns 200 with a success message."""
        mock_email.return_value = None
        resp = api_client.post(
            SEND_MAGIC_LINK_URL,
            {"email": test_user.email},
            format="json",
        )
        assert resp.status_code == 200
        assert "login link" in resp.json()["detail"].lower()
        mock_email.assert_called_once()

    @patch("enhanced_auth.views.send_magic_link_email")
    def test_send_magic_link_unknown_email(self, mock_email, api_client, db):
        """
        Sending to an unknown email still returns 200 — no email enumeration.
        send_magic_link_email must NOT be called (user doesn't exist).
        """
        resp = api_client.post(
            SEND_MAGIC_LINK_URL,
            {"email": "ghost@nowhere.example"},
            format="json",
        )
        assert resp.status_code == 200
        # Same message as for registered email
        assert "login link" in resp.json()["detail"].lower()
        mock_email.assert_not_called()

    def test_verify_magic_link_success(self, api_client, test_user, db):
        """Valid, unused, unexpired token returns access + refresh JWT — 200."""
        link = MagicLink.objects.create(
            user=test_user,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        resp = api_client.get(
            VERIFY_MAGIC_LINK_URL,
            {"token": str(link.token)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        link.refresh_from_db()
        assert link.is_used is True

    def test_verify_magic_link_used(self, api_client, test_user, db):
        """An already-used magic link token returns 400."""
        link = MagicLink.objects.create(
            user=test_user,
            is_used=True,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        resp = api_client.get(
            VERIFY_MAGIC_LINK_URL,
            {"token": str(link.token)},
        )
        assert resp.status_code == 400
        assert "already used" in resp.json()["error"].lower()

    def test_verify_magic_link_expired(self, api_client, test_user, db):
        """An expired magic link token returns 400."""
        link = MagicLink.objects.create(
            user=test_user,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        resp = api_client.get(
            VERIFY_MAGIC_LINK_URL,
            {"token": str(link.token)},
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["error"].lower()

    def test_verify_magic_link_missing_token(self, api_client, db):
        """Request without a token query param returns 400."""
        resp = api_client.get(VERIFY_MAGIC_LINK_URL)
        assert resp.status_code == 400
        assert "token is required" in resp.json()["error"].lower()

    def test_verify_magic_link_invalid_token(self, api_client, db):
        """A well-formed UUID that doesn't match any MagicLink returns 404."""
        resp = api_client.get(
            VERIFY_MAGIC_LINK_URL,
            {"token": str(uuid.uuid4())},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TestCustomToken
# ---------------------------------------------------------------------------

CUSTOM_TOKEN_URL = "/api/projects/{project_id}/auth/custom-token/"


class TestCustomToken:

    def test_issue_custom_token_as_editor(self, ct_editor_client, ct_project):
        """An editor-role member can issue a custom token — returns JWT + expires_at."""
        url = CUSTOM_TOKEN_URL.format(project_id=str(ct_project.id))
        resp = ct_editor_client.post(
            url,
            {"uid": "user-abc-123", "claims": {}},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert "expires_at" in data
        # Verify the JWT is decodable
        import jwt
        from django.conf import settings
        secret = getattr(settings, "JWT_SIGNING_KEY", settings.SECRET_KEY)
        payload = jwt.decode(data["token"], secret, algorithms=["HS256"])
        assert payload["uid"] == "user-abc-123"
        assert str(payload["project_id"]) == str(ct_project.id)

    def test_issue_custom_token_as_viewer(self, ct_viewer_client, ct_project):
        """A viewer-role member gets 403 when attempting to issue a custom token."""
        url = CUSTOM_TOKEN_URL.format(project_id=str(ct_project.id))
        resp = ct_viewer_client.post(
            url,
            {"uid": "user-viewer", "claims": {}},
            format="json",
        )
        assert resp.status_code == 403
        assert "Editor role required" in resp.json()["error"]

    def test_issue_custom_token_with_claims(self, ct_editor_client, ct_project):
        """Custom claims are embedded in the issued JWT payload."""
        url = CUSTOM_TOKEN_URL.format(project_id=str(ct_project.id))
        custom_claims = {"role": "superadmin", "tenant": "acme", "premium": True}
        resp = ct_editor_client.post(
            url,
            {"uid": "user-claims-test", "claims": custom_claims},
            format="json",
        )
        assert resp.status_code == 201
        import jwt
        from django.conf import settings
        secret = getattr(settings, "JWT_SIGNING_KEY", settings.SECRET_KEY)
        payload = jwt.decode(resp.json()["token"], secret, algorithms=["HS256"])
        assert payload["claims"] == custom_claims
        # Verify the CustomToken record was persisted
        assert CustomToken.objects.filter(
            project=ct_project, uid="user-claims-test"
        ).exists()

    def test_issue_custom_token_wrong_project(self, ct_editor_client, db):
        """
        An editor of project A trying to issue a token for a project they don't
        belong to returns 404 (no membership found).
        """
        # Create a completely separate project; ct_editor has no membership here.
        owner = User.objects.create_user("other_owner@ex.com", "other_owner@ex.com", "pass")
        UserProfile.objects.create(user=owner, sign_in_provider="password", email_verified=True)
        other_project = Project.objects.create(
            name="Other Project",
            slug="other-project-ct",
            owner=owner,
            is_active=True,
        )
        ProjectMembership.objects.create(project=other_project, user=owner, role="owner")

        url = CUSTOM_TOKEN_URL.format(project_id=str(other_project.id))
        resp = ct_editor_client.post(
            url,
            {"uid": "hacker-uid", "claims": {}},
            format="json",
        )
        assert resp.status_code == 404

    def test_issue_custom_token_requires_auth(self, api_client, ct_project):
        """Unauthenticated request to issue a custom token returns 401."""
        url = CUSTOM_TOKEN_URL.format(project_id=str(ct_project.id))
        resp = api_client.post(
            url,
            {"uid": "anon-user", "claims": {}},
            format="json",
        )
        assert resp.status_code == 401
