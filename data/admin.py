"""
Django admin configuration for Data models.
"""

from django.contrib import admin
from django.utils.html import format_html
from data.models import Collection, Document


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    """Admin interface for Collections."""
    list_display = ['path_link', 'project', 'name', 'document_count', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['name', 'path', 'project__name']
    readonly_fields = ['id', 'document_count', 'created_at', 'updated_at', 'created_by', 'updated_by']
    fieldsets = (
        ('Identity', {
            'fields': ['id', 'project']
        }),
        ('Collection Info', {
            'fields': ['name', 'path', 'document_count']
        }),
        ('Schema', {
            'fields': ['schema'],
            'classes': ['collapse']
        }),
        ('Audit', {
            'fields': ['created_by', 'created_at', 'updated_by', 'updated_at'],
            'classes': ['collapse']
        }),
    )

    def path_link(self, obj):
        """Display path as a link."""
        return format_html(
            '<code>{}</code>',
            obj.path
        )
    path_link.short_description = 'Path'

    def get_queryset(self, request):
        """Filter by user's projects."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            from core.models import ProjectMembership
            user_projects = ProjectMembership.objects.filter(
                user=request.user
            ).values_list('project_id', flat=True)
            qs = qs.filter(project__in=user_projects)
        return qs


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Documents."""
    list_display = ['full_path_link', 'project', 'collection_path', 'version_display', 'updated_at']
    list_filter = ['project', 'collection_path', 'updated_at']
    search_fields = ['collection_path', 'doc_id', 'project__name']
    readonly_fields = ['id', 'full_path', 'created_at', 'updated_at', 'created_by', 'updated_by']
    fieldsets = (
        ('Identity', {
            'fields': ['id', 'project', 'full_path']
        }),
        ('Document Path', {
            'fields': ['collection_path', 'doc_id']
        }),
        ('Data', {
            'fields': ['data'],
            'classes': ['collapse']
        }),
        ('Versioning', {
            'fields': ['v'],
        }),
        ('Audit', {
            'fields': ['created_by', 'created_at', 'updated_by', 'updated_at'],
            'classes': ['collapse']
        }),
    )

    def full_path_link(self, obj):
        """Display full path as a link."""
        return format_html(
            '<code>{}</code>',
            obj.full_path
        )
    full_path_link.short_description = 'Full Path'

    def version_display(self, obj):
        """Display version counter."""
        return format_html(
            '<strong>v{}</strong>',
            obj.v
        )
    version_display.short_description = 'Version'

    def get_queryset(self, request):
        """Filter by user's projects."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            from core.models import ProjectMembership
            user_projects = ProjectMembership.objects.filter(
                user=request.user
            ).values_list('project_id', flat=True)
            qs = qs.filter(project__in=user_projects)
        return qs

    def has_add_permission(self, request):
        """Prevent direct admin creation; use API instead."""
        return False
