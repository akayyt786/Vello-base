"""Admin registration for the Crashlytics app."""

from django.contrib import admin

from .models import CrashGroup, CrashReport, PerformanceTrace, NetworkRequest


@admin.register(CrashGroup)
class CrashGroupAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'project', 'exception_type', 'title',
        'occurrence_count', 'affected_users_count',
        'is_resolved', 'first_seen_at', 'last_seen_at',
    ]
    list_filter = ['is_resolved', 'project']
    search_fields = ['title', 'exception_type', 'signature', 'project__slug']
    raw_id_fields = ['project']
    readonly_fields = ['id', 'signature', 'occurrence_count', 'affected_users_count',
                       'first_seen_at', 'last_seen_at', 'created_at', 'updated_at']
    ordering = ['-last_seen_at']


@admin.register(CrashReport)
class CrashReportAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'project', 'exception_type', 'platform',
        'app_version', 'fatal', 'user_id', 'occurred_at', 'created_at',
    ]
    list_filter = ['platform', 'fatal', 'project']
    search_fields = ['exception_type', 'exception_message', 'user_id', 'project__slug', 'session_id']
    raw_id_fields = ['project', 'group']
    readonly_fields = ['id', 'group', 'created_at']
    ordering = ['-occurred_at']


@admin.register(PerformanceTrace)
class PerformanceTraceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'project', 'trace_name', 'duration_ms',
        'platform', 'app_version', 'user_id', 'occurred_at',
    ]
    list_filter = ['platform', 'project']
    search_fields = ['trace_name', 'user_id', 'project__slug', 'session_id']
    raw_id_fields = ['project']
    readonly_fields = ['id', 'created_at']
    ordering = ['-occurred_at']


@admin.register(NetworkRequest)
class NetworkRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'project', 'http_method', 'url', 'response_code',
        'duration_ms', 'platform', 'app_version', 'occurred_at',
    ]
    list_filter = ['http_method', 'response_code', 'platform', 'project']
    search_fields = ['url', 'user_id', 'project__slug', 'session_id']
    raw_id_fields = ['project']
    readonly_fields = ['id', 'created_at']
    ordering = ['-occurred_at']
