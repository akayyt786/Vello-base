"""
Analytics models: client events, user properties, and conversion event configuration.
Mirrors Firebase Analytics logEvent / setUserProperty APIs.
"""

import uuid
from django.db import models
from core.models import Project


class Event(models.Model):
    """
    A single analytics event logged by a client (mirrors Firebase Analytics logEvent).
    Stores arbitrary event_params as JSON alongside structured device/geo metadata.
    """

    PLATFORM_WEB = 'web'
    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS = 'ios'
    PLATFORM_SERVER = 'server'

    PLATFORM_CHOICES = [
        (PLATFORM_WEB, 'Web'),
        (PLATFORM_ANDROID, 'Android'),
        (PLATFORM_IOS, 'iOS'),
        (PLATFORM_SERVER, 'Server'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='analytics_events',
        db_index=True,
    )

    # Identity
    user_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text='Firebase UID or anonymous client-generated ID',
    )
    session_id = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
        help_text='Session identifier grouping related events',
    )

    # Event payload
    event_name = models.CharField(max_length=255, db_index=True)
    event_params = models.JSONField(
        default=dict,
        blank=True,
        help_text='Arbitrary key-value parameters attached to the event',
    )

    # Client context
    platform = models.CharField(
        max_length=32,
        choices=PLATFORM_CHOICES,
        default=PLATFORM_WEB,
        db_index=True,
    )
    app_version = models.CharField(max_length=64, blank=True)
    device_id = models.CharField(max_length=255, blank=True)

    # Geo (resolved server-side or passed by client)
    geo_country = models.CharField(max_length=2, blank=True, help_text='ISO 3166-1 alpha-2 country code')
    geo_city = models.CharField(max_length=128, blank=True)

    # Timestamps
    occurred_at = models.DateTimeField(
        db_index=True,
        help_text='Client-side event timestamp',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_event'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['project', 'event_name']),
            models.Index(fields=['project', 'user_id']),
            models.Index(fields=['project', 'occurred_at']),
            models.Index(fields=['project', 'session_id']),
        ]

    def __str__(self):
        return f"{self.event_name} @ {self.project.slug} [{self.occurred_at}]"


class UserProperty(models.Model):
    """
    A persistent per-user property (mirrors Firebase Analytics setUserProperty).
    Properties are keyed by (project, user_id, name) and upserted on write.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='analytics_user_properties',
        db_index=True,
    )
    user_id = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=64)
    value = models.CharField(max_length=256)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_user_property'
        unique_together = [['project', 'user_id', 'name']]

    def __str__(self):
        return f"{self.user_id}.{self.name}={self.value} ({self.project.slug})"


class ConversionEvent(models.Model):
    """
    Marks which event_names are tracked as conversion events for a project.
    Mirrors the Firebase Analytics conversion event configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='analytics_conversion_events',
        db_index=True,
    )
    event_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_conversion_event'
        unique_together = [['project', 'event_name']]

    def __str__(self):
        return f"conversion:{self.event_name} ({self.project.slug})"
