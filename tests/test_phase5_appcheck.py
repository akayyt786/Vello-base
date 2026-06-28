"""
Phase 5: App Check tests.

Covers AppCheckConfig, DebugToken, AppCheckToken (exchange / verify / revoke),
and AppCheckMiddleware.

Fixtures from conftest: api_client, authenticated_client, test_user, test_project.
"""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from app_check.models import AppCheckConfig, AppCheckToken, DebugToken
from app_check.middleware import AppCheckMiddleware
from app_check.services import hash_token


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def config_list_url(project_id):
    return f'/api/projects/{project_id}/app-check/config/'


def config_detail_url(project_id, pk):
    return f'/api/projects/{project_id}/app-check/config/{pk}/'


def exchange_url(project_id):
    return f'/api/projects/{project_id}/app-check/exchange/'


def verify_url(project_id):
    return f'/api/projects/{project_id}/app-check/verify/'


def tokens_url(project_id):
    return f'/api/projects/{project_id}/app-check/tokens/'


def revoke_url(project_id, pk):
    return f'/api/projects/{project_id}/app-check/tokens/{pk}/revoke/'


def debug_tokens_url(project_id):
    return f'/api/projects/{project_id}/app-check/debug-tokens/'


def debug_token_detail_url(project_id, pk):
    return f'/api/projects/{project_id}/app-check/debug-tokens/{pk}/'


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def viewer_user(db):
    """A user with no elevated project role."""
    user = User.objects.create_user(
        'acviewer@example.com',
        'acviewer@example.com',
        'pass123',
    )
    UserProfile.objects.create(user=user, sign_in_provider='password', email_verified=True)
    return user


@pytest.fixture
def viewer_client(viewer_user, test_project):
    """Authenticated API client whose membership role is 'viewer' on test_project."""
    ProjectMembership.objects.create(project=test_project, user=viewer_user, role='viewer')
    refresh = RefreshToken.for_user(viewer_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


# ---------------------------------------------------------------------------
# TestAppCheckConfig
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAppCheckConfig:
    def test_list_configs_empty(self, authenticated_client, test_project):
        resp = authenticated_client.get(config_list_url(test_project.id))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_config_editor(self, authenticated_client, test_project):
        resp = authenticated_client.post(
            config_list_url(test_project.id),
            {'platform': 'web', 'provider': 'recaptcha_v3', 'config': {'site_key': 'abc123'}},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['platform'] == 'web'
        assert data['provider'] == 'recaptcha_v3'
        assert data['config'] == {'site_key': 'abc123'}
        assert data['is_enabled'] is True
        assert 'id' in data

    def test_create_config_viewer(self, viewer_client, test_project):
        resp = viewer_client.post(
            config_list_url(test_project.id),
            {'platform': 'web', 'provider': 'recaptcha_v3'},
            format='json',
        )
        assert resp.status_code == 403

    def test_create_duplicate_platform(self, authenticated_client, test_project):
        # First creation succeeds
        r1 = authenticated_client.post(
            config_list_url(test_project.id),
            {'platform': 'android', 'provider': 'play_integrity'},
            format='json',
        )
        assert r1.status_code == 201

        # Same project + platform must be rejected
        r2 = authenticated_client.post(
            config_list_url(test_project.id),
            {'platform': 'android', 'provider': 'debug'},
            format='json',
        )
        assert r2.status_code == 400

    def test_update_config_editor(self, authenticated_client, test_project):
        create_resp = authenticated_client.post(
            config_list_url(test_project.id),
            {'platform': 'ios', 'provider': 'device_check', 'config': {}},
            format='json',
        )
        assert create_resp.status_code == 201
        config_id = create_resp.json()['id']

        patch_resp = authenticated_client.patch(
            config_detail_url(test_project.id, config_id),
            {'provider': 'debug', 'config': {'note': 'switched to debug'}},
            format='json',
        )
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data['provider'] == 'debug'
        assert data['config'] == {'note': 'switched to debug'}

    def test_delete_config_editor(self, authenticated_client, test_project):
        create_resp = authenticated_client.post(
            config_list_url(test_project.id),
            {'platform': 'web', 'provider': 'debug'},
            format='json',
        )
        assert create_resp.status_code == 201
        config_id = create_resp.json()['id']

        del_resp = authenticated_client.delete(config_detail_url(test_project.id, config_id))
        assert del_resp.status_code == 204
        assert not AppCheckConfig.objects.filter(id=config_id).exists()

    def test_list_configs_member(self, viewer_client, test_project):
        AppCheckConfig.objects.create(
            project=test_project,
            platform='web',
            provider='recaptcha_v3',
        )
        resp = viewer_client.get(config_list_url(test_project.id))
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]['platform'] == 'web'


# ---------------------------------------------------------------------------
# TestDebugTokens
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDebugTokens:
    def test_create_debug_token_editor(self, authenticated_client, test_project):
        resp = authenticated_client.post(
            debug_tokens_url(test_project.id),
            {'name': 'CI Token'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == 'CI Token'
        # token field must be a valid UUID
        uuid.UUID(str(data['token']))

    def test_create_debug_token_viewer(self, viewer_client, test_project):
        resp = viewer_client.post(
            debug_tokens_url(test_project.id),
            {'name': 'Unauthorized'},
            format='json',
        )
        assert resp.status_code == 403

    def test_list_debug_tokens_editor(self, authenticated_client, test_project):
        DebugToken.objects.create(project=test_project, name='Token A')
        DebugToken.objects.create(project=test_project, name='Token B')
        resp = authenticated_client.get(debug_tokens_url(test_project.id))
        assert resp.status_code == 200
        names = [t['name'] for t in resp.json()]
        assert 'Token A' in names
        assert 'Token B' in names

    def test_delete_debug_token(self, authenticated_client, test_project):
        token = DebugToken.objects.create(project=test_project, name='Temp Token')
        resp = authenticated_client.delete(debug_token_detail_url(test_project.id, token.id))
        assert resp.status_code == 204
        assert not DebugToken.objects.filter(id=token.id).exists()

    def test_debug_token_is_unique(self, authenticated_client, test_project):
        r1 = authenticated_client.post(
            debug_tokens_url(test_project.id),
            {'name': 'Token X'},
            format='json',
        )
        r2 = authenticated_client.post(
            debug_tokens_url(test_project.id),
            {'name': 'Token Y'},
            format='json',
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()['token'] != r2.json()['token']

    def test_debug_token_name_default(self, authenticated_client, test_project):
        resp = authenticated_client.post(
            debug_tokens_url(test_project.id),
            {},
            format='json',
        )
        assert resp.status_code == 201
        assert resp.json()['name'] == 'Debug Token'


# ---------------------------------------------------------------------------
# TestTokenExchange
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTokenExchange:
    def test_exchange_debug_token_success(self, authenticated_client, test_project):
        debug_token = DebugToken.objects.create(project=test_project, name='CI')
        resp = authenticated_client.post(
            exchange_url(test_project.id),
            {
                'raw_token': str(debug_token.token),
                'platform': 'web',
                'provider': 'debug',
            },
            format='json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'token' in data
        assert 'expires_at' in data
        # token is a SHA-256 hex digest
        assert len(data['token']) == 64

    def test_exchange_invalid_debug_token(self, authenticated_client, test_project):
        resp = authenticated_client.post(
            exchange_url(test_project.id),
            {
                'raw_token': str(uuid.uuid4()),
                'platform': 'web',
                'provider': 'debug',
            },
            format='json',
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_exchange_debug_token_wrong_project(
        self, authenticated_client, test_project, test_user
    ):
        """A debug token belonging to another project must be rejected."""
        other_project = Project.objects.create(
            name='Other Project',
            slug='other-project-ac',
            owner=test_user,
            is_active=True,
        )
        ProjectMembership.objects.create(project=other_project, user=test_user, role='owner')
        other_token = DebugToken.objects.create(project=other_project, name='Other CI')

        resp = authenticated_client.post(
            exchange_url(test_project.id),
            {
                'raw_token': str(other_token.token),
                'platform': 'web',
                'provider': 'debug',
            },
            format='json',
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_exchange_production_provider_not_configured(
        self, authenticated_client, test_project
    ):
        """Requesting recaptcha_v3 with no AppCheckConfig must return 400."""
        resp = authenticated_client.post(
            exchange_url(test_project.id),
            {
                'raw_token': 'some-recaptcha-token',
                'platform': 'web',
                'provider': 'recaptcha_v3',
            },
            format='json',
        )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_exchange_production_provider_configured(
        self, authenticated_client, test_project
    ):
        """recaptcha_v3 with a matching AppCheckConfig → 501 (placeholder)."""
        AppCheckConfig.objects.create(
            project=test_project,
            platform='web',
            provider='recaptcha_v3',
            config={'site_key': 'my-site-key'},
            is_enabled=True,
        )
        resp = authenticated_client.post(
            exchange_url(test_project.id),
            {
                'raw_token': 'some-recaptcha-token',
                'platform': 'web',
                'provider': 'recaptcha_v3',
            },
            format='json',
        )
        assert resp.status_code == 501
        assert 'error' in resp.json()

    def test_exchange_requires_auth(self, api_client, test_project):
        resp = api_client.post(
            exchange_url(test_project.id),
            {
                'raw_token': str(uuid.uuid4()),
                'platform': 'web',
                'provider': 'debug',
            },
            format='json',
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestTokenVerify
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTokenVerify:
    def _store_token(self, project, **overrides):
        """Create an AppCheckToken in the DB and return (db_obj, raw_token_str)."""
        raw = str(uuid.uuid4())
        token_hash = hash_token(raw)
        defaults = dict(
            project=project,
            token_hash=token_hash,
            platform='web',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        defaults.update(overrides)
        obj = AppCheckToken.objects.create(**defaults)
        return obj, raw

    def test_verify_valid_token(self, authenticated_client, test_project):
        _, raw = self._store_token(test_project)
        resp = authenticated_client.post(
            verify_url(test_project.id),
            {'token': raw},
            format='json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['valid'] is True
        assert data['error'] is None

    def test_verify_expired_token(self, authenticated_client, test_project):
        raw = str(uuid.uuid4())
        AppCheckToken.objects.create(
            project=test_project,
            token_hash=hash_token(raw),
            platform='web',
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = authenticated_client.post(
            verify_url(test_project.id),
            {'token': raw},
            format='json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['valid'] is False

    def test_verify_revoked_token(self, authenticated_client, test_project):
        _, raw = self._store_token(test_project, is_revoked=True)
        resp = authenticated_client.post(
            verify_url(test_project.id),
            {'token': raw},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.json()['valid'] is False

    def test_verify_nonexistent_token(self, authenticated_client, test_project):
        resp = authenticated_client.post(
            verify_url(test_project.id),
            {'token': str(uuid.uuid4())},
            format='json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['valid'] is False

    def test_verify_missing_token_field(self, authenticated_client, test_project):
        resp = authenticated_client.post(
            verify_url(test_project.id),
            {},
            format='json',
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TestTokenRevoke
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTokenRevoke:
    def _create_app_check_token(self, project):
        raw = str(uuid.uuid4())
        obj = AppCheckToken.objects.create(
            project=project,
            token_hash=hash_token(raw),
            platform='web',
            expires_at=timezone.now() + timedelta(hours=1),
        )
        return obj, raw

    def test_revoke_token_editor(self, authenticated_client, test_project):
        token_obj, _ = self._create_app_check_token(test_project)
        resp = authenticated_client.post(revoke_url(test_project.id, token_obj.id))
        assert resp.status_code == 200
        token_obj.refresh_from_db()
        assert token_obj.is_revoked is True

    def test_revoke_token_viewer(self, viewer_client, test_project):
        token_obj, _ = self._create_app_check_token(test_project)
        resp = viewer_client.post(revoke_url(test_project.id, token_obj.id))
        assert resp.status_code == 403

    def test_list_tokens_editor(self, authenticated_client, test_project):
        self._create_app_check_token(test_project)
        self._create_app_check_token(test_project)
        resp = authenticated_client.get(tokens_url(test_project.id))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_revoked_token_fails_verify(self, authenticated_client, test_project):
        token_obj, raw = self._create_app_check_token(test_project)
        # Revoke via API
        revoke_resp = authenticated_client.post(revoke_url(test_project.id, token_obj.id))
        assert revoke_resp.status_code == 200

        # Verify must now report invalid
        verify_resp = authenticated_client.post(
            verify_url(test_project.id),
            {'token': raw},
            format='json',
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()['valid'] is False


# ---------------------------------------------------------------------------
# TestAppCheckMiddleware
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAppCheckMiddleware:
    """
    Exercises AppCheckMiddleware.process_view() directly via RequestFactory
    to avoid the overhead of a full HTTP round-trip and to keep assertions
    focused on the middleware's side-effect (setting request.app_check_verified).
    """

    def _middleware(self):
        return AppCheckMiddleware(lambda request: None)

    def test_middleware_no_header(self, test_project):
        factory = RequestFactory()
        request = factory.get(f'/api/projects/{test_project.id}/app-check/verify/')

        mw = self._middleware()
        result = mw.process_view(
            request,
            lambda req: None,
            [],
            {'project_id': test_project.id},
        )

        assert result is None
        assert request.app_check_verified is False

    def test_middleware_valid_token(self, test_project):
        raw = str(uuid.uuid4())
        AppCheckToken.objects.create(
            project=test_project,
            token_hash=hash_token(raw),
            platform='web',
            expires_at=timezone.now() + timedelta(hours=1),
        )

        factory = RequestFactory()
        request = factory.get(
            f'/api/projects/{test_project.id}/app-check/verify/',
            HTTP_X_APP_CHECK_TOKEN=raw,
        )

        mw = self._middleware()
        result = mw.process_view(
            request,
            lambda req: None,
            [],
            {'project_id': test_project.id},
        )

        assert result is None
        assert request.app_check_verified is True

    def test_middleware_invalid_token(self, test_project):
        factory = RequestFactory()
        request = factory.get(
            f'/api/projects/{test_project.id}/app-check/verify/',
            HTTP_X_APP_CHECK_TOKEN='completely-invalid-token-xyz',
        )

        mw = self._middleware()
        result = mw.process_view(
            request,
            lambda req: None,
            [],
            {'project_id': test_project.id},
        )

        assert result is None
        assert request.app_check_verified is False
