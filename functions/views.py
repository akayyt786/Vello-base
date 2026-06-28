"""
Cloud Functions API views.

  GET    /api/projects/{id}/functions/               — list functions
  POST   /api/projects/{id}/functions/               — create function
  GET    /api/projects/{id}/functions/{name}/        — function detail
  PUT    /api/projects/{id}/functions/{name}/        — update function
  DELETE /api/projects/{id}/functions/{name}/        — delete function
  POST   /api/projects/{id}/functions/{name}/invoke/ — HTTP invoke
  GET    /api/projects/{id}/functions/{name}/logs/   — execution logs
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from core.models import Project, ProjectMembership
from .models import CloudFunction, FunctionLog
from .serializers import CloudFunctionSerializer, FunctionLogSerializer, InvokeSerializer

logger = logging.getLogger(__name__)


def _get_project_and_membership(request, project_id, require_editor=False):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if require_editor and membership.role not in ('owner', 'editor'):
        return project, membership, Response({'error': 'Editor role required'}, status=status.HTTP_403_FORBIDDEN)
    return project, membership, None


MAX_FUNCTIONS_PER_PROJECT = 100


class FunctionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project, _, err = _get_project_and_membership(request, project_id)
        if err:
            return err
        qs = CloudFunction.objects.filter(project=project)
        trigger = request.query_params.get('trigger_type')
        if trigger:
            qs = qs.filter(trigger_type=trigger)
        limit = min(int(request.query_params.get('limit', 50)), 200)
        offset = int(request.query_params.get('offset', 0))
        total = qs.count()
        return Response({
            'functions': CloudFunctionSerializer(qs[offset:offset + limit], many=True).data,
            'total': total,
            'limit': limit,
            'offset': offset,
        })

    def post(self, request, project_id):
        project, _, err = _get_project_and_membership(request, project_id, require_editor=True)
        if err:
            return err
        existing_count = CloudFunction.objects.filter(project=project).count()
        if existing_count >= MAX_FUNCTIONS_PER_PROJECT:
            return Response(
                {'error': f'Function limit reached ({MAX_FUNCTIONS_PER_PROJECT} per project).'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        ser = CloudFunctionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        fn = ser.save(project=project, created_by=request.user, updated_by=request.user)
        return Response(CloudFunctionSerializer(fn).data, status=status.HTTP_201_CREATED)


class FunctionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_fn(self, project, name):
        return get_object_or_404(CloudFunction, project=project, name=name)

    def get(self, request, project_id, name):
        project, _, err = _get_project_and_membership(request, project_id)
        if err:
            return err
        return Response(CloudFunctionSerializer(self._get_fn(project, name)).data)

    def put(self, request, project_id, name):
        project, _, err = _get_project_and_membership(request, project_id, require_editor=True)
        if err:
            return err
        fn = self._get_fn(project, name)
        ser = CloudFunctionSerializer(fn, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        fn = ser.save(updated_by=request.user)
        return Response(CloudFunctionSerializer(fn).data)

    def delete(self, request, project_id, name):
        project, _, err = _get_project_and_membership(request, project_id, require_editor=True)
        if err:
            return err
        self._get_fn(project, name).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FunctionInvokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, name):
        # Invoke requires editor+ — viewers must not be able to trigger webhook calls.
        project, _, err = _get_project_and_membership(request, project_id, require_editor=True)
        if err:
            return err
        fn = get_object_or_404(
            CloudFunction, project=project, name=name,
            trigger_type=CloudFunction.TRIGGER_HTTP, is_enabled=True,
        )
        ser = InvokeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        from functions.tasks import invoke_function_for_event
        result = invoke_function_for_event.delay(str(fn.id), {
            'event': 'http',
            'invoker_user_id': str(request.user.id),
            'data': ser.validated_data.get('data', {}),
        })
        return Response({'task_id': result.id, 'status': 'queued'}, status=status.HTTP_202_ACCEPTED)


class FunctionLogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, name):
        project, _, err = _get_project_and_membership(request, project_id)
        if err:
            return err
        fn = get_object_or_404(CloudFunction, project=project, name=name)
        limit = min(int(request.query_params.get('limit', 50)), 200)
        logs = fn.logs.all()[:limit]
        return Response({'logs': FunctionLogSerializer(logs, many=True).data})
