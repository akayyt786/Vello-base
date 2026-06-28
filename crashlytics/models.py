"""
Crashlytics models: crash reports, error grouping, breadcrumbs, and performance traces.
Mirrors Firebase Crashlytics + Firebase Performance Monitoring.
"""

import uuid
from django.db import models

from core.models import Project


PLATFORM_CHOICES_CRASH = [
    ('android', 'Android'),
    ('ios', 'iOS'),
    ('web', 'Web'),
    ('flutter', 'Flutter'),
]

PLATFORM_CHOICES_PERF = [
    ('android', 'Android'),
    ('ios', 'iOS'),
    ('web', 'Web'),
]


class CrashGroup(models.Model):
    """
    Deduplicated crash signature — Firebase calls this an "Issue".
    Multiple CrashReport occurrences sharing the same fingerprint collapse here.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        db_index=True,
        related_name='crash_groups',
    )
    # sha256 truncated fingerprint of exception_type + top stack frame
    signature = models.CharField(max_length=512, db_index=True)
    # Human-readable summary, e.g. "NullPointerException in MainActivity.java:42"
    title = models.CharField(max_length=512)
    exception_type = models.CharField(max_length=255)

    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(db_index=True)

    occurrence_count = models.PositiveIntegerField(default=0)
    affected_users_count = models.PositiveIntegerField(default=0)

    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'crashlytics_crash_group'
        unique_together = [['project', 'signature']]
        indexes = [
            models.Index(fields=['project', 'is_resolved'], name='crash_grp_proj_resolved_idx'),
            models.Index(fields=['project', 'last_seen_at'], name='crash_grp_proj_last_seen_idx'),
        ]
        ordering = ['-last_seen_at']

    def __str__(self):
        return f"{self.title} [{self.project.slug}]"


class CrashReport(models.Model):
    """
    Individual crash occurrence, linked (after grouping) to a CrashGroup.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        db_index=True,
        related_name='crash_reports',
    )
    group = models.ForeignKey(
        CrashGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
    )

    user_id = models.CharField(max_length=255, blank=True, db_index=True)
    session_id = models.CharField(max_length=128, blank=True)

    platform = models.CharField(
        max_length=16,
        choices=PLATFORM_CHOICES_CRASH,
        default='android',
    )
    app_version = models.CharField(max_length=64, blank=True)
    os_version = models.CharField(max_length=64, blank=True)
    device_model = models.CharField(max_length=128, blank=True)

    exception_type = models.CharField(max_length=255)
    exception_message = models.TextField(blank=True)
    stack_trace = models.TextField()

    # False = non-fatal (handled exception)
    fatal = models.BooleanField(default=True)

    # Ordered list of {timestamp, category, message, data}
    breadcrumbs = models.JSONField(default=list)
    custom_keys = models.JSONField(default=dict)

    occurred_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crashlytics_crash_report'
        indexes = [
            models.Index(fields=['project', 'occurred_at'], name='crash_rpt_proj_occurred_idx'),
            models.Index(fields=['project', 'user_id'], name='crash_rpt_proj_user_idx'),
            models.Index(fields=['project', 'app_version'], name='crash_rpt_proj_version_idx'),
        ]
        ordering = ['-occurred_at']

    def __str__(self):
        return f"{self.exception_type} @ {self.occurred_at} [{self.project.slug}]"


class PerformanceTrace(models.Model):
    """
    Client-side performance measurement — mirrors Firebase Performance custom traces.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        db_index=True,
        related_name='performance_traces',
    )
    trace_name = models.CharField(max_length=255, db_index=True)
    duration_ms = models.PositiveIntegerField()

    user_id = models.CharField(max_length=255, blank=True)
    session_id = models.CharField(max_length=128, blank=True)

    platform = models.CharField(
        max_length=16,
        choices=PLATFORM_CHOICES_PERF,
        default='web',
    )
    app_version = models.CharField(max_length=64, blank=True)

    custom_attributes = models.JSONField(default=dict)
    # {metric_name: value}
    custom_metrics = models.JSONField(default=dict)

    occurred_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crashlytics_perf_trace'
        indexes = [
            models.Index(fields=['project', 'trace_name'], name='perf_trace_proj_name_idx'),
            models.Index(fields=['project', 'occurred_at'], name='perf_trace_proj_occurred_idx'),
        ]
        ordering = ['-occurred_at']

    def __str__(self):
        return f"{self.trace_name} ({self.duration_ms}ms) [{self.project.slug}]"


class NetworkRequest(models.Model):
    """
    HTTP network request performance — mirrors Firebase Performance network monitoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        db_index=True,
        related_name='network_requests',
    )
    HTTP_METHOD_CHOICES = [(m, m) for m in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")]

    url = models.CharField(max_length=2048)
    http_method = models.CharField(max_length=8, choices=HTTP_METHOD_CHOICES)
    response_code = models.PositiveSmallIntegerField(null=True, blank=True)

    request_size_bytes = models.PositiveBigIntegerField(default=0)
    response_size_bytes = models.PositiveBigIntegerField(default=0)
    duration_ms = models.PositiveIntegerField()

    user_id = models.CharField(max_length=255, blank=True)
    session_id = models.CharField(max_length=128, blank=True)

    platform = models.CharField(
        max_length=16,
        choices=PLATFORM_CHOICES_PERF,
        default='web',
    )
    app_version = models.CharField(max_length=64, blank=True)

    occurred_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'crashlytics_network_request'
        indexes = [
            models.Index(fields=['project', 'occurred_at'], name='net_req_proj_occurred_idx'),
            models.Index(fields=['project', 'response_code'], name='net_req_proj_resp_code_idx'),
        ]
        ordering = ['-occurred_at']

    def __str__(self):
        return f"{self.http_method} {self.url[:80]} ({self.response_code}) [{self.project.slug}]"
