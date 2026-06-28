"""Admin registration for the Push Notifications app."""

from django.contrib import admin
from .models import DeviceToken, Topic, TopicSubscription, PushNotification, NotificationCampaign


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'platform', 'app_id', 'user', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active', 'project']
    search_fields = ['token', 'app_id', 'user__email', 'project__slug']
    raw_id_fields = ['project', 'user']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'name', 'created_at']
    list_filter = ['project']
    search_fields = ['name', 'description', 'project__slug']
    raw_id_fields = ['project']
    readonly_fields = ['id', 'created_at']
    ordering = ['project', 'name']


@admin.register(TopicSubscription)
class TopicSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'topic', 'device_token', 'created_at']
    list_filter = ['topic__project']
    search_fields = ['topic__name', 'device_token__token', 'topic__project__slug']
    raw_id_fields = ['topic', 'device_token']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']


@admin.register(PushNotification)
class PushNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'title', 'status', 'device_token', 'topic', 'delivered_at', 'created_at']
    list_filter = ['status', 'project']
    search_fields = ['title', 'body', 'project__slug', 'error']
    raw_id_fields = ['project', 'device_token', 'topic']
    readonly_fields = ['id', 'status', 'error', 'delivered_at', 'created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(NotificationCampaign)
class NotificationCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'project', 'name', 'status',
        'total_sent', 'total_failed',
        'scheduled_at', 'sent_at', 'created_at',
    ]
    list_filter = ['status', 'project']
    search_fields = ['name', 'title', 'body', 'project__slug']
    raw_id_fields = ['project', 'topic']
    readonly_fields = ['id', 'status', 'sent_at', 'total_sent', 'total_failed', 'created_at', 'updated_at']
    ordering = ['-created_at']
