"""
Phase 6 tests.

Covers:
  - RemoteConfigParameter CRUD + fetch
  - WebhookEndpoint CRUD + deliveries
  - Analytics track/batch/summary/events
  - Billing subscription/usage/tiers + service helpers
  - Realtime broadcast (no-channel-layer guard)
  - Webhook payload signing + verification
"""

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request

import pytest

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from remoteconfig.models import RemoteConfigParameter
from webhooks.models import WebhookEndpoint, WebhookDelivery
from analytics.models import AnalyticsEvent
from billing.models import ProjectSubscription, QuotaUsage


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
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner(db):
    u = User.objects.create_user("p6_owner@ex.com", "p6_owner@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def editor(db):
    u = User.objects.create_user("p6_editor@ex.com", "p6_editor@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def viewer(db):
    u = User.objects.create_user("p6_viewer@ex.com", "p6_viewer@ex.com", "pass123")
    UserProfile.objects.create(user=u, sign_in_provider="password", email_verified=True)
    return u


@pytest.fixture
def project(db, owner, editor, viewer):
    p = Project.objects.create(
        name="Phase6 Project",
        slug="phase6-proj",
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
# URL helpers
# ---------------------------------------------------------------------------

def config_params_url(project_id):
    return f"/api/projects/{project_id}/remoteconfig/params/"


def config_fetch_url(project_id):
    return f"/api/projects/{project_id}/remoteconfig/fetch/"


def webhook_endpoints_url(project_id):
    return f"/api/projects/{project_id}/webhooks/endpoints/"


def webhook_endpoint_url(project_id, pk):
    return f"/api/projects/{project_id}/webhooks/endpoints/{pk}/"


def webhook_deliveries_url(project_id, endpoint_id):
    return f"/api/projects/{project_id}/webhooks/endpoints/{endpoint_id}/deliveries/"


def analytics_track_url(project_id):
    return f"/api/projects/{project_id}/analytics/track/"


def analytics_batch_url(project_id):
    return f"/api/projects/{project_id}/analytics/batch/"


def analytics_summary_url(project_id):
    return f"/api/projects/{project_id}/analytics/sdk-summary/"


def analytics_events_url(project_id):
    return f"/api/projects/{project_id}/analytics/sdk-events/"


def billing_subscription_url(project_id):
    return f"/api/projects/{project_id}/billing/subscription/"


def billing_usage_url(project_id):
    return f"/api/projects/{project_id}/billing/usage/"


def billing_tiers_url():
    return "/api/billing/tiers/"


def billing_checkout_url(project_id):
    return f"/api/projects/{project_id}/billing/checkout/"


def billing_portal_url(project_id):
    return f"/api/projects/{project_id}/billing/portal/"


# ===========================================================================
# TestRemoteConfig
# ===========================================================================

@pytest.mark.django_db
class TestRemoteConfig:

    def test_create_param(self, editor_client, project):
        """Editor POST config param → 201."""
        resp = editor_client.post(
            config_params_url(project.id),
            {"key": "theme", "value": "dark", "param_type": "string"},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["key"] == "theme"
        assert data["value"] == "dark"

    def test_viewer_cannot_create(self, viewer_client, project):
        """Viewer role → 403."""
        resp = viewer_client.post(
            config_params_url(project.id),
            {"key": "theme", "value": "dark", "param_type": "string"},
            format="json",
        )
        assert resp.status_code == 403

    def test_list_params(self, editor_client, project):
        """Create 3 params, GET list → 3 results."""
        for i in range(3):
            RemoteConfigParameter.objects.create(
                project=project,
                key=f"param_{i}",
                value=str(i),
                param_type="string",
            )
        resp = editor_client.get(config_params_url(project.id))
        assert resp.status_code == 200
        body = resp.json()
        # Could be paginated or plain list
        results = body.get("results", body) if isinstance(body, dict) else body
        assert len(results) == 3

    def test_fetch_returns_typed_values(self, editor_client, project):
        """GET fetch/ returns number and boolean as native types."""
        RemoteConfigParameter.objects.create(
            project=project, key="maxRetries", value="5", param_type="number", is_active=True
        )
        RemoteConfigParameter.objects.create(
            project=project, key="debug", value="true", param_type="boolean", is_active=True
        )
        resp = editor_client.get(config_fetch_url(project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["maxRetries"] == 5
        assert data["debug"] is True

    def test_fetch_returns_only_active(self, editor_client, project):
        """GET fetch/ only includes active params."""
        RemoteConfigParameter.objects.create(
            project=project, key="active_key", value="yes", param_type="string", is_active=True
        )
        RemoteConfigParameter.objects.create(
            project=project, key="inactive_key", value="no", param_type="string", is_active=False
        )
        resp = editor_client.get(config_fetch_url(project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "active_key" in data
        assert "inactive_key" not in data

    def test_unique_key_per_project(self, editor_client, project):
        """Creating same key twice → 400."""
        RemoteConfigParameter.objects.create(
            project=project, key="dup_key", value="v1", param_type="string"
        )
        resp = editor_client.post(
            config_params_url(project.id),
            {"key": "dup_key", "value": "v2", "param_type": "string"},
            format="json",
        )
        assert resp.status_code == 400


# ===========================================================================
# TestWebhooks
# ===========================================================================

@pytest.mark.django_db
class TestWebhooks:

    def test_create_endpoint(self, editor_client, project):
        """Editor POST webhook endpoint → 201 with secret field."""
        resp = editor_client.post(
            webhook_endpoints_url(project.id),
            {"url": "https://example.com/hook", "events": ["data.created"]},
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "secret" in data
        assert "id" in data

    def test_secret_auto_generated(self, editor_client, project):
        """Secret is non-empty on creation."""
        resp = editor_client.post(
            webhook_endpoints_url(project.id),
            {"url": "https://example.com/hook2", "events": ["data.updated"]},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["secret"] != ""

    def test_viewer_cannot_create(self, viewer_client, project):
        """Viewer role → 403."""
        resp = viewer_client.post(
            webhook_endpoints_url(project.id),
            {"url": "https://example.com/hook", "events": ["data.created"]},
            format="json",
        )
        assert resp.status_code == 403

    def test_invalid_event(self, editor_client, project):
        """POST with unknown event type → 400."""
        resp = editor_client.post(
            webhook_endpoints_url(project.id),
            {"url": "https://example.com/hook", "events": ["invalid.event"]},
            format="json",
        )
        assert resp.status_code == 400

    def test_list_endpoints(self, editor_client, project):
        """Create 2 endpoints via ORM, GET list → 2 results."""
        WebhookEndpoint.objects.create(
            project=project,
            url="https://example.com/hook-a",
            secret="secret-a",
            events=["data.created"],
        )
        WebhookEndpoint.objects.create(
            project=project,
            url="https://example.com/hook-b",
            secret="secret-b",
            events=["data.deleted"],
        )
        resp = editor_client.get(webhook_endpoints_url(project.id))
        assert resp.status_code == 200
        body = resp.json()
        results = body.get("results", body) if isinstance(body, dict) else body
        assert len(results) == 2

    def test_delivery_list(self, editor_client, project):
        """Create endpoint + delivery, GET deliveries/ → list."""
        endpoint = WebhookEndpoint.objects.create(
            project=project,
            url="https://example.com/hook-del",
            secret="secret-del",
            events=["auth.login"],
        )
        WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type="auth.login",
            payload={"user": "alice"},
            status="success",
        )
        resp = editor_client.get(webhook_deliveries_url(project.id, endpoint.id))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1


# ===========================================================================
# TestAnalytics
# ===========================================================================

@pytest.mark.django_db
class TestAnalytics:

    def test_track_event(self, editor_client, project):
        """POST track/ → 201 with id."""
        resp = editor_client.post(
            analytics_track_url(project.id),
            {
                "event_name": "page_view",
                "properties": {"url": "/home"},
                "timestamp": "2025-01-01T00:00:00Z",
            },
            format="json",
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

    def test_batch_track(self, editor_client, project):
        """POST batch/ with 2 events → 201, created==2."""
        events = [
            {"event_name": "click", "properties": {}, "timestamp": "2025-01-01T00:00:00Z"},
            {"event_name": "view",  "properties": {}, "timestamp": "2025-01-01T00:01:00Z"},
        ]
        resp = editor_client.post(
            analytics_batch_url(project.id),
            {"events": events},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.json()["created"] == 2

    def test_batch_max_500(self, editor_client, project):
        """POST 501 events → 400 (exceeds batch limit)."""
        events = [
            {"event_name": "e", "properties": {}, "timestamp": "2025-01-01T00:00:00Z"}
            for _ in range(501)
        ]
        resp = editor_client.post(
            analytics_batch_url(project.id),
            {"events": events},
            format="json",
        )
        assert resp.status_code == 400

    def test_summary_returns_counts(self, editor_client, project, editor):
        """Track 5 click + 3 view events, summary → total_events==8, both in by_event."""
        now = timezone.now()
        for _ in range(5):
            AnalyticsEvent.objects.create(
                project=project,
                user=editor,
                event_name="click",
                properties={},
                timestamp=now,
            )
        for _ in range(3):
            AnalyticsEvent.objects.create(
                project=project,
                user=editor,
                event_name="view",
                properties={},
                timestamp=now,
            )
        resp = editor_client.get(f"{analytics_summary_url(project.id)}?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 8
        event_names = {item["event_name"] for item in data["by_event"]}
        assert "click" in event_names
        assert "view" in event_names

    def test_events_list(self, editor_client, project, editor):
        """Track 3 events via ORM, GET events/ → 3 items."""
        now = timezone.now()
        for i in range(3):
            AnalyticsEvent.objects.create(
                project=project,
                user=editor,
                event_name=f"event_{i}",
                properties={},
                timestamp=now,
            )
        resp = editor_client.get(analytics_events_url(project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_events_filter_by_name(self, editor_client, project, editor):
        """Track 'a' x2 and 'b' x1, filter by event_name=a → 2 results."""
        now = timezone.now()
        for _ in range(2):
            AnalyticsEvent.objects.create(
                project=project,
                user=editor,
                event_name="a",
                properties={},
                timestamp=now,
            )
        AnalyticsEvent.objects.create(
            project=project,
            user=editor,
            event_name="b",
            properties={},
            timestamp=now,
        )
        resp = editor_client.get(f"{analytics_events_url(project.id)}?event_name=a")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_unauthenticated(self, project):
        """No auth → 401."""
        client = APIClient()
        resp = client.post(
            analytics_track_url(project.id),
            {"event_name": "x", "properties": {}, "timestamp": "2025-01-01T00:00:00Z"},
            format="json",
        )
        assert resp.status_code == 401


# ===========================================================================
# TestBilling
# ===========================================================================

@pytest.mark.django_db
class TestBilling:

    def test_subscription_auto_created(self, editor_client, project):
        """GET subscription/ → 200, tier=='free' (auto-created)."""
        resp = editor_client.get(billing_subscription_url(project.id))
        assert resp.status_code == 200
        assert resp.json()["tier"] == "free"

    def test_subscription_has_limits(self, editor_client, project):
        """Subscription response includes limits.api_calls_monthly == 10000."""
        resp = editor_client.get(billing_subscription_url(project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "limits" in data
        assert data["limits"]["api_calls_monthly"] == 10_000

    def test_patch_billing_email(self, editor_client, project):
        """Editor PATCH billing_email → 200."""
        resp = editor_client.patch(
            billing_subscription_url(project.id),
            {"billing_email": "test@example.com"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["billing_email"] == "test@example.com"

    def test_patch_tier_is_ignored(self, editor_client, project):
        """Editor PATCH tier is silently ignored — tier only changes via the
        Stripe checkout/webhook flow, never directly through this API."""
        resp = editor_client.patch(
            billing_subscription_url(project.id),
            {"tier": "enterprise"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["tier"] == "free"

    def test_viewer_cannot_patch(self, viewer_client, project):
        """Viewer PATCH subscription → 403."""
        resp = viewer_client.patch(
            billing_subscription_url(project.id),
            {"billing_email": "viewer@example.com"},
            format="json",
        )
        assert resp.status_code == 403

    def test_usage_view(self, editor_client, project):
        """GET billing/usage/ → has api_calls, limits, percentages keys."""
        resp = editor_client.get(billing_usage_url(project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert "api_calls" in data
        assert "limits" in data
        assert "percentages" in data

    def test_tiers_public(self):
        """GET /api/billing/tiers/ → has free, starter, pro, enterprise keys."""
        client = APIClient()
        resp = client.get(billing_tiers_url())
        assert resp.status_code == 200
        data = resp.json()
        for tier in ("free", "starter", "pro", "enterprise"):
            assert tier in data

    def test_check_quota_free(self, project):
        """check_quota returns allowed==True when usage==0 on free tier."""
        from billing.services import check_quota
        result = check_quota(project, "api_calls_monthly")
        assert result["allowed"] is True

    def test_increment_usage(self, project):
        """increment_usage(5) → get_or_create_usage().api_calls == 5."""
        from billing.services import increment_usage, get_or_create_usage
        increment_usage(project, "api_calls_monthly", 5)
        usage = get_or_create_usage(project)
        assert usage.api_calls == 5


# ===========================================================================
# TestStripeCheckoutAndPortal / TestStripeWebhooks
#
# Real integration tests against a local stripe-mock instance
# (https://github.com/stripe/stripe-mock) — actual HTTP calls, actual Stripe
# API response parsing, not mocked. Skipped automatically if stripe-mock
# isn't running:
#   brew install stripe-mock
#   stripe-mock -http-port 12111 -https-port 12112
# ===========================================================================

def _stripe_mock_available():
    try:
        urllib.request.urlopen("http://localhost:12111/v1/customers", timeout=0.5)
    except urllib.error.HTTPError:
        return True  # any HTTP response (even 4xx/405) means the server is up
    except Exception:
        return False
    return True


requires_stripe_mock = pytest.mark.skipif(
    not _stripe_mock_available(),
    reason="stripe-mock not running on localhost:12111 (brew install stripe-mock)",
)


def _sign_stripe_payload(payload: str, secret: str) -> str:
    """Build a Stripe-Signature header exactly as Stripe itself does
    (https://stripe.com/docs/webhooks#verify-manually) — used to construct
    synthetic-but-correctly-signed webhook requests for testing."""
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


@requires_stripe_mock
@pytest.mark.django_db
class TestStripeCheckoutAndPortal:
    @pytest.fixture(autouse=True)
    def _stripe_settings(self, settings):
        settings.STRIPE_API_BASE = "http://localhost:12111"
        settings.STRIPE_SECRET_KEY = "sk_test_fake"
        settings.STRIPE_WEBHOOK_SECRET = "whsec_test_fake"
        settings.STRIPE_PRICE_IDS = {
            "starter": "price_starter_test",
            "pro": "price_pro_test",
            "enterprise": "price_enterprise_test",
        }

    def test_checkout_requires_valid_tier(self, editor_client, project):
        resp = editor_client.post(
            billing_checkout_url(project.id),
            {"tier": "bogus", "success_url": "https://x/ok", "cancel_url": "https://x/cancel"},
            format="json",
        )
        assert resp.status_code == 400

    def test_checkout_requires_urls(self, editor_client, project):
        resp = editor_client.post(
            billing_checkout_url(project.id),
            {"tier": "starter"},
            format="json",
        )
        assert resp.status_code == 400

    def test_viewer_cannot_checkout(self, viewer_client, project):
        resp = viewer_client.post(
            billing_checkout_url(project.id),
            {"tier": "starter", "success_url": "https://x/ok", "cancel_url": "https://x/cancel"},
            format="json",
        )
        assert resp.status_code == 403

    def test_checkout_creates_real_stripe_customer_and_session(self, editor_client, project):
        """Against real stripe-mock: a checkout.Session actually comes back with
        a URL, and a real Stripe customer id gets persisted locally."""
        resp = editor_client.post(
            billing_checkout_url(project.id),
            {
                "tier": "starter",
                "success_url": "https://example.com/ok",
                "cancel_url": "https://example.com/cancel",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.content
        data = resp.json()
        assert data["checkout_url"]
        assert data["session_id"]

        sub = ProjectSubscription.objects.get(project=project)
        assert sub.stripe_customer_id.startswith("cus_")
        # tier must NOT change yet — only the webhook does that, once Stripe
        # confirms payment.
        assert sub.tier == "free"

    def test_checkout_reuses_existing_stripe_customer(self, editor_client, project):
        """Second checkout call should reuse the same customer, not create a new one."""
        resp1 = editor_client.post(
            billing_checkout_url(project.id),
            {
                "tier": "starter",
                "success_url": "https://example.com/ok",
                "cancel_url": "https://example.com/cancel",
            },
            format="json",
        )
        cust1 = ProjectSubscription.objects.get(project=project).stripe_customer_id

        resp2 = editor_client.post(
            billing_checkout_url(project.id),
            {
                "tier": "pro",
                "success_url": "https://example.com/ok",
                "cancel_url": "https://example.com/cancel",
            },
            format="json",
        )
        cust2 = ProjectSubscription.objects.get(project=project).stripe_customer_id

        assert resp1.status_code == 201 and resp2.status_code == 201
        assert cust1 == cust2

    def test_portal_requires_existing_customer(self, editor_client, project):
        resp = editor_client.post(
            billing_portal_url(project.id),
            {"return_url": "https://example.com/account"},
            format="json",
        )
        assert resp.status_code == 400

    def test_portal_returns_url_after_checkout(self, editor_client, project):
        editor_client.post(
            billing_checkout_url(project.id),
            {
                "tier": "starter",
                "success_url": "https://example.com/ok",
                "cancel_url": "https://example.com/cancel",
            },
            format="json",
        )
        resp = editor_client.post(
            billing_portal_url(project.id),
            {"return_url": "https://example.com/account"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["portal_url"]


@requires_stripe_mock
@pytest.mark.django_db
class TestStripeWebhooks:
    @pytest.fixture(autouse=True)
    def _stripe_settings(self, settings):
        settings.STRIPE_API_BASE = "http://localhost:12111"
        settings.STRIPE_SECRET_KEY = "sk_test_fake"
        settings.STRIPE_WEBHOOK_SECRET = "whsec_test_fake"
        settings.STRIPE_PRICE_IDS = {
            "starter": "price_starter_test",
            "pro": "price_pro_test",
            "enterprise": "price_enterprise_test",
        }

    def _post_event(self, event: dict):
        # Real Stripe events always carry "object": "event" at the top level —
        # stripe.Webhook.construct_event checks it internally to distinguish
        # v1 webhook payloads from the newer "thin" v2 event notifications.
        event = {"object": "event", **event}
        payload = json.dumps(event)
        header = _sign_stripe_payload(payload, "whsec_test_fake")
        client = APIClient()
        return client.post(
            "/api/billing/webhook/",
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )

    def test_webhook_rejects_bad_signature(self, project):
        event = {
            "object": "event",
            "id": "evt_1",
            "type": "checkout.session.completed",
            "data": {"object": {}},
        }
        client = APIClient()
        resp = client.post(
            "/api/billing/webhook/",
            data=json.dumps(event),
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=1,v1=deadbeef",
        )
        assert resp.status_code == 400

    def test_webhook_checkout_completed_upgrades_tier(self, project):
        event = {
            "id": "evt_checkout_1",
            "type": "checkout.session.completed",
            "data": {"object": {
                "id": "cs_test_1",
                "subscription": "sub_test_1",
                "metadata": {"project_id": str(project.id), "tier": "pro"},
            }},
        }
        resp = self._post_event(event)
        assert resp.status_code == 200

        sub = ProjectSubscription.objects.get(project=project)
        assert sub.tier == "pro"
        assert sub.stripe_subscription_id == "sub_test_1"

    def test_webhook_checkout_completed_missing_metadata_is_ignored(self, project):
        """Malformed/foreign event (no project_id/tier metadata) must not crash
        the webhook or affect any subscription."""
        event = {
            "id": "evt_checkout_bad",
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_bad", "subscription": "sub_test_bad"}},
        }
        resp = self._post_event(event)
        assert resp.status_code == 200
        assert not ProjectSubscription.objects.filter(stripe_subscription_id="sub_test_bad").exists()

    def test_webhook_subscription_deleted_downgrades_to_free(self, project):
        ProjectSubscription.objects.update_or_create(
            project=project, defaults={"tier": "pro", "stripe_subscription_id": "sub_test_2"},
        )
        event = {
            "id": "evt_deleted_1",
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_test_2"}},
        }
        resp = self._post_event(event)
        assert resp.status_code == 200

        sub = ProjectSubscription.objects.get(project=project)
        assert sub.tier == "free"
        assert sub.stripe_subscription_id == ""

    def test_webhook_subscription_updated_switches_tier_via_portal(self, project):
        """Simulates a customer changing plans directly in the Stripe billing
        portal (not via a new checkout) — the webhook must re-derive the tier
        from the subscription's current price."""
        ProjectSubscription.objects.update_or_create(
            project=project, defaults={"tier": "starter", "stripe_subscription_id": "sub_test_3"},
        )
        event = {
            "id": "evt_updated_1",
            "type": "customer.subscription.updated",
            "data": {"object": {
                "id": "sub_test_3",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_enterprise_test"}}]},
            }},
        }
        resp = self._post_event(event)
        assert resp.status_code == 200

        sub = ProjectSubscription.objects.get(project=project)
        assert sub.tier == "enterprise"

    def test_webhook_subscription_updated_canceled_status_downgrades(self, project):
        ProjectSubscription.objects.update_or_create(
            project=project, defaults={"tier": "pro", "stripe_subscription_id": "sub_test_4"},
        )
        event = {
            "id": "evt_updated_2",
            "type": "customer.subscription.updated",
            "data": {"object": {"id": "sub_test_4", "status": "canceled"}},
        }
        resp = self._post_event(event)
        assert resp.status_code == 200

        sub = ProjectSubscription.objects.get(project=project)
        assert sub.tier == "free"

    def test_webhook_unknown_event_type_is_ignored(self, project):
        event = {"id": "evt_unknown", "type": "invoice.paid", "data": {"object": {}}}
        resp = self._post_event(event)
        assert resp.status_code == 200  # ignored gracefully, not an error

    def test_webhook_is_idempotent_under_replay(self, project):
        """Stripe delivers webhooks at-least-once and retries on any non-2xx
        response — replaying the identical event must be a no-op, not a
        duplicate row or a double-charge-equivalent side effect."""
        event = {
            "id": "evt_replay_1",
            "type": "checkout.session.completed",
            "data": {"object": {
                "id": "cs_test_replay",
                "subscription": "sub_test_replay",
                "metadata": {"project_id": str(project.id), "tier": "pro"},
            }},
        }
        resp1 = self._post_event(event)
        resp2 = self._post_event(event)
        assert resp1.status_code == 200 and resp2.status_code == 200

        assert ProjectSubscription.objects.filter(project=project).count() == 1
        sub = ProjectSubscription.objects.get(project=project)
        assert sub.tier == "pro"
        assert sub.stripe_subscription_id == "sub_test_replay"


# ===========================================================================
# TestRealtimeBroadcast
# ===========================================================================

@pytest.mark.django_db
class TestRealtimeBroadcast:

    def test_broadcast_no_channel_layer(self):
        """broadcast_document_event with no channel layer does NOT raise."""
        from unittest.mock import patch
        from realtime.broadcast import broadcast_document_event
        with patch("realtime.broadcast.get_channel_layer", return_value=None):
            # Should silently return without raising
            broadcast_document_event("proj-id", "users", "created", {"id": "doc1"})

    def test_signing_sign_and_structure(self):
        """sign_payload returns a string starting with 't=' and containing 'v1='."""
        from webhooks.signing import sign_payload
        sig = sign_payload("secret", {"x": 1})
        assert sig.startswith("t=")
        assert "v1=" in sig

    def test_signing_verify_valid(self):
        """sign_payload + verify_signature round-trip succeeds."""
        from webhooks.signing import sign_payload, verify_signature
        payload = {"x": 1}
        sig = sign_payload("secret", payload)
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        assert verify_signature("secret", body, sig) is True
