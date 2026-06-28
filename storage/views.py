"""
Cloud Storage API views.

  POST /api/projects/{id}/storage/upload-url/     — presigned PUT URL
  POST /api/projects/{id}/storage/confirm/        — confirm upload done
  GET  /api/projects/{id}/storage/files/          — list files
  GET  /api/projects/{id}/storage/files/<path>/   — file detail + download URL
  DELETE /api/projects/{id}/storage/files/<path>/ — delete file
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from core.models import Project, ProjectMembership
from .models import StorageFile
from .serializers import StorageFileSerializer, UploadRequestSerializer, ConfirmUploadSerializer
from .s3 import get_bucket_name, ensure_bucket, presigned_upload_url, get_object_metadata

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

logger = logging.getLogger(__name__)


def _get_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    get_object_or_404(ProjectMembership, project=project, user=request.user)
    return project


def _require_editor(request, project_id):
    project = get_object_or_404(Project, id=project_id, is_active=True)
    membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
    if membership.role not in ('owner', 'editor'):
        return None, Response({'error': 'Editor role required'}, status=status.HTTP_403_FORBIDDEN)
    return project, None


class UploadUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project, err = _require_editor(request, project_id)
        if err:
            return err

        ser = UploadRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # Validate file size if the client declares it (via 'size' or 'content_length').
        declared_size = d.get('size') or request.data.get('content_length')
        if declared_size is not None:
            try:
                declared_size = int(declared_size)
            except (TypeError, ValueError):
                declared_size = None
        if declared_size is not None and declared_size > MAX_FILE_SIZE:
            return Response(
                {'error': f'File size exceeds the {MAX_FILE_SIZE // (1024 * 1024)} MB limit.'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        bucket = get_bucket_name(project.slug)
        try:
            ensure_bucket(bucket)
        except Exception as e:
            logger.error(f'ensure_bucket failed: {e}')
            return Response({'error': 'Storage backend unavailable'}, status=503)

        file_obj, _ = StorageFile.objects.get_or_create(
            project=project,
            path=d['path'],
            defaults={
                'bucket': bucket,
                'original_name': d['path'].split('/')[-1],
                'content_type': d['content_type'],
                'size': d.get('size'),
                'metadata': d.get('metadata', {}),
                'status': StorageFile.STATUS_PENDING,
                'created_by': request.user,
                'updated_by': request.user,
            }
        )

        try:
            upload_info = presigned_upload_url(bucket, d['path'], d['content_type'])
        except Exception as e:
            logger.error(f'presigned_upload_url failed: {e}')
            return Response({'error': 'Could not generate upload URL'}, status=503)

        return Response({
            'file_id': str(file_obj.id),
            'upload_url': upload_info['url'],
            'method': upload_info['method'],
            'expires_in': upload_info['expires_in'],
            'path': file_obj.path,
            'bucket': bucket,
        }, status=status.HTTP_201_CREATED)


class ConfirmUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project, err = _require_editor(request, project_id)
        if err:
            return err

        ser = ConfirmUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        file_obj = get_object_or_404(StorageFile, id=ser.validated_data['file_id'], project=project)

        # Idempotent: already confirmed (or further along in lifecycle) — return existing data.
        if file_obj.status in (StorageFile.STATUS_CONFIRMED, StorageFile.STATUS_PROCESSING,
                               StorageFile.STATUS_READY):
            return Response(StorageFileSerializer(file_obj).data, status=status.HTTP_200_OK)

        meta = get_object_metadata(file_obj.bucket, file_obj.path)
        file_obj.size = meta.get('size', file_obj.size)
        file_obj.status = StorageFile.STATUS_CONFIRMED
        file_obj.updated_by = request.user
        file_obj.save(update_fields=['size', 'status', 'updated_by', 'updated_at'])

        return Response(StorageFileSerializer(file_obj).data, status=status.HTTP_200_OK)


class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(request, project_id)
        qs = StorageFile.objects.filter(project=project)
        prefix = request.query_params.get('prefix', '')
        if prefix:
            qs = qs.filter(path__startswith=prefix)
        limit = min(int(request.query_params.get('limit', 50)), 200)
        offset = int(request.query_params.get('offset', 0))
        total = qs.count()
        return Response({
            'files': StorageFileSerializer(qs[offset:offset + limit], many=True).data,
            'total': total,
            'limit': limit,
            'offset': offset,
        })


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, path):
        project = _get_project(request, project_id)
        file_obj = get_object_or_404(StorageFile, project=project, path=path)
        return Response(StorageFileSerializer(file_obj).data)

    def delete(self, request, project_id, path):
        project, err = _require_editor(request, project_id)
        if err:
            return err
        file_obj = get_object_or_404(StorageFile, project=project, path=path)
        file_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
