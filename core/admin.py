"""
Django admin configuration for core models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core.models import Project, ProjectMembership, UserProfile


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'owner', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'owner__email']
    readonly_fields = ['id', 'api_key', 'created_at', 'updated_at']
    fieldsets = (
        ('Project Info', {
            'fields': ('id', 'name', 'slug', 'owner', 'description')
        }),
        ('Configuration', {
            'fields': ('api_key', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['project__name', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'sign_in_provider', 'email_verified', 'phone_verified']
    list_filter = ['sign_in_provider', 'email_verified', 'phone_verified']
    search_fields = ['user__email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Authentication', {
            'fields': ('sign_in_provider', 'email_verified', 'email_verified_at')
        }),
        ('Contact', {
            'fields': ('phone_number', 'phone_verified')
        }),
        ('Profile', {
            'fields': ('avatar_url', 'bio', 'custom_claims')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
