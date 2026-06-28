import uuid
from django.db import models

WEBHOOK_EVENTS = [
    ('data.created', 'Data Document Created'),
    ('data.updated', 'Data Document Updated'),
    ('data.deleted', 'Data Document Deleted'),
    ('auth.registered', 'User Registered'),
    ('auth.login', 'User Login'),
    ('function.invoked', 'Function Invoked'),
    ('push.sent', 'Push Notification Sent'),
]


class WebhookEndpoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='webhook_endpoints')
    url = models.URLField(max_length=500)
    secret = models.CharField(max_length=128, help_text="HMAC-SHA256 signing secret")
    events = models.JSONField(default=list, help_text="List of event types to subscribe to")
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.project} → {self.url}"


class WebhookDelivery(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=64)
    payload = models.JSONField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    response_status = models.IntegerField(null=True)
    response_body = models.TextField(blank=True)
    latency_ms = models.IntegerField(null=True)
    attempt_count = models.IntegerField(default=0)
    delivered_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['endpoint', 'status'])]
