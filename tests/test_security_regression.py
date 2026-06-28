"""
Security regression tests.

These tests verify that key security properties hold:
  a. Viewer cannot invoke cloud functions (editor+ required).
  b. Login with is_active=False account is rejected.
  c. User from project A cannot read documents in project B.
  d. TOTP replay attack: same code rejected in the same 30-second window.
  e. Campaign double-fire: second concurrent send returns 409.
"""

import time
from unittest.mock import MagicMock, patch

import pyotp
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from data.models import Document
from enhanced_auth.models import MFADevice
from functions.models import CloudFunction
from push.models import NotificationCampaign


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(user):
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# a. Viewer cannot invoke cloud functions
# ---------------------------------------------------------------------------

@pytest.fixture
def sec_owner(db):
    u = User.objects.create_user("sec_owner@ex.com", "sec_owner@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def sec_viewer(db):
    u = User.objects.create_user("sec_viewer@ex.com", "sec_viewer@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def sec_project(db, sec_owner):
    p = Project.objects.create(
        name="SecProj", slug="sec-proj", owner=sec_owner, is_active=True
    )
    ProjectMembership.objects.create(project=p, user=sec_owner, role="owner")
    return p


@pytest.fixture
def sec_project_with_viewer(db, sec_project, sec_viewer):
    ProjectMembership.objects.create(project=sec_project, user=sec_viewer, role="viewer")
    return sec_project


@pytest.fixture
def sec_http_function(db, sec_project, sec_owner):
    return CloudFunction.objects.create(
        project=sec_project,
        name="sec-fn",
        trigger_type=CloudFunction.TRIGGER_HTTP,
        endpoint_url="https://example.com/sec-webhook",
        is_enabled=True,
        timeout_seconds=10,
        created_by=sec_owner,
        updated_by=sec_owner,
    )


class TestViewerCannotInvokeFunctions:
    def _url(self, project_id, name):
        return f"/api/projects/{project_id}/functions/{name}/invoke/"

    def test_viewer_invoke_returns_403(
        self, sec_project_with_viewer, sec_viewer, sec_http_function
    ):
        """A project viewer must not be able to invoke cloud functions (editor+ required)."""
        client = make_client(sec_viewer)
        resp = client.post(
            self._url(sec_project_with_viewer.id, "sec-fn"),
            {},
            format="json",
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# b. Login with is_active=False is rejected
# ---------------------------------------------------------------------------

LOGIN_URL = "/api/v1/auth/login/"


class TestInactiveUserLoginDenied:
    def test_inactive_user_cannot_login(self, db):
        """
        An account with is_active=False must be rejected at login.

        NOTE: The current login view (api/views.py AuthViewSet.login) does not
        check user.is_active — it only verifies the password. This test documents
        the EXPECTED security behaviour and will fail until the view is fixed to
        add:  if not user.is_active: return 403
        """
        user = User.objects.create_user(
            username="inactive@ex.com",
            email="inactive@ex.com",
            password="pass123",
            is_active=False,
        )
        UserProfile.objects.create(
            user=user, sign_in_provider="password", email_verified=True
        )
        client = APIClient()
        resp = client.post(
            LOGIN_URL,
            {"email": "inactive@ex.com", "password": "pass123"},
            format="json",
        )
        assert resp.status_code in (401, 403), (
            "Inactive account must be rejected at login. "
            f"Got {resp.status_code} instead."
        )


# ---------------------------------------------------------------------------
# c. Cross-project document access is denied
# ---------------------------------------------------------------------------

@pytest.fixture
def user_a(db):
    u = User.objects.create_user("user_a@ex.com", "user_a@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def user_b(db):
    u = User.objects.create_user("user_b@ex.com", "user_b@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def project_a(db, user_a):
    p = Project.objects.create(name="ProjA", slug="proj-a", owner=user_a, is_active=True)
    ProjectMembership.objects.create(project=p, user=user_a, role="owner")
    return p


@pytest.fixture
def project_b(db, user_b):
    p = Project.objects.create(name="ProjB", slug="proj-b", owner=user_b, is_active=True)
    ProjectMembership.objects.create(project=p, user=user_b, role="owner")
    return p


@pytest.fixture
def doc_in_project_b(db, project_b):
    return Document.objects.create(
        project=project_b,
        collection_path="users",
        doc_id="secret-doc",
        data={"secret": "data"},
    )


class TestCrossProjectDocumentAccess:
    def test_user_a_cannot_read_project_b_document(
        self, user_a, project_a, project_b, doc_in_project_b
    ):
        """User who is a member of project A must not access documents in project B."""
        client = make_client(user_a)
        url = f"/api/projects/{project_b.id}/collections/users/docs/secret-doc/"
        resp = client.get(url)
        # The view raises PermissionDenied (403) for non-members.
        # A 404 would also be acceptable (prevents project enumeration).
        assert resp.status_code in (403, 404), (
            f"Expected 403 or 404 for cross-project access, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# d. TOTP replay: same code rejected twice in the same 30-second window
# ---------------------------------------------------------------------------

VERIFY_TOTP_URL = "/api/v1/auth/mfa/verify/totp/"


@pytest.fixture
def totp_user(db):
    u = User.objects.create_user("totp_sec@ex.com", "totp_sec@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def active_totp_device(db, totp_user):
    secret = pyotp.random_base32()
    device = MFADevice.objects.create(
        user=totp_user,
        method=MFADevice.METHOD_TOTP,
        name="Replay Test Device",
        totp_secret=secret,
        is_active=True,
        confirmed_at=timezone.now(),
        # Start with a counter that won't conflict with the current window.
        last_used_counter=-1,
    )
    return device


class TestTOTPReplayPrevention:
    def test_totp_replay_returns_400(self, totp_user, active_totp_device):
        """The same TOTP code submitted twice in one 30-second window must be rejected."""
        client = make_client(totp_user)
        totp = pyotp.TOTP(active_totp_device.totp_secret)
        code = totp.now()

        # First use — must succeed.
        resp1 = client.post(
            VERIFY_TOTP_URL,
            {"device_id": str(active_totp_device.id), "totp_code": code},
            format="json",
        )
        assert resp1.status_code == 200, f"First TOTP use failed: {resp1.json()}"

        # Second use within same 30-second window — must be rejected.
        resp2 = client.post(
            VERIFY_TOTP_URL,
            {"device_id": str(active_totp_device.id), "totp_code": code},
            format="json",
        )
        assert resp2.status_code == 400, (
            f"TOTP replay must return 400, got {resp2.status_code}: {resp2.json()}"
        )
        assert "already used" in resp2.json().get("error", "").lower()


# ---------------------------------------------------------------------------
# e. Campaign double-fire: second send returns 409
# ---------------------------------------------------------------------------

@pytest.fixture
def push_owner(db):
    u = User.objects.create_user("push_sec@ex.com", "push_sec@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def push_project(db, push_owner):
    p = Project.objects.create(
        name="PushSecProj", slug="push-sec-proj", owner=push_owner, is_active=True
    )
    ProjectMembership.objects.create(project=p, user=push_owner, role="owner")
    return p


@pytest.fixture
def draft_campaign(db, push_project):
    return NotificationCampaign.objects.create(
        project=push_project,
        name="Double Fire Campaign",
        title="Sale!",
        body="50% off.",
        status=NotificationCampaign.STATUS_DRAFT,
    )


class TestCampaignDoubleFire:
    def _url(self, project_id, pk):
        return f"/api/projects/{project_id}/push/campaigns/{pk}/send/"

    @patch("push.tasks.send_campaign")
    def test_second_send_returns_409(
        self, mock_task, push_owner, push_project, draft_campaign
    ):
        """
        Calling the send action twice must return 409 on the second call.

        The view uses an atomic compare-and-swap (filter on STATUS_DRAFT +
        update to STATUS_SENDING) so only the first request wins.
        """
        mock_task.delay.return_value = MagicMock(id="camp-task-1")
        client = make_client(push_owner)
        url = self._url(push_project.id, draft_campaign.id)

        # First send — transitions DRAFT → SENDING, fires task.
        resp1 = client.post(url, format="json")
        assert resp1.status_code == 202, f"First send failed: {resp1.json()}"

        # Second send — status is now SENDING, atomic update affects 0 rows → 409.
        resp2 = client.post(url, format="json")
        assert resp2.status_code == 409, (
            f"Second send must return 409, got {resp2.status_code}: {resp2.json()}"
        )
