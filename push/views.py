"""
Push Notifications API views.

  GET    /api/projects/{id}/push/tokens/                        — list device tokens
  POST   /api/projects/{id}/push/tokens/                        — register device token
  GET    /api/projects/{id}/push/tokens/{pk}/                   — token detail
  PUT    /api/projects/{id}/push/tokens/{pk}/                   — update token
  DELETE /api/projects/{id}/push/tokens/{pk}/                   — delete token
  POST   /api/projects/{id}/push/tokens/register/               — upsert device token
  POST   /api/projects/{id}/push/tokens/{pk}/unregister/        — deactivate token

  GET    /api/projects/{id}/push/topics/                        — list topics
  POST   /api/projects/{id}/push/topics/                        — create topic
  GET    /api/projects/{id}/push/topics/{pk}/                   — topic detail
  PUT    /api/projects/{id}/push/topics/{pk}/                   — update topic
  DELETE /api/projects/{id}/push/topics/{pk}/                   — delete topic
  POST   /api/projects/{id}/push/topics/{pk}/subscribe/         — subscribe device token to topic
  POST   /api/projects/{id}/push/topics/{pk}/unsubscribe/       — unsubscribe device token from topic

  GET    /api/projects/{id}/push/notifications/                 — list notifications
  POST   /api/projects/{id}/push/notifications/                 — create + queue notification
  GET    /api/projects/{id}/push/notifications/{pk}/            — notification detail

  GET    /api/projects/{id}/push/campaigns/                     — list campaigns
  POST   /api/projects/{id}/push/campaigns/                     — create campaign
  GET    /api/projects/{id}/push/campaigns/{pk}/                — campaign detail
  PUT    /api/projects/{id}/push/campaigns/{pk}/                — update campaign
  DELETE /api/projects/{id}/push/campaigns/{pk}/                — delete campaign
  POST   /api/projects/{id}/push/campaigns/{pk}/send/           — send campaign immediately
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Project, ProjectMembership
from .models import DeviceToken, Topic, TopicSubscription, PushNotification, NotificationCampaign
from .serializers import (
    DeviceTokenSerializer,
    TopicSerializer,
    TopicSubscriptionSerializer,
    PushNotificationSerializer,
    NotificationCampaignSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers (mirrors functions/views.py pattern)
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
# DeviceToken ViewSet
# ---------------------------------------------------------------------------

class DeviceTokenViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for device tokens.  Includes register/unregister convenience actions.
    """
    serializer_class = DeviceTokenSerializer
    _model = DeviceToken
    _write_requires_editor = False  # Any project member can register their device

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request, project_id=None):
        """
        Upsert a device token.  If the (project, platform, token) triple already
        exists the existing record is reactivated and updated; otherwise a new one
        is created.  Returns HTTP 200 on update, 201 on create.
        """
        project = self._project()
        ser = DeviceTokenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        token_obj, created = DeviceToken.objects.update_or_create(
            project=project,
            platform=d['platform'],
            token=d['token'],
            defaults={
                'user': request.user,
                'app_id': d.get('app_id', ''),
                'is_active': True,
            },
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(DeviceTokenSerializer(token_obj).data, status=response_status)

    @action(detail=True, methods=['post'], url_path='unregister')
    def unregister(self, request, pk=None, project_id=None):
        """Deactivate a device token so it no longer receives notifications."""
        project = self._project()
        token_obj = get_object_or_404(DeviceToken, pk=pk, project=project)
        token_obj.is_active = False
        token_obj.save(update_fields=['is_active', 'updated_at'])
        return Response({'detail': 'Token deactivated.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Topic ViewSet
# ---------------------------------------------------------------------------

class TopicViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for topics.  Includes subscribe/unsubscribe device-token actions.
    """
    serializer_class = TopicSerializer
    _model = Topic

    @action(detail=True, methods=['post'], url_path='subscribe')
    def subscribe(self, request, pk=None, project_id=None):
        """Subscribe a device token to this topic."""
        project = self._project()
        topic = get_object_or_404(Topic, pk=pk, project=project)

        device_token_id = request.data.get('device_token_id')
        if not device_token_id:
            return Response(
                {'error': 'device_token_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        device_token = get_object_or_404(DeviceToken, pk=device_token_id, project=project, is_active=True)

        # Members can only subscribe their own tokens; editors/owners may subscribe any.
        if device_token.user_id is not None and device_token.user_id != request.user.id:
            _get_project_and_membership(request, project.id, require_editor=True)

        subscription, created = TopicSubscription.objects.get_or_create(
            topic=topic,
            device_token=device_token,
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(TopicSubscriptionSerializer(subscription).data, status=response_status)

    @action(detail=True, methods=['post'], url_path='unsubscribe')
    def unsubscribe(self, request, pk=None, project_id=None):
        """Unsubscribe a device token from this topic."""
        project = self._project()
        topic = get_object_or_404(Topic, pk=pk, project=project)

        device_token_id = request.data.get('device_token_id')
        if not device_token_id:
            return Response(
                {'error': 'device_token_id is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        device_token = get_object_or_404(DeviceToken, pk=device_token_id, project=project)

        # Members can only unsubscribe their own tokens; editors/owners may unsubscribe any.
        if device_token.user_id is not None and device_token.user_id != request.user.id:
            _, membership = _get_project_and_membership(request, project.id)
            if membership.role not in ('owner', 'editor'):
                raise PermissionDenied('Editor role required to unsubscribe another user\'s token.')

        deleted, _ = TopicSubscription.objects.filter(
            topic=topic,
            device_token=device_token,
        ).delete()
        if not deleted:
            return Response(
                {'error': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'detail': 'Unsubscribed.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# PushNotification ViewSet
# ---------------------------------------------------------------------------

class PushNotificationViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    List/retrieve/create push notifications.  On create the notification is
    immediately queued via Celery.
    """
    serializer_class = PushNotificationSerializer
    _model = PushNotification
    http_method_names = ['get', 'post', 'head', 'options']  # No PUT/PATCH/DELETE

    def perform_create(self, serializer):
        project = self._project(require_editor=self._write_requires_editor)
        notification = serializer.save(project=project)
        # Queue delivery asynchronously
        try:
            from push.tasks import deliver_push_notification
            deliver_push_notification.delay(str(notification.id))
        except Exception as exc:
            logger.error(
                'Failed to enqueue deliver_push_notification for %s: %s',
                notification.id, exc,
            )


# ---------------------------------------------------------------------------
# NotificationCampaign ViewSet
# ---------------------------------------------------------------------------

class NotificationCampaignViewSet(_ProjectScopedMixin, viewsets.ModelViewSet):
    """
    CRUD for notification campaigns.  Includes a send action to fire immediately.
    """
    serializer_class = NotificationCampaignSerializer
    _model = NotificationCampaign

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None, project_id=None):
        """
        Fire a campaign immediately regardless of its scheduled_at time.
        The campaign must be in draft or scheduled status.
        """
        project = self._project(require_editor=True)
        campaign = get_object_or_404(NotificationCampaign, pk=pk, project=project)

        # Atomic compare-and-swap: only one concurrent request wins; the rest get 409.
        updated = NotificationCampaign.objects.filter(
            pk=campaign.pk,
            status__in=[NotificationCampaign.STATUS_DRAFT, NotificationCampaign.STATUS_SCHEDULED],
        ).update(status=NotificationCampaign.STATUS_SENDING)
        if not updated:
            return Response(
                {'error': 'Campaign already sending or sent.'},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            from push.tasks import send_campaign
            result = send_campaign.delay(str(campaign.id))
        except Exception as exc:
            logger.error('Failed to enqueue send_campaign for %s: %s', campaign.id, exc)
            return Response(
                {'error': 'Failed to queue campaign. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {'task_id': result.id, 'status': 'queued'},
            status=status.HTTP_202_ACCEPTED,
        )
