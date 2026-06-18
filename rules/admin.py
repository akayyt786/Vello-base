"""
Django admin configuration for Security Rules.
"""

from django.contrib import admin
from rules.models import SecurityPolicy, PolicyAuditLog


@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    """Admin for SecurityPolicy model."""
    list_display = ['id', 'project', 'collection', 'rule_type', 'active', 'priority', 'created_at']
    list_filter = ['project', 'collection', 'rule_type', 'active', 'created_at']
    search_fields = ['project__slug', 'collection', 'description']
    ordering = ['-priority', 'collection', 'rule_type']

    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Project & Collection', {
            'fields': ['project', 'collection', 'rule_type']
        }),
        ('Rule Configuration', {
            'fields': ['condition_json', 'active', 'priority', 'description']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        Override save to trigger RLS policy application.
        """
        super().save_model(request, obj, form, change)

        # Apply RLS policy to Postgres (if configured)
        try:
            from rules.postgres import apply_rls_policy
            if obj.active:
                apply_rls_policy(
                    str(obj.project.id),
                    obj.collection,
                    obj.rule_type,
                    str(obj.id),
                    obj.condition_json,
                )
        except Exception as e:
            # Log but don't fail the admin save
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to apply RLS policy: {e}")


@admin.register(PolicyAuditLog)
class PolicyAuditLogAdmin(admin.ModelAdmin):
    """Admin for PolicyAuditLog model (read-only)."""
    list_display = ['id', 'project', 'user', 'collection', 'operation', 'document_id', 'allowed', 'created_at']
    list_filter = ['project', 'collection', 'operation', 'allowed', 'created_at']
    search_fields = ['project__slug', 'user__email', 'collection', 'document_id']
    readonly_fields = ['id', 'project', 'user', 'collection', 'operation', 'document_id', 'allowed', 'reason', 'matched_policies', 'created_at']

    def has_add_permission(self, request):
        """Disable adding audit logs manually."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for log retention management."""
        return True
