"""
AI Proxy API views.

  GET/POST/PATCH/DELETE  /api/projects/{id}/ai/providers/         — manage AI provider configs
  POST                   /api/projects/{id}/ai/chat/              — proxy chat completion
  POST                   /api/projects/{id}/ai/embeddings/        — proxy embeddings (OpenAI)
  GET                    /api/projects/{id}/ai/usage/             — usage log for project
"""

import logging

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Project, ProjectMembership
from .encryption import decrypt_api_key, encrypt_api_key
from .models import AIProviderConfig, AIUsageLog
from .serializers import (
    AIProviderConfigSerializer,
    AIUsageLogSerializer,
    ChatCompletionRequestSerializer,
    EmbeddingRequestSerializer,
)
from .services import call_anthropic, call_google, get_embeddings_openai

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helper (mirrors push/views.py pattern)
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
# AI Provider Config ViewSet
# ---------------------------------------------------------------------------

class AIProviderConfigViewSet(viewsets.ModelViewSet):
    serializer_class = AIProviderConfigSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        project, _ = _get_project_and_membership(self.request, self.kwargs['project_id'])
        return AIProviderConfig.objects.filter(project=project)

    def perform_create(self, serializer):
        project, _ = _get_project_and_membership(
            self.request, self.kwargs['project_id'], require_editor=True
        )
        plain_key = serializer.validated_data.pop('api_key')
        try:
            serializer.save(project=project, api_key_encrypted=encrypt_api_key(plain_key))
        except IntegrityError:
            raise ValidationError(
                {'provider': 'A configuration for this provider already exists in this project.'}
            )

    def perform_update(self, serializer):
        _get_project_and_membership(
            self.request, self.kwargs['project_id'], require_editor=True
        )
        plain_key = serializer.validated_data.pop('api_key', None)
        if plain_key:
            serializer.save(api_key_encrypted=encrypt_api_key(plain_key))
        else:
            serializer.save()

    def perform_destroy(self, instance):
        _get_project_and_membership(
            self.request, self.kwargs['project_id'], require_editor=True
        )
        instance.delete()


# ---------------------------------------------------------------------------
# Chat Completion View
# ---------------------------------------------------------------------------

class ChatCompletionView(APIView):
    """POST /api/projects/{id}/ai/chat/ — proxy to configured AI provider."""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        ser = ChatCompletionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        provider_cfg = AIProviderConfig.objects.filter(
            project=project, provider=d['provider'], is_active=True
        ).first()
        if not provider_cfg:
            return Response(
                {'error': f"No active {d['provider']} provider configured for this project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key = decrypt_api_key(provider_cfg.api_key_encrypted)
        messages = [{'role': m['role'], 'content': m['content']} for m in d['messages']]
        log_kwargs = dict(
            project=project,
            user=request.user,
            provider=d['provider'],
            model=d['model'],
        )

        try:
            if d['provider'] == 'anthropic':
                result = call_anthropic(
                    api_key, d['model'], messages,
                    d['max_tokens'], d['temperature'], d.get('system'),
                )
            elif d['provider'] == 'google':
                result = call_google(
                    api_key, d['model'], messages,
                    d['max_tokens'], d['temperature'], d.get('system'),
                )
            else:
                return Response(
                    {'error': 'Unsupported provider.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            AIUsageLog.objects.create(
                **log_kwargs,
                prompt_tokens=result['usage']['prompt_tokens'],
                completion_tokens=result['usage']['completion_tokens'],
                total_tokens=result['usage']['total_tokens'],
                latency_ms=result['latency_ms'],
                status='success',
            )
            return Response({
                'content': result['content'],
                'model': result['model'],
                'provider': result['provider'],
                'usage': result['usage'],
            })

        except Exception as exc:
            logger.exception('AI proxy error')
            AIUsageLog.objects.create(**log_kwargs, status='error', error_message=type(exc).__name__)
            return Response({'error': 'Upstream provider error.'}, status=status.HTTP_502_BAD_GATEWAY)


# ---------------------------------------------------------------------------
# Embedding View
# ---------------------------------------------------------------------------

class EmbeddingView(APIView):
    """POST /api/projects/{id}/ai/embeddings/ — get vector embeddings via OpenAI."""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        ser = EmbeddingRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        provider_cfg = AIProviderConfig.objects.filter(
            project=project, provider='openai', is_active=True
        ).first()
        if not provider_cfg:
            return Response(
                {'error': 'No active OpenAI provider configured.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key = decrypt_api_key(provider_cfg.api_key_encrypted)
        try:
            result = get_embeddings_openai(api_key, d['input'], d['model'])
            AIUsageLog.objects.create(
                project=project,
                user=request.user,
                provider='openai',
                model=d['model'],
                prompt_tokens=result['usage']['prompt_tokens'],
                total_tokens=result['usage']['total_tokens'],
                latency_ms=result['latency_ms'],
                status='success',
            )
            return Response({
                'embeddings': result['embeddings'],
                'model': result['model'],
                'usage': result['usage'],
            })

        except Exception as exc:
            logger.exception('Embedding error')
            return Response({'error': 'Upstream provider error.'}, status=status.HTTP_502_BAD_GATEWAY)


# ---------------------------------------------------------------------------
# AI Usage View
# ---------------------------------------------------------------------------

class AIUsageView(APIView):
    """GET /api/projects/{id}/ai/usage/ — usage stats for project."""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id=None):
        project, _ = _get_project_and_membership(request, project_id)
        logs = AIUsageLog.objects.filter(project=project).order_by('-created_at')[:100]
        return Response(AIUsageLogSerializer(logs, many=True).data)
