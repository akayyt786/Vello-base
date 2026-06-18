"""
Core models: multi-tenant projects, users, and base MultiTenant model for RLS.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Project(models.Model):
    """
    A project is the top-level multi-tenant container.
    Every row in every table carries a project_id for RLS isolation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    # Ownership & metadata
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='owned_projects')
    description = models.TextField(blank=True)

    # Config
    api_key = models.CharField(max_length=255, unique=True, db_index=True, editable=False)
    is_active = models.BooleanField(default=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_project'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = str(uuid.uuid4()).replace('-', '')
        super().save(*args, **kwargs)


class ProjectMembership(models.Model):
    """
    Membership of a user in a project with a specific role.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_project_membership'
        unique_together = [['project', 'user']]
        indexes = [
            models.Index(fields=['project', 'role']),
        ]

    def __str__(self):
        return f"{self.user.email} @ {self.project.slug} ({self.role})"


class MultiTenantModel(models.Model):
    """
    Abstract base model for all multi-tenant data.
    Every concrete model inheriting from this MUST include a foreign key to Project.
    RLS policies will filter by project_id at the database level.
    """
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        db_index=True,
        help_text="Multi-tenant isolation: every row belongs to a project"
    )

    # Optional: track which user created/updated the row (for audit + RLS refinements)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="User who created this row"
    )
    updated_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="User who last updated this row"
    )

    class Meta:
        abstract = True


class UserProfile(models.Model):
    """
    Extended user profile for OAuth, email verification, and sign-in provider tracking.
    """
    PROVIDER_CHOICES = [
        ('password', 'Email/Password'),
        ('google', 'Google'),
        ('github', 'GitHub'),
        ('anonymous', 'Anonymous'),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='profile')

    # Auth provider
    sign_in_provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default='password',
        db_index=True
    )

    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Phone
    phone_number = models.CharField(max_length=20, blank=True, db_index=True)
    phone_verified = models.BooleanField(default=False)

    # Profile metadata
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)

    # Custom claims (for JWT, serialized as JSON)
    custom_claims = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_user_profile'

    def __str__(self):
        return f"Profile of {self.user.email}"


class RefreshTokenBlacklist(models.Model):
    """
    Blacklist for refresh tokens on logout.
    Prevents token reuse after the user logs out.
    Works with rest_framework_simplejwt.token_blacklist.
    """
    jti = models.TextField(db_index=True, unique=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='blacklisted_tokens')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Token expiration time; after this, the entry can be pruned from the database"
    )

    class Meta:
        db_table = 'core_refresh_token_blacklist'
        indexes = [
            models.Index(fields=['jti']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Blacklisted token for {self.user.email}"
