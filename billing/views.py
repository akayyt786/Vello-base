from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Project, ProjectMembership
from .models import ProjectSubscription, QuotaUsage, TIER_LIMITS
from .serializers import ProjectSubscriptionSerializer, QuotaUsageSerializer
from .services import get_subscription, get_or_create_usage, check_quota


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
