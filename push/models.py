"""
Push Notifications models: device tokens, topics, notifications, and campaigns.
Supports FCM (Android/Web), APNs (iOS/macOS), and Web Push protocols.
"""

import uuid
from django.db import models
from django.conf import settings
from core.models import Project


class DeviceToken(models.Model):
    """A registered push notification endpoint for a specific device and platform."""

    PLATFORM_FCM = 'fcm'
    PLATFORM_APNS = 'apns'
    PLATFORM_WEB = 'web'

    PLATFORM_CHOICES = [
        (PLATFORM_FCM, 'FCM (Firebase Cloud Messaging)'),
        (PLATFORM_APNS, 'APNs (Apple Push Notification service)'),
        (PLATFORM_WEB, 'Web Push'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_tokens',
        help_text='Optional: associate this token with an authenticated user',
    )
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, db_index=True)
    token = models.TextField(help_text='FCM registration token, APNs device token, or Web Push subscription JSON')
    app_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='Application identifier (bundle ID for APNs, sender ID for FCM)',
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'push_device_token'
        ordering = ['-created_at']
        unique_together = [['project', 'platform', 'token']]
        indexes = [
            models.Index(fields=['project', 'platform', 'is_active']),
            models.Index(fields=['project', 'user']),
        ]

    def __str__(self):
        return f"{self.platform}:{self.token[:20]}… ({self.project.slug})"


class Topic(models.Model):
    """A named topic that device tokens can subscribe to for group notifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='push_topics',
        db_index=True,
    )
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'push_topic'
        ordering = ['name']
        unique_together = [['project', 'name']]
        indexes = [
            models.Index(fields=['project', 'name']),
        ]

    def __str__(self):
        return f"{self.project.slug}/{self.name}"


class TopicSubscription(models.Model):
    """Links a device token to a topic."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    device_token = models.ForeignKey(
        DeviceToken,
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'push_topic_subscription'
        ordering = ['-created_at']
        unique_together = [['topic', 'device_token']]
        indexes = [
            models.Index(fields=['topic', 'device_token']),
        ]

    def __str__(self):
        return f"{self.device_token.platform}:{self.device_token.token[:12]}… → {self.topic.name}"


class PushNotification(models.Model):
    """A single push notification sent to one device token or topic."""

    STATUS_PENDING = 'pending'
    STATUS_QUEUED = 'queued'
    STATUS_DELIVERED = 'delivered'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_QUEUED, 'Queued'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='push_notifications',
        db_index=True,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Arbitrary key-value payload attached to the notification',
    )
    image_url = models.URLField(blank=True, help_text='Optional image shown in the notification')

    # Targeting — exactly one of device_token or topic should be set
    device_token = models.ForeignKey(
        DeviceToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Send to a specific device token',
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Send to all subscribers of this topic',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    error = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'push_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'created_at']),
        ]

    def __str__(self):
        target = self.device_token_id or f"topic:{self.topic_id}"
        return f"{self.title} → {target} [{self.status}]"


class NotificationCampaign(models.Model):
    """A broadcast campaign that sends a notification to many device tokens at once."""

    STATUS_DRAFT = 'draft'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_SENDING = 'sending'
    STATUS_SENT = 'sent'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_SENDING, 'Sending'),
        (STATUS_SENT, 'Sent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='notification_campaigns',
        db_index=True,
    )
    name = models.CharField(max_length=255, help_text='Internal campaign name')
    title = models.CharField(max_length=255, help_text='Notification title shown to users')
    body = models.TextField(help_text='Notification body shown to users')
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Arbitrary key-value payload attached to each notification',
    )
    image_url = models.URLField(blank=True)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        help_text='If set, send only to subscribers of this topic',
    )
    target_platforms = models.JSONField(
        default=list,
        help_text='List of platforms to target, e.g. ["fcm", "apns", "web"]. Empty means all.',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text='When to send (future scheduling)')
    sent_at = models.DateTimeField(null=True, blank=True)
    total_sent = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'push_campaign'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'scheduled_at']),
        ]

    def __str__(self):
        return f"{self.name} [{self.status}] ({self.project.slug})"
