"""
Cloud Functions models: function definitions and execution logs.
Functions are webhook-based: code runs on developer's server, Own Firebase routes triggers.
"""

import uuid
from django.db import models
from core.models import MultiTenantModel


class CloudFunction(MultiTenantModel):
    TRIGGER_HTTP = 'http'
    TRIGGER_ON_CREATE = 'on_create'
    TRIGGER_ON_UPDATE = 'on_update'
    TRIGGER_ON_DELETE = 'on_delete'
    TRIGGER_SCHEDULED = 'scheduled'
    TRIGGER_ON_STORAGE = 'on_storage'
    TRIGGER_ON_AUTH = 'on_auth'

    TRIGGER_CHOICES = [
        (TRIGGER_HTTP, 'HTTP (callable via REST)'),
        (TRIGGER_ON_CREATE, 'Document Created'),
        (TRIGGER_ON_UPDATE, 'Document Updated'),
        (TRIGGER_ON_DELETE, 'Document Deleted'),
        (TRIGGER_SCHEDULED, 'Scheduled (cron)'),
        (TRIGGER_ON_STORAGE, 'Storage Object Event'),
        (TRIGGER_ON_AUTH, 'Auth Event'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_CHOICES, db_index=True)
    collection_path = models.TextField(blank=True, help_text='For document triggers: collection to watch')
    endpoint_url = models.URLField(max_length=2048, help_text='Webhook URL to POST trigger payload to')
    schedule = models.CharField(max_length=100, blank=True, help_text='Cron expression for scheduled triggers')
    is_enabled = models.BooleanField(default=True, db_index=True)
    timeout_seconds = models.IntegerField(default=30)
    retry_count = models.IntegerField(default=0)
    secret_header = models.CharField(max_length=255, blank=True,
                                     help_text='X-OwnFirebase-Secret header value for webhook auth')
    extra_headers = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'functions_cloudfunction'
        ordering = ['name']
        indexes = [
            models.Index(fields=['project', 'trigger_type']),
            models.Index(fields=['project', 'trigger_type', 'collection_path']),
        ]

    def __str__(self):
        return f"{self.project.slug}/{self.name}"


class FunctionLog(models.Model):
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_ERROR = 'error'
    STATUS_TIMEOUT = 'timeout'

    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_ERROR, 'Error'),
        (STATUS_TIMEOUT, 'Timeout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    function = models.ForeignKey(CloudFunction, on_delete=models.CASCADE, related_name='logs')
    trigger_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING, db_index=True)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'functions_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['function', 'status']),
            models.Index(fields=['function', 'created_at']),
        ]
