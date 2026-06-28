"""Models for enhanced authentication: Phone OTP, MFA, Magic Links, Custom Tokens."""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class PhoneVerification(models.Model):
    """OTP sent to a phone number for authentication or phone linking."""

    STATUS_PENDING = 'pending'
    STATUS_VERIFIED = 'verified'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='phone_verifications',
    )
    phone_number = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=64)  # stores SHA-256 hex digest
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_number', 'status']),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.phone_number} [{self.status}]"


class MFADevice(models.Model):
    """A registered MFA device (TOTP app or SMS number) for a user."""

    METHOD_TOTP = 'totp'
    METHOD_SMS = 'sms'
    METHOD_CHOICES = [
        (METHOD_TOTP, 'TOTP (Authenticator App)'),
        (METHOD_SMS, 'SMS'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mfa_devices',
    )
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    name = models.CharField(max_length=100, default='My Device')
    totp_secret = models.CharField(max_length=64, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    # Tracks the most recent TOTP counter used — prevents replay attacks.
    last_used_counter = models.IntegerField(default=-1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} MFA [{self.method}] active={self.is_active}"


class MFASMSCode(models.Model):
    """Temporary SMS code for MFA verification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(MFADevice, on_delete=models.CASCADE, related_name='sms_codes')
    code = models.CharField(max_length=64)  # stores SHA-256 hex digest
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        return timezone.now() > self.expires_at


class MagicLink(models.Model):
    """Passwordless email login link."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='magic_links',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    redirect_url = models.URLField(blank=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"MagicLink for {self.user} used={self.is_used}"


class CustomToken(models.Model):
    """Custom JWT token issued server-side for a specific user/project."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='custom_tokens',
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='issued_custom_tokens',
    )
    uid = models.CharField(max_length=255)
    claims = models.JSONField(default=dict)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['project', 'uid'])]

    def is_expired(self):
        return timezone.now() > self.expires_at
