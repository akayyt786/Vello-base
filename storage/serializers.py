"""Serializers for Cloud Storage API."""

from rest_framework import serializers
from .models import StorageFile


class StorageFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = StorageFile
        fields = [
            'id', 'path', 'original_name', 'content_type', 'size',
            'status', 'metadata', 'thumbnails', 'download_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'thumbnails', 'created_at', 'updated_at']

    def get_download_url(self, obj):
        if obj.status not in ('confirmed', 'ready'):
            return None
        try:
            from storage.s3 import presigned_download_url
            return presigned_download_url(obj.bucket, obj.path)
        except Exception:
            return None


class UploadRequestSerializer(serializers.Serializer):
    path = serializers.CharField(max_length=1024)
    content_type = serializers.CharField(max_length=255, default='application/octet-stream')
    size = serializers.IntegerField(min_value=1, max_value=100 * 1024 * 1024, required=False)
    metadata = serializers.DictField(required=False, default=dict)


class ConfirmUploadSerializer(serializers.Serializer):
    file_id = serializers.UUIDField()
