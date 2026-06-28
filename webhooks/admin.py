from django.contrib import admin
from .models import WebhookEndpoint, WebhookDelivery


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ['url', 'project', 'is_active', 'created_at']


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'event_type', 'status', 'response_status', 'latency_ms', 'created_at']
    list_filter = ['status', 'event_type']
