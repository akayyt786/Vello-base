"""
Custom permission classes for multi-tenant + project-based access control.
"""

from django.db import connection
from django.http import Http404
from rest_framework.permissions import BasePermission, SAFE_METHODS
from core.models import Project, ProjectMembership


def _set_rls_context(project_id, user_id=None):
    """
    Set the Postgres session variables that RLS policies read via
    app_funcs.current_project()/current_user() (see
    core/migrations/0004_postgres_rls.py).

    No-op on non-Postgres backends (e.g. SQLite in tests), since RLS doesn't
    apply there. Uses SET LOCAL so the value is scoped to the current
    request's transaction (DATABASES['default']['ATOMIC_REQUESTS'] = True
    for Postgres) and never leaks across requests on a pooled connection.
    """
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL app.current_project = %s", [str(project_id)])
        if user_id is not None:
            cursor.execute("SET LOCAL app.current_user = %s", [str(user_id)])


class IsProjectMember(BasePermission):
    """
    Allow access only to authenticated users who are members of the project.
    The project_id is passed as a URL parameter or extracted from JWT.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated and member of the project."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Extract project_id from request context (set by middleware)
        project_id = getattr(request, 'tenant_project_id', None)
        if not project_id:
            # Only use explicit project_id kwarg — never fall back to pk, which is
            # the object-level primary key in most ViewSets and would cause IDOR.
            project_id = view.kwargs.get('project_id')

        if not project_id:
            return False

        # Return 404 if project doesn't exist rather than 403
        if not Project.objects.filter(id=project_id).exists():
            raise Http404

        # Check membership
        is_member = ProjectMembership.objects.filter(
            project_id=project_id,
            user=request.user
        ).exists()
        if is_member:
            _set_rls_context(project_id, request.user.id)
        return is_member

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions."""
        # Objects should inherit project_id from parent model
        if hasattr(obj, 'project_id'):
            is_member = ProjectMembership.objects.filter(
                project_id=obj.project_id,
                user=request.user
            ).exists()
            if is_member:
                _set_rls_context(obj.project_id, request.user.id)
            return is_member
        return False


class IsProjectOwner(BasePermission):
    """
    Allow access only to project owners.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        project_id = getattr(request, 'tenant_project_id', None) or view.kwargs.get('project_id')
        if not project_id:
            return False

        is_owner = ProjectMembership.objects.filter(
            project_id=project_id,
            user=request.user,
            role='owner'
        ).exists()
        if is_owner:
            _set_rls_context(project_id, request.user.id)
        return is_owner

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'project_id'):
            is_owner = ProjectMembership.objects.filter(
                project_id=obj.project_id,
                user=request.user,
                role='owner'
            ).exists()
            if is_owner:
                _set_rls_context(obj.project_id, request.user.id)
            return is_owner
        return False


class IsProjectEditor(BasePermission):
    """
    Allow access only to project members whose role is 'owner' or 'editor'.
    Unlike IsProjectEditorOrOwner, this does NOT grant read access to plain viewers
    on SAFE_METHODS — it enforces editor/owner requirement on every method.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        project_id = getattr(request, 'tenant_project_id', None) or view.kwargs.get('project_id')
        if not project_id:
            return False

        is_editor = ProjectMembership.objects.filter(
            project_id=project_id,
            user=request.user,
            role__in=('owner', 'editor')
        ).exists()
        if is_editor:
            _set_rls_context(project_id, request.user.id)
        return is_editor

    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'project_id'):
            return False

        is_editor = ProjectMembership.objects.filter(
            project_id=obj.project_id,
            user=request.user,
            role__in=('owner', 'editor')
        ).exists()
        if is_editor:
            _set_rls_context(obj.project_id, request.user.id)
        return is_editor


class IsProjectEditorOrOwner(BasePermission):
    """
    Allow edit access to project editors and owners.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Read-only access for members
        if request.method in SAFE_METHODS:
            return ProjectMembership.objects.filter(
                user=request.user
            ).exists()

        # Write access for editors/owners
        project_id = getattr(request, 'tenant_project_id', None) or view.kwargs.get('project_id')
        if not project_id:
            return False

        is_editor = ProjectMembership.objects.filter(
            project_id=project_id,
            user=request.user,
            role__in=['editor', 'owner']
        ).exists()
        if is_editor:
            _set_rls_context(project_id, request.user.id)
        return is_editor

    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'project_id'):
            return False

        if request.method in SAFE_METHODS:
            is_member = ProjectMembership.objects.filter(
                project_id=obj.project_id,
                user=request.user
            ).exists()
            if is_member:
                _set_rls_context(obj.project_id, request.user.id)
            return is_member

        is_editor = ProjectMembership.objects.filter(
            project_id=obj.project_id,
            user=request.user,
            role__in=['editor', 'owner']
        ).exists()
        if is_editor:
            _set_rls_context(obj.project_id, request.user.id)
        return is_editor
