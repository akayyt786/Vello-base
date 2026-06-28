from django.contrib import admin

from .models import AIProviderConfig, AIUsageLog


@admin.register(AIProviderConfig)
class AIProviderConfigAdmin(admin.ModelAdmin):
    list_display = ['project', 'provider', 'is_active', 'created_at']
    list_filter = ['provider', 'is_active']


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ['project', 'provider', 'model', 'total_tokens', 'latency_ms', 'status', 'created_at']
    list_filter = ['provider', 'status']
