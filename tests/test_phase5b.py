"""
Phase 5B tests.

Covers:
  - AIProviderConfig CRUD
  - Chat Completion (mocked external calls)
  - Embedding (mocked external calls)
  - AI Usage Logs
  - VectorCollection CRUD
  - RAG Ingest (with and without embeddings)
  - RAG Search (mocked)
  - cosine_similarity utility
"""

import pytest
from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from ai.models import AIProviderConfig, AIUsageLog
from ai.encryption import encrypt_api_key
from rag.models import VectorCollection, VectorDocument
from rag.services import cosine_similarity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(user):
    """Return an authenticated APIClient for the given user."""
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Module-level fixtures (mirror test_phase5a.py pattern)
# ---------------------------------------------------------------------------

@pytest.fixture
def owner(db):
    u = User.objects.create_user("p5b_owner@ex.com", "p5b_owner@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def editor(db):
    u = User.objects.create_user("p5b_editor@ex.com", "p5b_editor@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def viewer(db):
    u = User.objects.create_user("p5b_viewer@ex.com", "p5b_viewer@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def project(db, owner, editor, viewer):
    p = Project.objects.create(
        name="Phase5B Project",
        slug="phase5b-proj",
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


@pytest.fixture
def rag_collection(db, project):
    return VectorCollection.objects.create(
        project=project,
        name="ingest-test-collection",
        embedding_model="text-embedding-3-small",
    )


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def providers_url(project_id):
    return f"/api/projects/{project_id}/ai/providers/"


def provider_detail_url(project_id, pk):
    return f"/api/projects/{project_id}/ai/providers/{pk}/"


def chat_url(project_id):
    return f"/api/projects/{project_id}/ai/chat/"


def embeddings_url(project_id):
    return f"/api/projects/{project_id}/ai/embeddings/"


def usage_url(project_id):
    return f"/api/projects/{project_id}/ai/usage/"


def collections_url(project_id):
    return f"/api/projects/{project_id}/rag/collections/"


def collection_url(project_id, pk):
    return f"/api/projects/{project_id}/rag/collections/{pk}/"


def ingest_url(project_id, collection_id):
    return f"/api/projects/{project_id}/rag/collections/{collection_id}/ingest/"


def search_url(project_id, collection_id):
    return f"/api/projects/{project_id}/rag/collections/{collection_id}/search/"


# ===========================================================================
# TestAIProviderConfig
# ===========================================================================

@pytest.mark.django_db
class TestAIProviderConfig:

    def test_create_provider(self, editor_client, project):
        """Editor can create an AI provider config — returns 201."""
        resp = editor_client.post(
            providers_url(project.id),
            {"provider": "anthropic", "api_key": "sk-test"},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "anthropic"
        assert "id" in data

    def test_viewer_cannot_create(self, viewer_client, project):
        """Viewer role gets 403 trying to create a provider config."""
        resp = viewer_client.post(
            providers_url(project.id),
            {"provider": "anthropic", "api_key": "sk-test"},
            format="json",
        )
        assert resp.status_code == 403

    def test_api_key_not_in_response(self, editor_client, project):
        """api_key and api_key_encrypted must not appear in GET provider list response."""
        AIProviderConfig.objects.create(
            project=project,
            provider="anthropic",
            api_key_encrypted=encrypt_api_key("sk-secret"),
        )
        resp = editor_client.get(providers_url(project.id))
        assert resp.status_code == 200
        # Response is paginated: {"next": …, "previous": …, "results": […]}
        body = resp.json()
        items = body["results"]
        assert len(items) >= 1
        for item in items:
            assert "api_key_encrypted" not in item
            # api_key is write_only — must not appear in read responses
            assert "api_key" not in item

    def test_create_duplicate_provider(self, editor_client, project):
        """Creating the same provider twice returns 400 (unique constraint)."""
        payload = {"provider": "anthropic", "api_key": "sk-test"}
        r1 = editor_client.post(providers_url(project.id), payload, format="json")
        assert r1.status_code == 201
        r2 = editor_client.post(providers_url(project.id), payload, format="json")
        assert r2.status_code == 400


# ===========================================================================
# TestChatCompletion
# ===========================================================================

_MOCK_ANTHROPIC_RESULT = {
    "content": "Hello",
    "model": "claude-haiku-4-5-20251001",
    "provider": "anthropic",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    },
    "latency_ms": 100,
}


@pytest.mark.django_db
class TestChatCompletion:

    def test_chat_no_provider(self, editor_client, project):
        """POST /ai/chat/ when no AIProviderConfig exists → 400 with 'No active'."""
        resp = editor_client.post(
            chat_url(project.id),
            {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "No active" in resp.json().get("error", "")

    @patch("ai.views.call_anthropic")
    def test_chat_mocked(self, mock_call, editor_client, project):
        """Mocked Anthropic call returns 200 with content field."""
        mock_call.return_value = _MOCK_ANTHROPIC_RESULT
        AIProviderConfig.objects.create(
            project=project,
            provider="anthropic",
            api_key_encrypted=encrypt_api_key("sk-test"),
        )
        resp = editor_client.post(
            chat_url(project.id),
            {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "Hello"
        assert "usage" in data

    @patch("ai.views.call_anthropic")
    def test_chat_logs_usage(self, mock_call, editor_client, project):
        """After a mocked chat call, one AIUsageLog record is created."""
        mock_call.return_value = _MOCK_ANTHROPIC_RESULT
        AIProviderConfig.objects.create(
            project=project,
            provider="anthropic",
            api_key_encrypted=encrypt_api_key("sk-test"),
        )
        editor_client.post(
            chat_url(project.id),
            {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            format="json",
        )
        assert AIUsageLog.objects.count() == 1

    def test_chat_unauthenticated(self, api_client, project):
        """No auth header → 401."""
        resp = api_client.post(
            chat_url(project.id),
            {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            format="json",
        )
        assert resp.status_code == 401


# ===========================================================================
# TestEmbedding
# ===========================================================================

@pytest.mark.django_db
class TestEmbedding:

    def test_embed_no_provider(self, editor_client, project):
        """POST /ai/embeddings/ with no OpenAI config → 400."""
        resp = editor_client.post(
            embeddings_url(project.id),
            {"input": ["Hello world"], "model": "text-embedding-3-small"},
            format="json",
        )
        assert resp.status_code == 400

    @patch("ai.views.get_embeddings_openai")
    def test_embed_mocked(self, mock_embed, editor_client, project):
        """Mocked OpenAI embedding call returns 200 with embeddings list."""
        mock_embed.return_value = {
            "embeddings": [[0.1, 0.2, 0.3]],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
            "latency_ms": 50,
        }
        AIProviderConfig.objects.create(
            project=project,
            provider="openai",
            api_key_encrypted=encrypt_api_key("sk-openai-test"),
        )
        resp = editor_client.post(
            embeddings_url(project.id),
            {"input": ["Hello world"], "model": "text-embedding-3-small"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "embeddings" in data
        assert isinstance(data["embeddings"], list)


# ===========================================================================
# TestAIUsage
# ===========================================================================

@pytest.mark.django_db
class TestAIUsage:

    def test_usage_returns_logs(self, editor_client, project, owner):
        """GET /ai/usage/ returns the list of AIUsageLog entries for the project."""
        AIUsageLog.objects.create(
            project=project,
            user=owner,
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=100,
            status="success",
        )
        AIUsageLog.objects.create(
            project=project,
            user=owner,
            provider="openai",
            model="text-embedding-3-small",
            prompt_tokens=3,
            total_tokens=3,
            latency_ms=30,
            status="success",
        )
        resp = editor_client.get(usage_url(project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


# ===========================================================================
# TestVectorCollection
# ===========================================================================

@pytest.mark.django_db
class TestVectorCollection:

    def test_create_collection(self, editor_client, project):
        """Editor POST /rag/collections/ with name + embedding_model → 201."""
        resp = editor_client.post(
            collections_url(project.id),
            {"name": "test", "embedding_model": "text-embedding-3-small"},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test"
        assert "id" in data

    def test_viewer_cannot_create(self, viewer_client, project):
        """Viewer role gets 403 trying to create a collection."""
        resp = viewer_client.post(
            collections_url(project.id),
            {"name": "should-fail", "embedding_model": "text-embedding-3-small"},
            format="json",
        )
        assert resp.status_code == 403

    def test_list_collections(self, editor_client, project):
        """Create 2 collections via ORM, GET /rag/collections/ → 2 results."""
        VectorCollection.objects.create(project=project, name="col-a")
        VectorCollection.objects.create(project=project, name="col-b")
        resp = editor_client.get(collections_url(project.id))
        assert resp.status_code == 200
        # Response is paginated: {"next": …, "previous": …, "results": […]}
        body = resp.json()
        assert len(body["results"]) == 2


# ===========================================================================
# TestRAGIngest
# ===========================================================================

@pytest.mark.django_db
class TestRAGIngest:

    def test_ingest_no_openai(self, editor_client, project, rag_collection):
        """POST ingest with embed=true but no OpenAI provider → 400."""
        resp = editor_client.post(
            ingest_url(project.id, rag_collection.id),
            {"documents": [{"content": "hello"}], "embed": True},
            format="json",
        )
        assert resp.status_code == 400

    def test_ingest_no_embed(self, editor_client, project, rag_collection):
        """POST ingest with embed=false creates doc without embedding → 201."""
        resp = editor_client.post(
            ingest_url(project.id, rag_collection.id),
            {"documents": [{"content": "hello world"}], "embed": False},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["created"] == 1
        doc = VectorDocument.objects.get(collection=rag_collection)
        assert doc.content == "hello world"
        assert doc.embedding is None

    @patch("rag.views.embed_texts")
    def test_ingest_mocked_embed(self, mock_embed, editor_client, project, rag_collection):
        """Mocked embed_texts: ingest 1 doc → 201, VectorDocument.embedding is set."""
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        AIProviderConfig.objects.create(
            project=project,
            provider="openai",
            api_key_encrypted=encrypt_api_key("sk-openai-test"),
        )
        resp = editor_client.post(
            ingest_url(project.id, rag_collection.id),
            {"documents": [{"content": "embedding test doc"}], "embed": True},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["created"] == 1
        doc = VectorDocument.objects.get(collection=rag_collection)
        assert doc.embedding == [0.1, 0.2, 0.3]


# ===========================================================================
# TestRAGSearch
# ===========================================================================

@pytest.mark.django_db
class TestRAGSearch:

    @patch("rag.views.embed_texts")
    def test_search_returns_results(self, mock_embed, editor_client, project):
        """Create collection + doc with embedding, mock embed_texts for query → results list."""
        mock_embed.return_value = [[1.0, 0.0, 0.0]]

        AIProviderConfig.objects.create(
            project=project,
            provider="openai",
            api_key_encrypted=encrypt_api_key("sk-openai-test"),
        )
        collection = VectorCollection.objects.create(
            project=project,
            name="search-test-col",
            embedding_model="text-embedding-3-small",
        )
        VectorDocument.objects.create(
            collection=collection,
            content="test document content",
            embedding=[1.0, 0.0, 0.0],
        )

        resp = editor_client.post(
            search_url(project.id, collection.id),
            {"query": "test"},
            format="json",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) >= 1

    def test_cosine_similarity(self):
        """cosine_similarity([1,0],[1,0]) == 1.0 and ([1,0],[0,1]) == 0.0."""
        assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
