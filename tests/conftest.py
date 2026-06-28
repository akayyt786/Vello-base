"""
Pytest configuration and fixtures.
"""

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import Project, ProjectMembership, UserProfile
from data.models import Collection, Document

# Override CHANNEL_LAYERS and CACHES for the entire test session to avoid
# needing a real Redis server during tests.
TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

def pytest_configure(config):
    """Apply in-memory backends before Django settings are locked in."""
    from django.conf import settings
    if not settings.configured:
        return
    settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
    settings.CACHES = TEST_CACHES


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        username='testuser@example.com',
        email='testuser@example.com',
        password='testpass123'
    )
    UserProfile.objects.create(
        user=user,
        sign_in_provider='password',
        email_verified=True
    )
    return user


@pytest.fixture
def test_user2(db):
    """Create a second test user for permission testing."""
    user = User.objects.create_user(
        username='testuser2@example.com',
        email='testuser2@example.com',
        password='testpass123'
    )
    UserProfile.objects.create(
        user=user,
        sign_in_provider='password',
        email_verified=False
    )
    return user


@pytest.fixture
def test_project(db, test_user):
    """Create a test project."""
    project = Project.objects.create(
        name='Test Project',
        slug='test-project',
        owner=test_user,
        description='Test project for unit tests',
        is_active=True
    )
    ProjectMembership.objects.create(
        project=project,
        user=test_user,
        role='owner'
    )
    return project


@pytest.fixture
def test_project_2(db, test_user2):
    """Create a second test project."""
    project = Project.objects.create(
        name='Test Project 2',
        slug='test-project-2',
        owner=test_user2,
        description='Second test project',
        is_active=True
    )
    ProjectMembership.objects.create(
        project=project,
        user=test_user2,
        role='owner'
    )
    return project


@pytest.fixture
def test_collection(db, test_project):
    """Create a test collection."""
    collection = Collection.objects.create(
        project=test_project,
        name='users',
        path='users',
        schema={
            'fields': {
                'name': {'type': 'string', 'indexed': True},
                'email': {'type': 'string', 'indexed': True},
                'age': {'type': 'number'},
                'status': {'type': 'string'}
            }
        }
    )
    return collection


@pytest.fixture
def test_document(db, test_project, test_collection):
    """Create a test document."""
    doc = Document.objects.create(
        project=test_project,
        collection_path='users',
        doc_id='alice',
        data={
            'name': 'Alice',
            'email': 'alice@example.com',
            'age': 30,
            'status': 'active'
        }
    )
    return doc


@pytest.fixture
def admin_user(db):
    """Create an admin/staff user for testing."""
    user = User.objects.create_user(
        username='admin@example.com',
        email='admin@example.com',
        password='adminpass123',
        is_staff=True,
        is_superuser=True
    )
    UserProfile.objects.create(
        user=user,
        sign_in_provider='password',
        email_verified=True,
        custom_claims={'admin': True, 'is_admin': True}
    )
    return user


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Return an API client authenticated as test_user."""
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def authenticated_client_2(api_client, test_user2):
    """Return an API client authenticated as test_user2."""
    refresh = RefreshToken.for_user(test_user2)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an API client authenticated as admin_user."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client
