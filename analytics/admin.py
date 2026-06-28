from django.contrib import admin
from .models import AnalyticsEvent

@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'project', 'user', 'platform', 'timestamp']
    list_filter = ['event_name', 'platform']
    search_fields = ['event_name', 'anonymous_id']
