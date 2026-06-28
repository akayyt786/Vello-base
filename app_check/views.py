"""
App Check API views.

  GET    /api/projects/{id}/app-check/config/            — list App Check configs
  POST   /api/projects/{id}/app-check/config/            — create config (editor)
  PATCH  /api/projects/{id}/app-check/config/{pk}/       — update config (editor)
  DELETE /api/projects/{id}/app-check/config/{pk}/       — delete config (editor)
  POST   /api/projects/{id}/app-check/exchange/          — exchange raw token -> AppCheck token
  POST   /api/projects/{id}/app-check/verify/            — verify existing AppCheck token
  GET    /api/projects/{id}/app-check/tokens/            — list issued tokens (editor)
  POST   /api/projects/{id}/app-check/tokens/{pk}/revoke/ — revoke token (editor)
  GET    /api/projects/{id}/app-check/debug-tokens/      — list debug tokens (editor)
  POST   /api/projects/{id}/app-check/debug-tokens/      — create debug token (editor)
  DELETE /api/projects/{id}/app-check/debug-tokens/{pk}/ — delete debug token (editor)
"""

import logging

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Project, ProjectMembership
from .models import AppCheckConfig, AppCheckToken, DebugToken
from .serializers import (
    AppCheckConfigSerializer, AppCheckTokenSerializer,
    DebugTokenSerializer, ExchangeTokenSerializer,
)
from .services import exchange_debug_token, validate_app_check_token, hash_token

logger = logging.getLogger(__name__)


def _get_project(request, project_id, require_editor=False):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('Editor role required.')
    return project


class AppCheckConfigListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request, project_id)
        configs = AppCheckConfig.objects.filter(project=project)
        return Response(AppCheckConfigSerializer(configs, many=True).data)

    def post(self, request, project_id):
        project = _get_project(request, project_id, require_editor=True)
        ser = AppCheckConfigSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ser.save(project=project)
        except IntegrityError:
            return Response(
                {'error': 'App Check config for this platform already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ser.data, status=status.HTTP_201_CREATED)


class AppCheckConfigDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, project_id, pk):
        project = _get_project(request, project_id, require_editor=True)
        config = get_object_or_404(AppCheckConfig, pk=pk, project=project)
        ser = AppCheckConfigSerializer(config, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, project_id, pk):
        project = _get_project(request, project_id, require_editor=True)
        config = get_object_or_404(AppCheckConfig, pk=pk, project=project)
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExchangeTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = _get_project(request, project_id)
        ser = ExchangeTokenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        provider = ser.validated_data['provider']
        platform = ser.validated_data['platform']
        raw_token = ser.validated_data['raw_token']

        if provider == 'debug':
            token_obj, error = exchange_debug_token(project, raw_token, platform)
            if error:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
            return Response({
                'token': token_obj.token_hash,
                'expires_at': token_obj.expires_at.isoformat(),
            })

        # For production providers (reCAPTCHA, Play Integrity, DeviceCheck)
        # validate via external APIs — implementation depends on provider config
        config = AppCheckConfig.objects.filter(
            project=project, platform=platform, provider=provider, is_enabled=True
        ).first()
        if not config:
            return Response(
                {'error': 'App Check not configured for this platform/provider.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Placeholder: production validation would call provider API here
        # For now return error indicating provider integration needed
        return Response(
            {'error': f'Production provider "{provider}" requires server-side integration. Use debug provider for testing.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class VerifyTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = _get_project(request, project_id)
        token = request.data.get('token')
        if not token:
            return Response({'error': 'token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = hash_token(token)
        valid, error = validate_app_check_token(project, token_hash)
        return Response({'valid': valid, 'error': error})


class TokenListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request, project_id, require_editor=True)
        tokens = AppCheckToken.objects.filter(project=project).order_by('-issued_at')[:100]
        return Response(AppCheckTokenSerializer(tokens, many=True).data)


class RevokeTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, pk):
        project = _get_project(request, project_id, require_editor=True)
        token = get_object_or_404(AppCheckToken, pk=pk, project=project)
        token.is_revoked = True
        token.save(update_fields=['is_revoked'])
        return Response({'detail': 'Token revoked.'})


class DebugTokenListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request, project_id, require_editor=True)
        tokens = DebugToken.objects.filter(project=project)
        return Response(DebugTokenSerializer(tokens, many=True).data)

    def post(self, request, project_id):
        project = _get_project(request, project_id, require_editor=True)
        name = request.data.get('name', 'Debug Token')
        token = DebugToken.objects.create(project=project, name=name)
        return Response(DebugTokenSerializer(token).data, status=status.HTTP_201_CREATED)


class DebugTokenDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, project_id, pk):
        project = _get_project(request, project_id, require_editor=True)
        token = get_object_or_404(DebugToken, pk=pk, project=project)
        token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
