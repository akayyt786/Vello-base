from django.contrib import admin
from .models import AppCheckConfig, AppCheckToken, DebugToken


@admin.register(AppCheckConfig)
class AppCheckConfigAdmin(admin.ModelAdmin):
    list_display = ['project', 'platform', 'provider', 'is_enabled']
    list_filter = ['platform', 'provider', 'is_enabled']


@admin.register(AppCheckToken)
class AppCheckTokenAdmin(admin.ModelAdmin):
    list_display = ['project', 'platform', 'is_revoked', 'expires_at', 'issued_at']
    list_filter = ['platform', 'is_revoked']


@admin.register(DebugToken)
class DebugTokenAdmin(admin.ModelAdmin):
    list_display = ['project', 'name', 'is_active', 'created_at']
