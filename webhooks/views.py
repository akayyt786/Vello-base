from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Project, ProjectMembership
from .models import WebhookEndpoint, WebhookDelivery
from .serializers import WebhookEndpointSerializer, WebhookDeliverySerializer


def _get_project_and_membership(request, project_id, require_editor=False):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        raise PermissionDenied('Editor role required.')
    return project, membership


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project, _ = _get_project_and_membership(self.request, self.kwargs['project_id'])
        return WebhookEndpoint.objects.filter(project=project)

    def perform_create(self, serializer):
        project, _ = _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        serializer.save(project=project)

    def perform_update(self, serializer):
        _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        serializer.save()

    def perform_destroy(self, instance):
        _get_project_and_membership(self.request, self.kwargs['project_id'], require_editor=True)
        instance.delete()

    @action(detail=True, methods=['get'], url_path='deliveries')
    def deliveries(self, request, pk=None, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        endpoint = get_object_or_404(WebhookEndpoint, pk=pk, project=project)
        qs = WebhookDelivery.objects.filter(endpoint=endpoint).order_by('-created_at')[:50]
        return Response(WebhookDeliverySerializer(qs, many=True).data)
