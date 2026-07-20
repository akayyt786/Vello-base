"""Admin registrations for Remote Config models."""

from django.contrib import admin
from .models import RemoteConfig, ConfigCondition, ConfigVersion


class ConfigConditionInline(admin.TabularInline):
    model = ConfigCondition
    extra = 0
    fields = ['name', 'condition_type', 'condition_params', 'value', 'priority', 'is_active']
    ordering = ['-priority', 'created_at']


@admin.register(RemoteConfig)
class RemoteConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'project', 'value_type', 'is_active', 'created_at', 'updated_at']
    list_filter = ['value_type', 'is_active', 'project']
    search_fields = ['key', 'description', 'project__name', 'project__slug']
    ordering = ['project', 'key']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ConfigConditionInline]
    fieldsets = [
        (None, {
            'fields': ['id', 'project', 'key', 'value_type', 'default_value', 'description', 'is_active'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(ConfigCondition)
class ConfigConditionAdmin(admin.ModelAdmin):
    list_display = ['name', 'config', 'condition_type', 'priority', 'is_active', 'created_at']
    list_filter = ['condition_type', 'is_active']
    search_fields = ['name', 'config__key', 'config__project__name']
    ordering = ['-priority', 'created_at']
    readonly_fields = ['id', 'created_at']


@admin.register(ConfigVersion)
class ConfigVersionAdmin(admin.ModelAdmin):
    list_display = ['version_number', 'project', 'description', 'published_by', 'published_at']
    list_filter = ['project']
    search_fields = ['description', 'project__name', 'project__slug', 'published_by__email']
    ordering = ['-version_number']
    readonly_fields = ['id', 'version_number', 'published_at']
