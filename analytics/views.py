"""
Analytics API views.

  GET    /api/projects/{id}/analytics/events/                     — list events
  POST   /api/projects/{id}/analytics/events/                     — log single event
  POST   /api/projects/{id}/analytics/events/batch/               — log up to 500 events
  GET    /api/projects/{id}/analytics/events/{pk}/                — event detail

  GET    /api/projects/{id}/analytics/user-properties/            — list user properties
  POST   /api/projects/{id}/analytics/user-properties/            — set user property
  GET    /api/projects/{id}/analytics/user-properties/{pk}/       — property detail
  PUT    /api/projects/{id}/analytics/user-properties/{pk}/       — update property
  DELETE /api/projects/{id}/analytics/user-properties/{pk}/       — delete property
  POST   /api/projects/{id}/analytics/user-properties/set/        — bulk upsert properties

  GET    /api/projects/{id}/analytics/conversion-events/          — list conversion events
  POST   /api/projects/{id}/analytics/conversion-events/          — create conversion event
  DELETE /api/projects/{id}/analytics/conversion-events/{pk}/     — remove conversion event

  GET    /api/projects/{id}/analytics/query/                      — aggregated metrics query
"""

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Project, ProjectMembership
from core.pagination import DefaultCursorPagination
from .models import Event, UserProperty, ConversionEvent
from .serializers import EventSerializer, UserPropertySerializer, ConversionEventSerializer


class _UpdatedAtCursorPagination(DefaultCursorPagination):
    ordering = '-updated_at'

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
# Event ViewSet
# ---------------------------------------------------------------------------

class EventViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    Log and retrieve analytics events.
    Any project member can log events; writes do not require editor role.
    """
    serializer_class = EventSerializer
    _model = Event
    _write_requires_editor = False
    http_method_names = ['get', 'post', 'head', 'options']

    def perform_create(self, serializer):
        project = self._project(require_editor=self._write_requires_editor)
        # Default occurred_at to now if not provided by the client.
        occurred_at = serializer.validated_data.get('occurred_at') or timezone.now()
        serializer.save(project=project, occurred_at=occurred_at)

    @action(detail=False, methods=['post'], url_path='batch')
    def batch(self, request, project_id=None):
        """
        Log up to 500 events in a single request.
        Accepts a list of event dicts in request.data.
        All events are created atomically.
        Returns {count: N} on success.
        """
        project = self._project(require_editor=self._write_requires_editor)

        if not isinstance(request.data, list):
            return Response(
                {'error': 'Request body must be a JSON array of event objects.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(request.data) > 500:
            return Response(
                {'error': 'Batch size exceeds maximum of 500 events.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.data:
            return Response({'count': 0}, status=status.HTTP_200_OK)

        serializer = EventSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        events = []
        for item in serializer.validated_data:
            item.setdefault('occurred_at', now)
            events.append(Event(project=project, **item))

        with transaction.atomic():
            Event.objects.bulk_create(events)

        return Response({'count': len(events)}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# UserProperty ViewSet
# ---------------------------------------------------------------------------

class UserPropertyViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    Manage per-user persistent properties (mirrors Firebase setUserProperty).
    Any project member can write properties.
    """
    serializer_class = UserPropertySerializer
    _model = UserProperty
    _write_requires_editor = False
    pagination_class = _UpdatedAtCursorPagination

    @action(detail=False, methods=['post'], url_path='set')
    def set_properties(self, request, project_id=None):
        """
        Bulk upsert user properties.
        Accepts {user_id: str, properties: {name: value, ...}}.
        Returns {updated: N} on success.
        """
        project = self._project(require_editor=self._write_requires_editor)

        user_id = request.data.get('user_id', '').strip()
        if not user_id:
            return Response(
                {'error': 'user_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        properties = request.data.get('properties')
        if not isinstance(properties, dict):
            return Response(
                {'error': 'properties must be a JSON object mapping name to value.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_count = 0
        with transaction.atomic():
            for name, value in properties.items():
                UserProperty.objects.update_or_create(
                    project=project,
                    user_id=user_id,
                    name=str(name)[:64],
                    defaults={'value': str(value)[:256]},
                )
                updated_count += 1

        return Response({'updated': updated_count}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# ConversionEvent ViewSet
# ---------------------------------------------------------------------------

class ConversionEventViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    Manage conversion event configuration.
    Editor or owner role required to mutate.
    """
    serializer_class = ConversionEventSerializer
    _model = ConversionEvent
    _write_requires_editor = True


# ---------------------------------------------------------------------------
# Analytics Query View
# ---------------------------------------------------------------------------

class AnalyticsQueryView(APIView):
    """
    Aggregated analytics metrics query.

    GET /api/projects/{project_id}/analytics/query/

    Query params:
      metric      — event_count | unique_users | session_count  (required)
      event_name  — filter to a specific event name             (optional)
      start_date  — ISO date, inclusive                         (required)
      end_date    — ISO date, inclusive                         (required)
      group_by    — day | week | month | event_name | platform  (required)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id=None):
        from django.db.models import Count
        from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

        project, _ = _get_project_and_membership(request, project_id)

        # --- Validate required params ---
        metric = request.query_params.get('metric', '').strip()
        valid_metrics = ('event_count', 'unique_users', 'session_count')
        if metric not in valid_metrics:
            return Response(
                {'error': f'metric must be one of: {", ".join(valid_metrics)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date = request.query_params.get('start_date', '').strip()
        end_date = request.query_params.get('end_date', '').strip()
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required (ISO date format).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group_by = request.query_params.get('group_by', '').strip()
        valid_group_by = ('day', 'week', 'month', 'event_name', 'platform')
        if group_by not in valid_group_by:
            return Response(
                {'error': f'group_by must be one of: {", ".join(valid_group_by)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from django.utils.dateparse import parse_date
            start = parse_date(start_date)
            end = parse_date(end_date)
            if start is None or end is None:
                raise ValueError('unparseable date')
        except (ValueError, TypeError):
            return Response(
                {'error': 'start_date and end_date must be valid ISO dates (YYYY-MM-DD).'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Build queryset ---
        qs = Event.objects.filter(
            project=project,
            occurred_at__date__gte=start,
            occurred_at__date__lte=end,
        )

        event_name_filter = request.query_params.get('event_name', '').strip()
        if event_name_filter:
            qs = qs.filter(event_name=event_name_filter)

        # --- Apply group_by annotation ---
        TRUNC_MAP = {
            'day': TruncDay,
            'week': TruncWeek,
            'month': TruncMonth,
        }

        if group_by in TRUNC_MAP:
            trunc_fn = TRUNC_MAP[group_by]
            qs = qs.annotate(period=trunc_fn('occurred_at'))
            group_field = 'period'
        else:
            # group_by in ('event_name', 'platform')
            group_field = group_by

        # --- Compute the requested metric ---
        if metric == 'event_count':
            agg = Count('id')
            agg_label = 'event_count'
        elif metric == 'unique_users':
            agg = Count('user_id', distinct=True)
            agg_label = 'unique_users'
        else:  # session_count
            agg = Count('session_id', distinct=True)
            agg_label = 'session_count'

        rows = (
            qs
            .values(group_field)
            .annotate(**{agg_label: agg})
            .order_by(group_field)
        )

        data = []
        for row in rows:
            value = row[group_field]
            # Serialize datetime/date objects to ISO strings for JSON
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            data.append({group_field: value, agg_label: row[agg_label]})

        return Response({
            'metric': metric,
            'group_by': group_by,
            'start_date': start_date,
            'end_date': end_date,
            'results': data,
        })
