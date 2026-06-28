"""Django admin registration for Analytics models."""

from django.contrib import admin
from .models import Event, UserProperty, ConversionEvent


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'event_name', 'user_id', 'platform', 'occurred_at', 'created_at']
    list_filter = ['platform', 'project']
    search_fields = ['event_name', 'user_id', 'session_id', 'device_id']
    readonly_fields = ['id', 'created_at']
    ordering = ['-occurred_at']


@admin.register(UserProperty)
class UserPropertyAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'user_id', 'name', 'value', 'updated_at']
    list_filter = ['project']
    search_fields = ['user_id', 'name', 'value']
    readonly_fields = ['id', 'updated_at']


@admin.register(ConversionEvent)
class ConversionEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'event_name', 'created_at']
    list_filter = ['project']
    search_fields = ['event_name']
    readonly_fields = ['id', 'created_at']
