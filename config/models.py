"""
Remote Config models.

Mirrors Firebase Remote Config:
  - RemoteConfig: a key-value parameter with optional conditional overrides
  - ConfigCondition: conditional value override for a parameter
  - ConfigVersion: snapshot of all params at a point in time (publish history)

A/B testing (Experiment/ExperimentVariant) used to live here too, but was a
duplicate of the dedicated abtesting app (which SDKs actually use, and which
additionally tracks assignment/conversion) -- see abtesting/models.py.
"""

import uuid
from django.db import models


class RemoteConfig(models.Model):
    """
    A Remote Config parameter (key + typed value + optional conditions).
    Each parameter belongs to a project and has a unique key within that project.
    """
    VALUE_TYPE_STRING = 'string'
    VALUE_TYPE_NUMBER = 'number'
    VALUE_TYPE_BOOLEAN = 'boolean'
    VALUE_TYPE_JSON = 'json'

    VALUE_TYPE_CHOICES = [
        (VALUE_TYPE_STRING, 'String'),
        (VALUE_TYPE_NUMBER, 'Number'),
        (VALUE_TYPE_BOOLEAN, 'Boolean'),
        (VALUE_TYPE_JSON, 'JSON'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='remote_configs',
        db_index=True,
    )
    key = models.CharField(max_length=255, db_index=True)
    value_type = models.CharField(
        max_length=16,
        choices=VALUE_TYPE_CHOICES,
        default=VALUE_TYPE_STRING,
    )
    default_value = models.TextField(blank=True)
    description = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    is_secret = models.BooleanField(
        default=False,
        help_text='If True, default_value is treated as a secret and masked in list responses.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'remoteconfig_parameter'
        unique_together = [['project', 'key']]
        ordering = ['key']

    def __str__(self):
        return f"{self.key} ({self.value_type}) @ {self.project_id}"


class ConfigCondition(models.Model):
    """
    A conditional override for a RemoteConfig parameter.
    Conditions are evaluated in priority order (highest priority first).
    The first matching condition's value is used; if none match, default_value is used.
    """
    CONDITION_TYPE_USER_PROPERTY = 'user_property'
    CONDITION_TYPE_PLATFORM = 'platform'
    CONDITION_TYPE_APP_VERSION = 'app_version'
    CONDITION_TYPE_PERCENTAGE = 'percentage'
    CONDITION_TYPE_ALWAYS = 'always'

    CONDITION_TYPE_CHOICES = [
        (CONDITION_TYPE_USER_PROPERTY, 'User Property'),
        (CONDITION_TYPE_PLATFORM, 'Platform'),
        (CONDITION_TYPE_APP_VERSION, 'App Version'),
        (CONDITION_TYPE_PERCENTAGE, 'Percentage'),
        (CONDITION_TYPE_ALWAYS, 'Always'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(
        RemoteConfig,
        on_delete=models.CASCADE,
        related_name='conditions',
    )
    name = models.CharField(max_length=255)
    condition_type = models.CharField(
        max_length=32,
        choices=CONDITION_TYPE_CHOICES,
        default=CONDITION_TYPE_ALWAYS,
    )
    condition_params = models.JSONField(
        default=dict,
        help_text='Condition parameters, e.g. {"property_name": "plan", "property_value": "pro"}',
    )
    value = models.TextField()
    priority = models.IntegerField(
        default=0,
        help_text='Higher value = evaluated first',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'remoteconfig_condition'
        ordering = ['-priority', 'created_at']

    def __str__(self):
        return f"{self.name} ({self.condition_type}) → {self.value[:50]}"


class ConfigVersion(models.Model):
    """
    A published snapshot of all Remote Config parameters for a project.
    Each publish operation increments the version number and records the full state.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
        related_name='config_versions',
        db_index=True,
    )
    version_number = models.PositiveIntegerField()
    params = models.JSONField(
        help_text='Full snapshot of all config parameters at publish time: {key: value}',
    )
    description = models.CharField(max_length=500, blank=True)
    published_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='published_config_versions',
    )
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'remoteconfig_version'
        unique_together = [['project', 'version_number']]
        ordering = ['-version_number']

    def __str__(self):
        return f"v{self.version_number} @ {self.project_id}"
