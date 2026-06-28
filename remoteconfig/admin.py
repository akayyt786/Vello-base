from django.contrib import admin
from .models import RemoteConfigParameter


@admin.register(RemoteConfigParameter)
class RemoteConfigParameterAdmin(admin.ModelAdmin):
    list_display = ['key', 'project', 'param_type', 'value', 'is_active', 'updated_at']
    list_filter = ['param_type', 'is_active']
    search_fields = ['key']
