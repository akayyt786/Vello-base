from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Project, ProjectMembership
from .models import RemoteConfigParameter
from .serializers import RemoteConfigParameterSerializer, RemoteConfigFetchSerializer


def _get_project_and_membership(request, project_id, require_editor=False):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        raise PermissionDenied('Editor role required.')
    return project, membership


class RemoteConfigViewSet(viewsets.ModelViewSet):
    """CRUD for remote config parameters (admin-side)."""
    serializer_class = RemoteConfigParameterSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project, _ = _get_project_and_membership(self.request, self.kwargs['project_id'])
        return RemoteConfigParameter.objects.filter(project=project)

    def perform_create(self, serializer):
        project, _ = _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        try:
            serializer.save(project=project)
        except IntegrityError:
            raise ValidationError({'key': 'A parameter with this key already exists for this project.'})

    def perform_update(self, serializer):
        _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        serializer.save()

    def perform_destroy(self, instance):
        _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        instance.delete()


class RemoteConfigFetchView(APIView):
    """
    GET /api/projects/{id}/remoteconfig/fetch/
    Client-facing endpoint — returns all active parameters with typed values.
    Auth: Bearer token (project member) OR ?api_key=<project_api_key> for SDK use.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        params = RemoteConfigParameter.objects.filter(project=project, is_active=True)
        result = {p.key: p.cast_value() for p in params}
        return Response(result)
