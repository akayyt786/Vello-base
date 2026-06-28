"""
Crashlytics API views.

  GET    /api/projects/{id}/crashlytics/groups/                      — list crash groups
  GET    /api/projects/{id}/crashlytics/groups/{pk}/                 — crash group detail
  PATCH  /api/projects/{id}/crashlytics/groups/{pk}/                 — update is_resolved / notes
  POST   /api/projects/{id}/crashlytics/groups/{pk}/resolve/         — mark resolved
  POST   /api/projects/{id}/crashlytics/groups/{pk}/unresolve/       — mark unresolved

  GET    /api/projects/{id}/crashlytics/reports/                     — list crash reports
  POST   /api/projects/{id}/crashlytics/reports/                     — submit crash report
  GET    /api/projects/{id}/crashlytics/reports/{pk}/                — report detail

  GET    /api/projects/{id}/crashlytics/traces/                      — list performance traces
  POST   /api/projects/{id}/crashlytics/traces/                      — submit trace
  GET    /api/projects/{id}/crashlytics/traces/{pk}/                 — trace detail
  POST   /api/projects/{id}/crashlytics/traces/batch/                — submit up to 500 traces

  GET    /api/projects/{id}/crashlytics/network/                     — list network requests
  POST   /api/projects/{id}/crashlytics/network/                     — submit network request
  GET    /api/projects/{id}/crashlytics/network/{pk}/                — network request detail
  POST   /api/projects/{id}/crashlytics/network/batch/               — submit up to 500 network requests

  GET    /api/projects/{id}/crashlytics/summary/                     — crash + perf summary
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Project, ProjectMembership
from .models import CrashGroup, CrashReport, PerformanceTrace, NetworkRequest
from .serializers import (
    CrashGroupSerializer,
    CrashReportSerializer,
    PerformanceTraceSerializer,
    NetworkRequestSerializer,
)
from .services import group_crash_report

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers (mirrors push/views.py pattern)
# ---------------------------------------------------------------------------

def _get_project_and_membership(request, project_id, require_editor=False):
    """
    Fetch project + verify membership.  Raises PermissionDenied instead of
    returning a Response tuple so ViewSet actions can call it inline.
    Returns (project, membership).
    """
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        raise PermissionDenied('Editor role required.')
    return project, membership


# ---------------------------------------------------------------------------
# Base mixin used by all ViewSets in this app
# ---------------------------------------------------------------------------

class _ProjectScopedMixin:
    """
    Mixin that wires project-scoped access control into a ModelViewSet.
    Subclasses must set `_model` to the concrete model class.
    """
    permission_classes = [IsAuthenticated]

    # Override in subclasses to require editor role for mutating operations.
    _write_requires_editor = True

    def _project(self, require_editor=False):
        project, _ = _get_project_and_membership(
            self.request,
            self.kwargs['project_id'],
            require_editor=require_editor,
        )
        return project

    def get_queryset(self):
        project = self._project()
        return self._model.objects.filter(project=project)

    def perform_create(self, serializer):
        project = self._project(require_editor=self._write_requires_editor)
        serializer.save(project=project)

    def perform_update(self, serializer):
        self._project(require_editor=self._write_requires_editor)
        serializer.save()

    def perform_destroy(self, instance):
        self._project(require_editor=self._write_requires_editor)
        instance.delete()


# ---------------------------------------------------------------------------
# CrashGroup ViewSet (read + partial_update only — no create, no delete)
# ---------------------------------------------------------------------------

class CrashGroupViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    Read crash groups and update their resolution state / notes.
    Groups are created automatically by the grouping service — no direct POST.
    """
    serializer_class = CrashGroupSerializer
    _model = CrashGroup
    _write_requires_editor = True
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def create(self, request, *args, **kwargs):
        """Direct creation is not allowed; groups are created by the grouping service."""
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed('POST')

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None, project_id=None):
        """Mark a crash group as resolved."""
        project = self._project(require_editor=True)
        crash_group = get_object_or_404(CrashGroup, pk=pk, project=project)
        crash_group.is_resolved = True
        crash_group.resolved_at = timezone.now()
        crash_group.save(update_fields=['is_resolved', 'resolved_at', 'updated_at'])
        return Response(CrashGroupSerializer(crash_group).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='unresolve')
    def unresolve(self, request, pk=None, project_id=None):
        """Mark a crash group as unresolved (regression)."""
        project = self._project(require_editor=True)
        crash_group = get_object_or_404(CrashGroup, pk=pk, project=project)
        crash_group.is_resolved = False
        crash_group.resolved_at = None
        crash_group.save(update_fields=['is_resolved', 'resolved_at', 'updated_at'])
        return Response(CrashGroupSerializer(crash_group).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# CrashReport ViewSet (list + create only — no update/delete)
# ---------------------------------------------------------------------------

class CrashReportViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    Submit and list individual crash occurrences.
    On create, the report is automatically grouped via the grouping service.
    Any project member (not just editors) may submit a crash report.
    """
    serializer_class = CrashReportSerializer
    _model = CrashReport
    _write_requires_editor = False
    http_method_names = ['get', 'post', 'head', 'options']

    def perform_create(self, serializer):
        project = self._project(require_editor=self._write_requires_editor)
        report = serializer.save(project=project)
        # Deduplicate into a CrashGroup
        try:
            group_crash_report(report)
        except Exception as exc:
            logger.error('Failed to group crash report %s: %s', report.id, exc)


# ---------------------------------------------------------------------------
# PerformanceTrace ViewSet
# ---------------------------------------------------------------------------

class PerformanceTraceViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    Submit and list client-side performance traces.
    Any project member may submit; batch endpoint accepts up to 500 traces at once.
    """
    serializer_class = PerformanceTraceSerializer
    _model = PerformanceTrace
    _write_requires_editor = False
    http_method_names = ['get', 'post', 'head', 'options']

    @action(detail=False, methods=['post'], url_path='batch')
    def batch(self, request, project_id=None):
        """
        Bulk-create up to 500 performance traces in a single request.
        Accepts a JSON list of trace objects.
        """
        project = self._project(require_editor=False)
        items = request.data
        if not isinstance(items, list):
            return Response(
                {'error': 'Expected a JSON array of trace objects.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(items) > 500:
            return Response(
                {'error': 'Batch size exceeds the maximum of 500 items.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PerformanceTraceSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)
        traces = serializer.save(project=project)
        return Response(
            PerformanceTraceSerializer(traces, many=True).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# NetworkRequest ViewSet
# ---------------------------------------------------------------------------

class NetworkRequestViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    Submit and list HTTP network request performance records.
    Any project member may submit; batch endpoint accepts up to 500 records at once.
    """
    serializer_class = NetworkRequestSerializer
    _model = NetworkRequest
    _write_requires_editor = False
    http_method_names = ['get', 'post', 'head', 'options']

    @action(detail=False, methods=['post'], url_path='batch')
    def batch(self, request, project_id=None):
        """
        Bulk-create up to 500 network request records in a single request.
        Accepts a JSON list of network request objects.
        """
        project = self._project(require_editor=False)
        items = request.data
        if not isinstance(items, list):
            return Response(
                {'error': 'Expected a JSON array of network request objects.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(items) > 500:
            return Response(
                {'error': 'Batch size exceeds the maximum of 500 items.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = NetworkRequestSerializer(data=items, many=True)
        serializer.is_valid(raise_exception=True)
        network_requests = serializer.save(project=project)
        return Response(
            NetworkRequestSerializer(network_requests, many=True).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# CrashSummaryView — project dashboard stats
# ---------------------------------------------------------------------------

class CrashSummaryView(APIView):
    """
    GET /api/projects/{project_id}/crashlytics/summary/

    Returns high-level crash + performance stats for the project:
      - total_crash_groups
      - unresolved_groups
      - total_reports_last_7d
      - affected_users_last_7d
      - top_crashes (top 10 by occurrence_count)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)

        seven_days_ago = timezone.now() - timezone.timedelta(days=7)

        total_crash_groups = CrashGroup.objects.filter(project=project).count()
        unresolved_groups = CrashGroup.objects.filter(project=project, is_resolved=False).count()

        total_reports_last_7d = CrashReport.objects.filter(
            project=project,
            occurred_at__gte=seven_days_ago,
        ).count()

        # Count distinct user_ids over the last 7 days (exclude blank)
        affected_users_last_7d = (
            CrashReport.objects
            .filter(project=project, occurred_at__gte=seven_days_ago)
            .exclude(user_id='')
            .values('user_id')
            .distinct()
            .count()
        )

        top_crashes = list(
            CrashGroup.objects
            .filter(project=project)
            .order_by('-occurrence_count')[:10]
            .values('signature', 'title', 'occurrence_count', 'last_seen_at')
        )
        # Rename occurrence_count -> count for cleaner API
        top_crashes_out = [
            {
                'signature': c['signature'],
                'title': c['title'],
                'count': c['occurrence_count'],
                'last_seen': c['last_seen_at'],
            }
            for c in top_crashes
        ]

        return Response({
            'total_crash_groups': total_crash_groups,
            'unresolved_groups': unresolved_groups,
            'total_reports_last_7d': total_reports_last_7d,
            'affected_users_last_7d': affected_users_last_7d,
            'top_crashes': top_crashes_out,
        })
