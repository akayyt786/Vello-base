"""Models for App Check — client attestation tokens."""

import uuid
from django.db import models
from django.utils import timezone


class AppCheckConfig(models.Model):
    """App Check configuration for a project + platform."""

    PLATFORM_WEB = 'web'
    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS = 'ios'
    PLATFORM_CHOICES = [
        (PLATFORM_WEB, 'Web'),
        (PLATFORM_ANDROID, 'Android'),
        (PLATFORM_IOS, 'iOS'),
    ]

    PROVIDER_RECAPTCHA_V3 = 'recaptcha_v3'
    PROVIDER_RECAPTCHA_ENTERPRISE = 'recaptcha_enterprise'
    PROVIDER_PLAY_INTEGRITY = 'play_integrity'
    PROVIDER_DEVICE_CHECK = 'device_check'
    PROVIDER_DEBUG = 'debug'
    PROVIDER_CHOICES = [
        (PROVIDER_RECAPTCHA_V3, 'reCAPTCHA v3'),
        (PROVIDER_RECAPTCHA_ENTERPRISE, 'reCAPTCHA Enterprise'),
        (PROVIDER_PLAY_INTEGRITY, 'Play Integrity'),
        (PROVIDER_DEVICE_CHECK, 'DeviceCheck'),
        (PROVIDER_DEBUG, 'Debug (Development Only)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='app_check_configs',
    )
    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES)
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    config = models.JSONField(default=dict, help_text='Provider-specific config (site key, etc.)')
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('project', 'platform')]
        ordering = ['platform']

    def __str__(self):
        return f"AppCheck {self.project} [{self.platform}/{self.provider}]"


class AppCheckToken(models.Model):
    """A validated App Check token issued for a specific project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='app_check_tokens',
    )
    token_hash = models.CharField(max_length=64, unique=True)
    platform = models.CharField(max_length=10, choices=AppCheckConfig.PLATFORM_CHOICES)
    app_id = models.CharField(max_length=255, blank=True)
    is_revoked = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['project', 'token_hash']),
            models.Index(fields=['expires_at']),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_revoked and not self.is_expired()

    def __str__(self):
        return f"AppCheckToken {self.project} [{self.platform}] valid={self.is_valid()}"


class DebugToken(models.Model):
    """Debug tokens for development/CI — bypasses attestation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='debug_tokens',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=100, default='Debug Token')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"DebugToken {self.name} [{self.project}]"
