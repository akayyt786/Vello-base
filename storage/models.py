"""
StorageFile model: Firebase Storage equivalent.
Tracks file uploads to MinIO/S3 with lifecycle states.
"""

import uuid
from django.db import models
from core.models import MultiTenantModel


class StorageFile(MultiTenantModel):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_PROCESSING = 'processing'
    STATUS_READY = 'ready'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending upload'),
        (STATUS_CONFIRMED, 'Upload confirmed'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_READY, 'Ready'),
        (STATUS_ERROR, 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.CharField(max_length=255, db_index=True)
    path = models.TextField(db_index=True)
    original_name = models.CharField(max_length=512)
    content_type = models.CharField(max_length=255, default='application/octet-stream')
    size = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    thumbnails = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'storage_file'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'content_type']),
        ]

    def __str__(self):
        return f"{self.project.slug}/{self.path}"

    @property
    def is_image(self):
        return self.content_type.startswith('image/')

    @property
    def extension(self):
        return self.path.rsplit('.', 1)[-1].lower() if '.' in self.path else ''
