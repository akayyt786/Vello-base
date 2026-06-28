"""Django admin registrations for the A/B Testing app."""

from django.contrib import admin

from .models import Experiment, ExperimentVariant, ExperimentAssignment, ExperimentConversion


class ExperimentVariantInline(admin.TabularInline):
    model = ExperimentVariant
    extra = 0
    fields = ['name', 'description', 'allocation', 'config']


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'status', 'targeting_key', 'created_at']
    list_filter = ['status', 'targeting_key']
    search_fields = ['name', 'project__slug']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ExperimentVariantInline]


@admin.register(ExperimentVariant)
class ExperimentVariantAdmin(admin.ModelAdmin):
    list_display = ['name', 'experiment', 'allocation', 'created_at']
    list_filter = ['experiment__status']
    search_fields = ['name', 'experiment__name']
    readonly_fields = ['id', 'created_at']


@admin.register(ExperimentAssignment)
class ExperimentAssignmentAdmin(admin.ModelAdmin):
    list_display = ['targeting_value', 'experiment', 'variant', 'assigned_at']
    list_filter = ['experiment']
    search_fields = ['targeting_value', 'experiment__name', 'variant__name']
    readonly_fields = ['id', 'assigned_at']


@admin.register(ExperimentConversion)
class ExperimentConversionAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'value', 'assignment', 'recorded_at']
    list_filter = ['event_name']
    search_fields = ['event_name', 'assignment__targeting_value']
    readonly_fields = ['id', 'recorded_at']
