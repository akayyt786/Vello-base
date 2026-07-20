"""
Remote Config API views.

  GET    /api/projects/{id}/config/parameters/                      — list config parameters
  POST   /api/projects/{id}/config/parameters/                      — create parameter
  GET    /api/projects/{id}/config/parameters/{pk}/                 — parameter detail
  PUT    /api/projects/{id}/config/parameters/{pk}/                 — update parameter
  DELETE /api/projects/{id}/config/parameters/{pk}/                 — delete parameter
  GET    /api/projects/{id}/config/parameters/fetch/                — evaluate params for client context
  POST   /api/projects/{id}/config/parameters/publish/              — publish a version snapshot

  GET    /api/projects/{id}/config/parameters/{config_id}/conditions/       — list conditions
  POST   /api/projects/{id}/config/parameters/{config_id}/conditions/       — create condition
  GET    /api/projects/{id}/config/parameters/{config_id}/conditions/{pk}/  — condition detail
  PUT    /api/projects/{id}/config/parameters/{config_id}/conditions/{pk}/  — update condition
  DELETE /api/projects/{id}/config/parameters/{config_id}/conditions/{pk}/  — delete condition

A/B experiments used to live here too (Experiment/ExperimentVariant), but
that was a duplicate of the dedicated abtesting app (which SDKs actually use,
and which additionally tracks assignment/conversion) -- see abtesting/views.py.
"""

import hashlib
import logging

from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Project, ProjectMembership
from .models import RemoteConfig, ConfigCondition, ConfigVersion
from .serializers import (
    RemoteConfigSerializer,
    ConfigConditionSerializer,
    ConfigVersionSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers (same pattern as push/views.py)
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
# Base mixin
# ---------------------------------------------------------------------------

class _ProjectScopedMixin:
    """
    Mixin that wires project-scoped access control into a ModelViewSet.
    Subclasses must set `_model` to the concrete model class.
    """
    permission_classes = [IsAuthenticated]
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
# Condition evaluation helper
# ---------------------------------------------------------------------------

def _evaluate_conditions(config, context):
    """
    Evaluate conditions for a RemoteConfig in priority order.
    Returns the first matching condition's value, or default_value if none match.

    context dict may contain:
      platform     (str, e.g. "ios", "android", "web")
      app_version  (str, e.g. "1.2.3")
      user_id      (str)
      user_props   (dict of user property name → value)
    """
    platform = context.get('platform', '')
    app_version = context.get('app_version', '')
    user_id = context.get('user_id', '')

    active_conditions = config.conditions.filter(is_active=True)

    for condition in active_conditions:
        ctype = condition.condition_type
        params = condition.condition_params or {}

        if ctype == ConfigCondition.CONDITION_TYPE_ALWAYS:
            return condition.value

        elif ctype == ConfigCondition.CONDITION_TYPE_PLATFORM:
            target = params.get('platform', '')
            if platform and platform.lower() == target.lower():
                return condition.value

        elif ctype == ConfigCondition.CONDITION_TYPE_APP_VERSION:
            target = params.get('app_version', '')
            if app_version and app_version == target:
                return condition.value

        elif ctype == ConfigCondition.CONDITION_TYPE_USER_PROPERTY:
            prop_name = params.get('property_name', '')
            prop_value = params.get('property_value', '')
            user_props = context.get('user_props', {})
            if prop_name and str(user_props.get(prop_name, '')) == str(prop_value):
                return condition.value

        elif ctype == ConfigCondition.CONDITION_TYPE_PERCENTAGE:
            if user_id:
                pct = params.get('percentage', 100)
                # deterministic hash-based bucketing
                bucket = int(hashlib.md5(
                    f"{config.id}:{user_id}".encode()
                ).hexdigest(), 16) % 100
                if bucket < pct:
                    return condition.value

    return config.default_value


# ---------------------------------------------------------------------------
# RemoteConfig ViewSet
# ---------------------------------------------------------------------------

class RemoteConfigViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for Remote Config parameters.
    Includes fetch (evaluate for client context) and publish (snapshot) actions.
    """
    serializer_class = RemoteConfigSerializer
    _model = RemoteConfig
    _write_requires_editor = True

    @action(detail=False, methods=['get'], url_path='fetch')
    def fetch(self, request, project_id=None):
        """
        Evaluate all active config parameters for a given client context.
        Accepts query params: platform, app_version, user_id.
        Returns {key: resolved_value} dict.
        """
        project = self._project()
        context = {
            'platform': request.query_params.get('platform', ''),
            'app_version': request.query_params.get('app_version', ''),
            'user_id': request.query_params.get('user_id', ''),
        }

        # Warn when clients send context as HTTP headers instead of query params —
        # those header values are silently discarded and the query param (which may
        # be absent) is used instead. This helps catch misconfigured clients early.
        _CONTEXT_HEADER_MAP = {
            'HTTP_X_PLATFORM': ('platform', '?platform='),
            'HTTP_X_APP_VERSION': ('app_version', '?app_version='),
            'HTTP_X_USER_ID': ('user_id', '?user_id='),
        }
        for meta_key, (param_name, hint) in _CONTEXT_HEADER_MAP.items():
            header_val = request.META.get(meta_key)
            if header_val and not request.query_params.get(param_name):
                logger.warning(
                    'RemoteConfig fetch [project=%s]: request header %s=%r is present '
                    'but will be discarded — pass context via query param %s instead.',
                    project_id, meta_key, header_val, hint,
                )

        configs = RemoteConfig.objects.filter(
            project=project,
            is_active=True,
        ).prefetch_related('conditions')

        resolved = {}
        for config in configs:
            resolved[config.key] = _evaluate_conditions(config, context)

        return Response(resolved, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='publish')
    def publish(self, request, project_id=None):
        """
        Publish a snapshot of all current config parameters as a new version.
        Editor or owner required. Returns the created ConfigVersion.
        """
        project = self._project(require_editor=True)

        with transaction.atomic():
            # Lock the project row to serialize concurrent publish requests.
            # Without this lock, two simultaneous publishes can both read the
            # same max version_number and then race to insert the same next
            # version, hitting the unique_together constraint.
            Project.objects.select_for_update().get(pk=project.pk)

            # Determine next version number
            max_ver = ConfigVersion.objects.filter(
                project=project
            ).aggregate(max=Max('version_number'))['max'] or 0
            next_version = max_ver + 1

            # Build params snapshot: {key: default_value} for all active params
            params_snapshot = {}
            for cfg in RemoteConfig.objects.filter(project=project, is_active=True):
                params_snapshot[cfg.key] = cfg.default_value

            description = request.data.get('description', '')
            version = ConfigVersion.objects.create(
                project=project,
                version_number=next_version,
                params=params_snapshot,
                description=description,
                published_by=request.user,
            )

        serializer = ConfigVersionSerializer(version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# ConfigCondition ViewSet (nested under RemoteConfig)
# ---------------------------------------------------------------------------

class ConfigConditionViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for conditions nested under a RemoteConfig parameter.
    URL must include config_id.
    """
    serializer_class = ConfigConditionSerializer
    _write_requires_editor = True

    # Override _model — this viewset doesn't use project-level filtering directly
    _model = None

    def get_queryset(self):
        project = self._project()
        config_id = self.kwargs['config_id']
        # Verify the config belongs to this project (guards cross-project access)
        get_object_or_404(RemoteConfig, id=config_id, project=project)
        return ConfigCondition.objects.filter(config_id=config_id)

    def perform_create(self, serializer):
        project = self._project(require_editor=self._write_requires_editor)
        config_id = self.kwargs['config_id']
        config = get_object_or_404(RemoteConfig, id=config_id, project=project)
        serializer.save(config=config)

    def perform_update(self, serializer):
        project = self._project(require_editor=self._write_requires_editor)
        config_id = self.kwargs['config_id']
        get_object_or_404(RemoteConfig, id=config_id, project=project)
        serializer.save()

    def perform_destroy(self, instance):
        project = self._project(require_editor=self._write_requires_editor)
        config_id = self.kwargs['config_id']
        get_object_or_404(RemoteConfig, id=config_id, project=project)
        instance.delete()
