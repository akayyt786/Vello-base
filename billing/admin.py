from django.contrib import admin
from .models import ProjectSubscription, QuotaUsage


@admin.register(ProjectSubscription)
class ProjectSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['project', 'tier', 'billing_email', 'created_at']
    list_filter = ['tier']


@admin.register(QuotaUsage)
class QuotaUsageAdmin(admin.ModelAdmin):
    list_display = ['project', 'year', 'month', 'api_calls', 'ai_tokens', 'function_invocations']
