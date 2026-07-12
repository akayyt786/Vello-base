import stripe
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Project, ProjectMembership
from .models import ProjectSubscription, QuotaUsage, TIER_LIMITS
from .serializers import ProjectSubscriptionSerializer, QuotaUsageSerializer
from .services import get_subscription, get_or_create_usage, check_quota
from .stripe_service import (
    create_checkout_session,
    create_billing_portal_session,
    construct_webhook_event,
    handle_webhook_event,
)


def _get_project_and_membership(request, project_id, require_editor=False):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        raise PermissionDenied('Editor role required.')
    return project, membership


class SubscriptionView(APIView):
    """GET/PATCH /api/projects/{id}/billing/subscription/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        sub = get_subscription(project)
        return Response(ProjectSubscriptionSerializer(sub).data)

    def patch(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id, require_editor=True)
        sub = get_subscription(project)
        ser = ProjectSubscriptionSerializer(sub, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class QuotaUsageView(APIView):
    """GET /api/projects/{id}/billing/usage/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        usage = get_or_create_usage(project)
        sub = get_subscription(project)
        limits = sub.get_limits()
        data = QuotaUsageSerializer(usage).data
        data['limits'] = limits
        data['tier'] = sub.tier
        data['percentages'] = {}
        for resource_key, field in [
            ('api_calls_monthly', 'api_calls'),
            ('function_invocations', 'function_invocations'),
            ('ai_tokens', 'ai_tokens'),
        ]:
            lim = limits.get(resource_key, 0)
            used = data.get(field, 0)
            data['percentages'][field] = round(100 * used / lim, 1) if lim and lim != -1 else 0
        return Response(data)


class TiersView(APIView):
    """GET /api/billing/tiers/ — public plan info."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(TIER_LIMITS)


class CreateCheckoutSessionView(APIView):
    """POST /api/projects/{id}/billing/checkout/ — start a paid-tier upgrade.

    Body: {tier: 'starter'|'pro'|'enterprise', success_url, cancel_url}.
    The project's tier only actually changes once Stripe calls back to the
    webhook endpoint with checkout.session.completed — this just returns a
    URL for the client to redirect the user to.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id, require_editor=True)

        tier = request.data.get('tier')
        if tier not in ('starter', 'pro', 'enterprise'):
            return Response({'error': "tier must be one of: starter, pro, enterprise"}, status=400)

        success_url = request.data.get('success_url')
        cancel_url = request.data.get('cancel_url')
        if not success_url or not cancel_url:
            return Response({'error': 'success_url and cancel_url are required'}, status=400)

        sub = get_subscription(project)
        try:
            session = create_checkout_session(sub, request.user, tier, success_url, cancel_url)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except stripe.error.StripeError as e:
            return Response({'error': f'Stripe error: {e.user_message or str(e)}'}, status=502)

        return Response({'checkout_url': session['url'], 'session_id': session['id']}, status=201)


class BillingPortalView(APIView):
    """POST /api/projects/{id}/billing/portal/ — open the Stripe billing portal."""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id, require_editor=True)

        return_url = request.data.get('return_url')
        if not return_url:
            return Response({'error': 'return_url is required'}, status=400)

        sub = get_subscription(project)
        try:
            session = create_billing_portal_session(sub, return_url)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except stripe.error.StripeError as e:
            return Response({'error': f'Stripe error: {e.user_message or str(e)}'}, status=502)

        return Response({'portal_url': session['url']}, status=200)


class StripeWebhookView(APIView):
    """POST /api/billing/webhook/ — Stripe calls this directly (no project in the URL;
    the project is identified via checkout metadata or the subscription id already
    stored on a ProjectSubscription). Authenticated by Stripe-Signature, not a user token.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        try:
            event = construct_webhook_event(request.body, sig_header)
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=400)

        handle_webhook_event(event)
        return Response(status=200)
