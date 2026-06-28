"""Serializers for the Crashlytics API."""

from rest_framework import serializers

from .models import CrashGroup, CrashReport, PerformanceTrace, NetworkRequest


class CrashGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrashGroup
        fields = [
            'id', 'project', 'signature', 'title', 'exception_type',
            'first_seen_at', 'last_seen_at',
            'occurrence_count', 'affected_users_count',
            'is_resolved', 'resolved_at',
            'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'project', 'signature', 'title', 'exception_type',
            'first_seen_at', 'last_seen_at',
            'occurrence_count', 'affected_users_count',
            'resolved_at',
            'created_at', 'updated_at',
        ]
        # is_resolved and notes are writable by editors (PATCH to resolve/add notes)


class CrashReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrashReport
        fields = [
            'id', 'project', 'group',
            'user_id', 'session_id',
            'platform', 'app_version', 'os_version', 'device_model',
            'exception_type', 'exception_message', 'stack_trace',
            'fatal', 'breadcrumbs', 'custom_keys',
            'occurred_at',
            'created_at',
        ]
        read_only_fields = ['id', 'project', 'group', 'created_at']


class PerformanceTraceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceTrace
        fields = [
            'id', 'project',
            'trace_name', 'duration_ms',
            'user_id', 'session_id',
            'platform', 'app_version',
            'custom_attributes', 'custom_metrics',
            'occurred_at',
            'created_at',
        ]
        read_only_fields = ['id', 'project', 'created_at']


class NetworkRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkRequest
        fields = [
            'id', 'project',
            'url', 'http_method', 'response_code',
            'request_size_bytes', 'response_size_bytes',
            'duration_ms',
            'user_id', 'session_id',
            'platform', 'app_version',
            'occurred_at',
            'created_at',
        ]
        read_only_fields = ['id', 'project', 'created_at']
