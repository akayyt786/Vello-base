"""
A/B Testing models.

Experiment      — defines the test (name, status, targeting key)
ExperimentVariant  — one bucket within an experiment (control, variant_a, …)
ExperimentAssignment — sticky mapping: targeting_value → variant (created once, reused forever)
ExperimentConversion — conversion events recorded against an assignment
"""

import uuid

from django.db import models

from core.models import Project


class Experiment(models.Model):
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('running',   'Running'),
        ('paused',    'Paused'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='abtesting_experiments',
        db_index=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
    )
    targeting_key = models.CharField(
        max_length=64,
        default='user_id',
        help_text='Field used for deterministic assignment: user_id, session_id, device_id',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'abtesting_experiment'
        unique_together = [('project', 'name')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.status}] ({self.project.slug})"


class ExperimentVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='variants',
    )
    name = models.CharField(
        max_length=64,
        help_text='e.g. "control", "variant_a"',
    )
    description = models.TextField(blank=True)
    allocation = models.IntegerField(
        default=50,
        help_text='Percentage 0-100; all variants in an experiment must sum to 100',
    )
    config = models.JSONField(
        default=dict,
        help_text='Variant-specific config values exposed to the client',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abtesting_experiment_variant'
        unique_together = [('experiment', 'name')]
        ordering = ['name']

    def __str__(self):
        return f"{self.experiment.name} / {self.name} ({self.allocation}%)"


class ExperimentAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    targeting_value = models.CharField(
        max_length=256,
        help_text='The actual user_id / session_id / device_id value',
    )
    variant = models.ForeignKey(
        ExperimentVariant,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abtesting_experiment_assignment'
        unique_together = [('experiment', 'targeting_value')]
        indexes = [
            models.Index(fields=['experiment', 'variant']),
        ]

    def __str__(self):
        return f"{self.targeting_value} → {self.variant.name} ({self.experiment.name})"


class ExperimentConversion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        ExperimentAssignment,
        on_delete=models.CASCADE,
        related_name='conversions',
    )
    event_name = models.CharField(max_length=128)
    value = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'abtesting_experiment_conversion'
        indexes = [
            models.Index(fields=['assignment', 'event_name']),
        ]

    def __str__(self):
        return f"{self.event_name} @ {self.assignment}"
