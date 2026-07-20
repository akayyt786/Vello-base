"""
Phase 5A comprehensive tests.

Covers:
  - Social Auth: Google sign-in, GitHub sign-in
  - Linked Accounts: list, unlink
  - Anonymous Account Upgrade
  - Set Password
  - A/B Testing: experiments, variants, assignment, conversion, results
"""

import hashlib
import pytest
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from social_auth.models import SocialAccount
from abtesting.models import Experiment, ExperimentVariant, ExperimentAssignment, ExperimentConversion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(user):
    """Return an authenticated APIClient for the given user."""
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


def _google_provider_data(uid="google-sub-001", email="googleuser@example.com"):
    """Return a fake Google provider_data dict."""
    return {
        "provider_uid": uid,
        "email": email,
        "email_verified": True,
        "name": "Google User",
        "avatar_url": "https://example.com/avatar.png",
        "raw_data": {"sub": uid, "email": email},
    }


def _github_provider_data(uid="gh-12345", email="githubuser@example.com"):
    """Return a fake GitHub provider_data dict."""
    return {
        "provider_uid": uid,
        "email": email,
        "email_verified": True,
        "name": "GitHub User",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        "raw_data": {"id": int(uid.replace("gh-", "")), "email": email},
    }


def _apple_provider_data(uid="apple-sub-001", email="appleuser@example.com", email_verified=True):
    """Return a fake Apple provider_data dict (no name/avatar -- Apple's ID token never carries them)."""
    return {
        "provider_uid": uid,
        "email": email,
        "email_verified": email_verified,
        "name": "",
        "avatar_url": "",
        "raw_data": {"sub": uid, "email": email},
    }


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner(db):
    u = User.objects.create_user("p5a_owner@ex.com", "p5a_owner@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def editor(db):
    u = User.objects.create_user("p5a_editor@ex.com", "p5a_editor@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def viewer(db):
    u = User.objects.create_user("p5a_viewer@ex.com", "p5a_viewer@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def project(db, owner, editor, viewer):
    p = Project.objects.create(
        name="Phase5A Project",
        slug="phase5a-proj",
        owner=owner,
        is_active=True,
    )
    ProjectMembership.objects.create(project=p, user=owner, role="owner")
    ProjectMembership.objects.create(project=p, user=editor, role="editor")
    ProjectMembership.objects.create(project=p, user=viewer, role="viewer")
    return p


@pytest.fixture
def owner_client(owner):
    return make_client(owner)


@pytest.fixture
def editor_client(editor):
    return make_client(editor)


@pytest.fixture
def viewer_client(viewer):
    return make_client(viewer)


# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

GOOGLE_SIGNIN_URL = "/api/v1/auth/social/google/"
GITHUB_SIGNIN_URL = "/api/v1/auth/social/github/"
APPLE_SIGNIN_URL = "/api/v1/auth/social/apple/"
LINKED_URL = "/api/v1/auth/social/linked/"
UPGRADE_URL = "/api/v1/auth/upgrade/"
SET_PASSWORD_URL = "/api/v1/auth/set-password/"


def ab_experiments_url(project_id):
    return f"/api/projects/{project_id}/abtesting/experiments/"


def ab_experiment_url(project_id, pk):
    return f"/api/projects/{project_id}/abtesting/experiments/{pk}/"


def ab_start_url(project_id, pk):
    return f"/api/projects/{project_id}/abtesting/experiments/{pk}/start/"


def ab_assign_url(project_id, pk):
    return f"/api/projects/{project_id}/abtesting/experiments/{pk}/assign/"


def ab_convert_url(project_id, pk):
    return f"/api/projects/{project_id}/abtesting/experiments/{pk}/convert/"


def ab_results_url(project_id, pk):
    return f"/api/projects/{project_id}/abtesting/experiments/{pk}/results/"


# ===========================================================================
# TestSocialAuthGoogle
# ===========================================================================

@pytest.mark.django_db
class TestSocialAuthGoogle:

    @patch("social_auth.views.verify_google_id_token")
    def test_google_signin_new_user(self, mock_verify, api_client):
        """New user via Google returns 201 with access + refresh tokens."""
        mock_verify.return_value = (_google_provider_data(), None)

        resp = api_client.post(GOOGLE_SIGNIN_URL, {"id_token": "fake-google-token"}, format="json")

        assert resp.status_code == 201
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert "user_id" in data
        assert data.get("is_new") is True

    @patch("social_auth.views.verify_google_id_token")
    def test_google_signin_existing_user(self, mock_verify, db):
        """Existing user (via pre-created SocialAccount) returns 200 with the same user id."""
        # Create the user + SocialAccount first
        user = User.objects.create_user(
            username="google_existing@ex.com",
            email="google_existing@ex.com",
            password=None,
        )
        UserProfile.objects.create(user=user, sign_in_provider="google", email_verified=True)
        SocialAccount.objects.create(
            user=user,
            provider="google",
            provider_uid="google-sub-existing",
            email="google_existing@ex.com",
        )

        mock_verify.return_value = (
            _google_provider_data(uid="google-sub-existing", email="google_existing@ex.com"),
            None,
        )

        client = APIClient()
        resp = client.post(GOOGLE_SIGNIN_URL, {"id_token": "fake-token"}, format="json")

        assert resp.status_code == 200
        data = resp.json()
        assert str(user.id) == data["user_id"]
        assert "access" in data
        assert "refresh" in data

    @patch("social_auth.views.verify_google_id_token")
    def test_google_signin_invalid_token(self, mock_verify, api_client):
        """Invalid Google token returns 400 with an error message."""
        mock_verify.return_value = (None, "Invalid Google ID token.")

        resp = api_client.post(GOOGLE_SIGNIN_URL, {"id_token": "bad-token"}, format="json")

        assert resp.status_code == 400
        assert "error" in resp.json()

    @patch("social_auth.views.verify_google_id_token")
    def test_google_signin_links_by_email(self, mock_verify, db):
        """
        When a user with the same email already exists (no SocialAccount),
        sign-in should link a new SocialAccount and return the existing user.
        """
        email = "link_by_email@ex.com"
        existing_user = User.objects.create_user(
            username=email, email=email, password="oldpass123"
        )
        UserProfile.objects.create(user=existing_user, sign_in_provider="password", email_verified=True)

        mock_verify.return_value = (
            _google_provider_data(uid="google-sub-link", email=email),
            None,
        )

        client = APIClient()
        resp = client.post(GOOGLE_SIGNIN_URL, {"id_token": "fake-token"}, format="json")

        assert resp.status_code == 200
        data = resp.json()
        # Same user should be returned
        assert str(existing_user.id) == data["user_id"]
        # SocialAccount must now be created
        assert SocialAccount.objects.filter(
            user=existing_user, provider="google", provider_uid="google-sub-link"
        ).exists()


# ===========================================================================
# TestSocialAuthGitHub
# ===========================================================================

@pytest.mark.django_db
class TestSocialAuthGitHub:

    @patch("social_auth.views.verify_github_access_token")
    def test_github_signin_new_user(self, mock_verify, api_client):
        """New user via GitHub returns 201."""
        mock_verify.return_value = (_github_provider_data(), None)

        resp = api_client.post(GITHUB_SIGNIN_URL, {"access_token": "gh-token-abc"}, format="json")

        assert resp.status_code == 201
        assert resp.json().get("is_new") is True

    @patch("social_auth.views.verify_github_access_token")
    def test_github_signin_returns_jwt(self, mock_verify, api_client):
        """GitHub sign-in response includes access, refresh, and user_id."""
        mock_verify.return_value = (_github_provider_data(uid="gh-99999"), None)

        resp = api_client.post(GITHUB_SIGNIN_URL, {"access_token": "gh-token-xyz"}, format="json")

        assert resp.status_code == 201
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert "user_id" in data

    @patch("social_auth.views.verify_github_access_token")
    def test_github_signin_invalid_token(self, mock_verify, api_client):
        """Invalid GitHub access token returns 400."""
        mock_verify.return_value = (None, "Invalid GitHub access token.")

        resp = api_client.post(GITHUB_SIGNIN_URL, {"access_token": "bad-gh-token"}, format="json")

        assert resp.status_code == 400
        assert "error" in resp.json()


# ===========================================================================
# TestSocialAuthApple
# ===========================================================================

@pytest.mark.django_db
class TestSocialAuthApple:

    @patch("social_auth.views.verify_apple_id_token")
    def test_apple_signin_new_user(self, mock_verify, api_client):
        """New user via Apple returns 201 with access + refresh tokens."""
        mock_verify.return_value = (_apple_provider_data(), None)

        resp = api_client.post(APPLE_SIGNIN_URL, {"id_token": "fake-apple-token"}, format="json")

        assert resp.status_code == 201
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert "user_id" in data
        assert data.get("is_new") is True

    @patch("social_auth.views.verify_apple_id_token")
    def test_apple_signin_existing_user(self, mock_verify, db):
        """Existing user (via pre-created SocialAccount) returns 200 with the same user id."""
        user = User.objects.create_user(
            username="apple_existing@ex.com",
            email="apple_existing@ex.com",
            password=None,
        )
        UserProfile.objects.create(user=user, sign_in_provider="apple", email_verified=True)
        SocialAccount.objects.create(
            user=user,
            provider="apple",
            provider_uid="apple-sub-existing",
            email="apple_existing@ex.com",
        )

        mock_verify.return_value = (
            _apple_provider_data(uid="apple-sub-existing", email="apple_existing@ex.com"),
            None,
        )

        client = APIClient()
        resp = client.post(APPLE_SIGNIN_URL, {"id_token": "fake-token"}, format="json")

        assert resp.status_code == 200
        data = resp.json()
        assert str(user.id) == data["user_id"]
        assert "access" in data
        assert "refresh" in data

    @patch("social_auth.views.verify_apple_id_token")
    def test_apple_signin_invalid_token(self, mock_verify, api_client):
        """Invalid/unverifiable Apple token returns 400 with an error message."""
        mock_verify.return_value = (None, "Invalid Apple ID token.")

        resp = api_client.post(APPLE_SIGNIN_URL, {"id_token": "bad-token"}, format="json")

        assert resp.status_code == 400
        assert "error" in resp.json()

    @patch("social_auth.views.verify_apple_id_token")
    def test_apple_signin_links_by_email(self, mock_verify, db):
        """
        When a user with the same email already exists (no SocialAccount),
        sign-in should link a new SocialAccount and return the existing user.
        """
        email = "apple_link_by_email@ex.com"
        existing_user = User.objects.create_user(
            username=email, email=email, password="oldpass123"
        )
        UserProfile.objects.create(user=existing_user, sign_in_provider="password", email_verified=True)

        mock_verify.return_value = (
            _apple_provider_data(uid="apple-sub-link", email=email),
            None,
        )

        client = APIClient()
        resp = client.post(APPLE_SIGNIN_URL, {"id_token": "fake-token"}, format="json")

        assert resp.status_code == 200
        data = resp.json()
        assert str(existing_user.id) == data["user_id"]
        assert SocialAccount.objects.filter(
            user=existing_user, provider="apple", provider_uid="apple-sub-link"
        ).exists()

    @patch("social_auth.views.verify_apple_id_token")
    def test_apple_signin_unverified_email_does_not_link(self, mock_verify, db):
        """
        An Apple token with email_verified=False must NOT link to an existing
        user by email -- prevents account takeover (same rule as Google/GitHub).
        """
        email = "apple_unverified@ex.com"
        existing_user = User.objects.create_user(
            username=email, email=email, password="oldpass123"
        )
        UserProfile.objects.create(user=existing_user, sign_in_provider="password", email_verified=True)

        mock_verify.return_value = (
            _apple_provider_data(uid="apple-sub-unverified", email=email, email_verified=False),
            None,
        )

        client = APIClient()
        resp = client.post(APPLE_SIGNIN_URL, {"id_token": "fake-token"}, format="json")

        assert resp.status_code == 201
        data = resp.json()
        assert str(existing_user.id) != data["user_id"]


# ===========================================================================
# TestLinkedAccounts
# ===========================================================================

@pytest.mark.django_db
class TestLinkedAccounts:

    def _make_user_with_accounts(self, n_accounts, has_password=True):
        """Helper: create a user with n SocialAccount rows."""
        user = User.objects.create_user(
            username=f"linked_user_{n_accounts}@ex.com",
            email=f"linked_user_{n_accounts}@ex.com",
            password="securepass123" if has_password else None,
        )
        UserProfile.objects.create(user=user, sign_in_provider="google", email_verified=True)
        for i in range(n_accounts):
            SocialAccount.objects.create(
                user=user,
                provider="google" if i == 0 else "github",
                provider_uid=f"uid-{n_accounts}-{i}",
                email=user.email,
            )
        return user

    def test_list_linked_accounts(self, api_client, db):
        """GET linked/ returns all social accounts for the authenticated user."""
        user = self._make_user_with_accounts(2)
        client = make_client(user)

        resp = client.get(LINKED_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_unlink_account(self, api_client, db):
        """DELETE linked/{pk}/ removes the social account and returns 204."""
        user = self._make_user_with_accounts(2, has_password=True)
        client = make_client(user)
        account = SocialAccount.objects.filter(user=user).first()

        resp = client.delete(f"{LINKED_URL}{account.pk}/")

        assert resp.status_code == 204
        assert not SocialAccount.objects.filter(pk=account.pk).exists()

    def test_cannot_unlink_last_account_without_password(self, db):
        """
        If the user has exactly 1 social account and no usable password,
        DELETE must return 400 to avoid locking the user out.
        """
        user = self._make_user_with_accounts(1, has_password=False)
        # Ensure user has no usable password
        assert not user.has_usable_password()

        client = make_client(user)
        account = SocialAccount.objects.filter(user=user).first()

        resp = client.delete(f"{LINKED_URL}{account.pk}/")

        assert resp.status_code == 400
        assert "Cannot unlink" in resp.json()["error"] or "password" in resp.json()["error"].lower()


# ===========================================================================
# TestAnonymousUpgrade
# ===========================================================================

@pytest.mark.django_db
class TestAnonymousUpgrade:

    def _make_anon_user(self):
        """Create a proper anonymous user as the server does."""
        import uuid
        anon_id = uuid.uuid4().hex[:12]
        user = User.objects.create_user(
            username=f"anon_{anon_id}",
            email=f"anon_{anon_id}@anonymous.local",
            password=None,
        )
        UserProfile.objects.create(user=user, sign_in_provider="anonymous", email_verified=False)
        return user

    def test_upgrade_anon_account(self, db):
        """Anonymous user can upgrade to a full email/password account."""
        anon = self._make_anon_user()
        client = make_client(anon)

        resp = client.post(
            UPGRADE_URL,
            {
                "email": "upgraded@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            format="json",
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert "upgraded" in data.get("detail", "").lower()

        # User should now have the new email
        anon.refresh_from_db()
        assert anon.email == "upgraded@example.com"

    def test_upgrade_non_anon_fails(self, db):
        """A regular (non-anonymous) user POSTing to upgrade gets 400."""
        user = User.objects.create_user(
            username="regularuser@ex.com",
            email="regularuser@ex.com",
            password="somepass123",
        )
        UserProfile.objects.create(user=user, sign_in_provider="password", email_verified=True)
        client = make_client(user)

        resp = client.post(
            UPGRADE_URL,
            {
                "email": "newmail@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            format="json",
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "credentials" in str(body).lower() or "already" in str(body).lower()

    def test_upgrade_duplicate_email(self, db):
        """
        If another user already owns the target email, upgrade returns 400.
        """
        # Another user who already owns the email
        User.objects.create_user(
            username="taken@example.com",
            email="taken@example.com",
            password="somepass123",
        )

        anon = self._make_anon_user()
        client = make_client(anon)

        resp = client.post(
            UPGRADE_URL,
            {
                "email": "taken@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            format="json",
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "email" in str(body).lower() or "use" in str(body).lower()


# ===========================================================================
# TestSetPassword
# ===========================================================================

@pytest.mark.django_db
class TestSetPassword:

    def _make_social_user(self):
        """Create a user with no usable password (OAuth-only)."""
        user = User.objects.create_user(
            username="social_only@ex.com",
            email="social_only@ex.com",
            password=None,
        )
        UserProfile.objects.create(user=user, sign_in_provider="google", email_verified=True)
        return user

    def _make_password_user(self, password="initialpass123"):
        """Create a user who already has a password."""
        user = User.objects.create_user(
            username="pw_user@ex.com",
            email="pw_user@ex.com",
            password=password,
        )
        UserProfile.objects.create(user=user, sign_in_provider="password", email_verified=True)
        return user

    def test_set_password_no_existing(self, db):
        """
        Social-only user (no usable password) can set a new password
        without providing current_password.
        """
        user = self._make_social_user()
        assert not user.has_usable_password()
        client = make_client(user)

        resp = client.post(
            SET_PASSWORD_URL,
            {
                "new_password": "NewStrongPass1!",
                "new_password2": "NewStrongPass1!",
            },
            format="json",
        )

        assert resp.status_code == 200
        assert "password" in resp.json().get("detail", "").lower() or "updated" in resp.json().get("detail", "").lower()

        # Verify the password is now usable
        user.refresh_from_db()
        assert user.has_usable_password()

    def test_set_password_with_existing_wrong(self, db):
        """
        User with an existing password who provides the wrong current_password
        gets 400.
        """
        user = self._make_password_user(password="initialpass123")
        client = make_client(user)

        resp = client.post(
            SET_PASSWORD_URL,
            {
                "current_password": "WRONGPASSWORD",
                "new_password": "NewStrongPass1!",
                "new_password2": "NewStrongPass1!",
            },
            format="json",
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "current_password" in body or "incorrect" in str(body).lower()

    def test_set_password_mismatch(self, db):
        """
        new_password != new_password2 returns 400 regardless of current_password.
        """
        user = self._make_social_user()
        client = make_client(user)

        resp = client.post(
            SET_PASSWORD_URL,
            {
                "new_password": "StrongPass1!",
                "new_password2": "DoesNotMatch99!",
            },
            format="json",
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "password" in str(body).lower() or "match" in str(body).lower()


# ===========================================================================
# TestABTesting
# ===========================================================================

@pytest.mark.django_db
class TestABTesting:

    # ---- helpers -----------------------------------------------------------

    def _create_experiment(self, project, name="Btn Color Test", status="draft"):
        return Experiment.objects.create(
            project=project,
            name=name,
            status=status,
            targeting_key="user_id",
        )

    def _add_variants(self, experiment, alloc_a=50, alloc_b=50):
        """Add two variants (control + variant_a) to an experiment."""
        v_control = ExperimentVariant.objects.create(
            experiment=experiment,
            name="control",
            allocation=alloc_a,
            config={"button_color": "blue"},
        )
        v_a = ExperimentVariant.objects.create(
            experiment=experiment,
            name="variant_a",
            allocation=alloc_b,
            config={"button_color": "green"},
        )
        return v_control, v_a

    # ---- tests -------------------------------------------------------------

    def test_create_experiment(self, editor_client, project):
        """Editor can create an experiment — returns 201."""
        url = ab_experiments_url(project.id)

        resp = editor_client.post(
            url,
            {"name": "Homepage CTA Test", "description": "Testing CTA variants", "targeting_key": "user_id"},
            format="json",
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Homepage CTA Test"
        assert data["status"] == "draft"
        assert "id" in data

    def test_viewer_cannot_create(self, viewer_client, project):
        """Viewer role gets 403 when trying to create an experiment."""
        url = ab_experiments_url(project.id)

        resp = viewer_client.post(
            url,
            {"name": "Unauthorized Experiment", "targeting_key": "user_id"},
            format="json",
        )

        assert resp.status_code == 403

    def test_start_experiment(self, editor_client, project):
        """Starting an experiment (via start/ action) sets status to running."""
        experiment = self._create_experiment(project, name="Start Test")
        self._add_variants(experiment, alloc_a=50, alloc_b=50)

        start_url = ab_start_url(project.id, experiment.id)
        resp = editor_client.post(start_url)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"

    def test_assign_variant_deterministic(self, editor_client, project):
        """
        The same targeting_value must always yield the same variant.
        Call assign twice independently and compare results.
        """
        experiment = self._create_experiment(project, name="Determinism Test", status="running")
        self._add_variants(experiment)

        assign_url = ab_assign_url(project.id, experiment.id)
        payload = {"targeting_value": "user-determinism-abc"}

        resp1 = editor_client.post(assign_url, payload, format="json")
        resp2 = editor_client.post(assign_url, payload, format="json")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["variant_name"] == resp2.json()["variant_name"]

    def test_assign_variant_sticky(self, editor_client, project):
        """
        Calling assign twice for the same targeting_value should return
        the same variant (sticky), and create only one ExperimentAssignment row.
        """
        experiment = self._create_experiment(project, name="Sticky Test", status="running")
        self._add_variants(experiment)

        assign_url = ab_assign_url(project.id, experiment.id)
        payload = {"targeting_value": "sticky-user-xyz"}

        resp1 = editor_client.post(assign_url, payload, format="json")
        resp2 = editor_client.post(assign_url, payload, format="json")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["variant_name"] == resp2.json()["variant_name"]

        # Only one assignment record should exist
        count = ExperimentAssignment.objects.filter(
            experiment=experiment, targeting_value="sticky-user-xyz"
        ).count()
        assert count == 1

    def test_assign_paused_experiment(self, editor_client, project):
        """
        Assigning a targeting_value to a paused (non-running) experiment
        returns a 409 with an explanatory detail message.
        """
        experiment = self._create_experiment(project, name="Paused Assign Test", status="paused")
        self._add_variants(experiment)

        assign_url = ab_assign_url(project.id, experiment.id)
        resp = editor_client.post(assign_url, {"targeting_value": "some-user"}, format="json")

        assert resp.status_code == 409
        body = resp.json()
        assert "not running" in body.get("detail", "").lower() or "paused" in str(body).lower()

    def test_record_conversion(self, editor_client, project):
        """
        Posting a conversion event for a known assignment returns 201 with event details.
        """
        experiment = self._create_experiment(project, name="Conversion Test", status="running")
        v_control, _ = self._add_variants(experiment)

        # Create an assignment directly via ORM
        assignment = ExperimentAssignment.objects.create(
            experiment=experiment,
            targeting_value="convert-user-1",
            variant=v_control,
        )

        convert_url = ab_convert_url(project.id, experiment.id)
        resp = editor_client.post(
            convert_url,
            {
                "targeting_value": "convert-user-1",
                "event_name": "purchase",
                "value": 49.99,
            },
            format="json",
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["event_name"] == "purchase"
        assert data["value"] == 49.99
        assert "id" in data

    def test_experiment_results(self, editor_client, project):
        """
        GET results/ returns per-variant assignment and conversion counts.
        """
        experiment = self._create_experiment(project, name="Results Test", status="running")
        v_control, v_a = self._add_variants(experiment)

        # Create assignments
        a1 = ExperimentAssignment.objects.create(
            experiment=experiment, targeting_value="res-user-1", variant=v_control
        )
        a2 = ExperimentAssignment.objects.create(
            experiment=experiment, targeting_value="res-user-2", variant=v_control
        )
        a3 = ExperimentAssignment.objects.create(
            experiment=experiment, targeting_value="res-user-3", variant=v_a
        )

        # One conversion on control
        ExperimentConversion.objects.create(assignment=a1, event_name="signup")

        results_url = ab_results_url(project.id, experiment.id)
        resp = editor_client.get(results_url)

        assert resp.status_code == 200
        data = resp.json()
        assert "variants" in data
        assert "experiment" in data

        # Build a name → row map
        rows = {r["variant_name"]: r for r in data["variants"]}
        assert rows["control"]["assignments"] == 2
        assert rows["control"]["conversions"] == 1
        assert rows["variant_a"]["assignments"] == 1
        assert rows["variant_a"]["conversions"] == 0

    def test_variant_allocation_invalid(self, editor_client, project):
        """
        Trying to start an experiment whose variants do not sum to 100
        returns 400.
        """
        experiment = self._create_experiment(project, name="Bad Allocation Test")
        # Add variants that only sum to 60
        self._add_variants(experiment, alloc_a=40, alloc_b=20)

        start_url = ab_start_url(project.id, experiment.id)
        resp = editor_client.post(start_url)

        assert resp.status_code == 400
        body = resp.json()
        # DRF ValidationError returns the error inside a list under various keys
        error_text = str(body).lower()
        assert "100" in error_text or "allocation" in error_text
