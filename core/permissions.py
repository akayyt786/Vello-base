"""
Custom permission classes for multi-tenant + project-based access control.
"""

from django.http import Http404
from rest_framework.permissions import BasePermission, SAFE_METHODS
from core.models import Project, ProjectMembership


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
            # Try to get from URL kwargs
            project_id = view.kwargs.get('project_id') or view.kwargs.get('pk')

        if not project_id:
            return False

        # Return 404 if project doesn't exist rather than 403
        if not Project.objects.filter(id=project_id).exists():
            raise Http404

        # Check membership
        return ProjectMembership.objects.filter(
            project_id=project_id,
            user=request.user
        ).exists()

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions."""
        # Objects should inherit project_id from parent model
        if hasattr(obj, 'project_id'):
            return ProjectMembership.objects.filter(
                project_id=obj.project_id,
                user=request.user
            ).exists()
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

        return ProjectMembership.objects.filter(
            project_id=project_id,
            user=request.user,
            role='owner'
        ).exists()

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'project_id'):
            return ProjectMembership.objects.filter(
                project_id=obj.project_id,
                user=request.user,
                role='owner'
            ).exists()
        return False


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

        return ProjectMembership.objects.filter(
            project_id=project_id,
            user=request.user,
            role__in=['editor', 'owner']
        ).exists()

    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'project_id'):
            return False

        if request.method in SAFE_METHODS:
            return ProjectMembership.objects.filter(
                project_id=obj.project_id,
                user=request.user
            ).exists()

        return ProjectMembership.objects.filter(
            project_id=obj.project_id,
            user=request.user,
            role__in=['editor', 'owner']
        ).exists()
