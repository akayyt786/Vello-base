"""Admin registrations for Remote Config + A/B Testing models."""

from django.contrib import admin
from .models import RemoteConfig, ConfigCondition, ConfigVersion, Experiment, ExperimentVariant


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


class ExperimentVariantInline(admin.TabularInline):
    model = ExperimentVariant
    extra = 0
    fields = ['name', 'is_control', 'traffic_weight', 'config_overrides']
    ordering = ['created_at']


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'project', 'status', 'traffic_fraction',
        'start_date', 'end_date', 'created_at',
    ]
    list_filter = ['status', 'project']
    search_fields = ['name', 'description', 'project__name', 'project__slug']
    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ExperimentVariantInline]
    fieldsets = [
        (None, {
            'fields': [
                'id', 'project', 'name', 'description', 'status',
                'traffic_fraction', 'metric_event',
            ],
        }),
        ('Schedule', {
            'fields': ['start_date', 'end_date'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]


@admin.register(ExperimentVariant)
class ExperimentVariantAdmin(admin.ModelAdmin):
    list_display = ['name', 'experiment', 'is_control', 'traffic_weight', 'created_at']
    list_filter = ['is_control']
    search_fields = ['name', 'description', 'experiment__name', 'experiment__project__name']
    ordering = ['experiment', 'created_at']
    readonly_fields = ['id', 'created_at']
