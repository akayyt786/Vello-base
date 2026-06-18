"""
DRF permission classes that enforce Security Rules on every request.
Integrates with RuleEngine to evaluate policies before allowing access.
"""

import logging
from typing import Optional
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone

from rules.dsl import RuleEngine, RequestContext, Document
from rules.models import SecurityPolicy, PolicyAuditLog

logger = logging.getLogger(__name__)


class DocumentRules(BasePermission):
    """
    DRF permission class that enforces Security Rules on document access.

    Usage:
      class DocumentViewSet(viewsets.ModelViewSet):
          permission_classes = [IsAuthenticated, DocumentRules]
          queryset = Document.objects.all()

    This class:
    1. Extracts the operation type (read/write/delete) from the HTTP method
    2. Loads matching SecurityPolicy rules for the collection
    3. Evaluates rules via RuleEngine
    4. Logs the decision to PolicyAuditLog (for debugging)
    5. Returns True/False for DRF to allow/deny
    """

    def has_permission(self, request, view):
        """
        Check list/create permissions.
        Called for non-detail routes like GET /documents/ or POST /documents/
        """
        # All authenticated users can list/create (details checked in has_object_permission)
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions (detail routes).
        Called for GET /documents/123, PATCH /documents/123, DELETE /documents/123
        """
        if not request.user or not request.user.is_authenticated:
            return False

        # Determine operation
        operation = self._get_operation(request)

        # Extract collection and document info from object
        collection = self._get_collection_name(obj)
        document = self._object_to_document(obj)

        if not collection or not document:
            logger.warning(f"Could not extract collection/document info from {obj}")
            return False

        # Get project ID
        project_id = self._get_project_id(request, obj)
        if not project_id:
            return False

        # Check rules
        allowed = self._check_rules(
            request.user,
            project_id,
            collection,
            operation,
            document,
        )

        # Audit log
        self._log_decision(
            request.user,
            project_id,
            collection,
            operation,
            document.id,
            allowed,
            f"Document rule check: {operation} {collection}/{document.id}",
        )

        return allowed

    def _get_operation(self, request) -> str:
        """Map HTTP method to operation type."""
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return 'read'
        elif request.method == 'DELETE':
            return 'delete'
        else:  # POST, PUT, PATCH
            return 'write'

    def _get_collection_name(self, obj) -> Optional[str]:
        """Extract collection name from object."""
        # Option 1: Check for explicit collection attribute
        if hasattr(obj, 'collection'):
            return obj.collection

        # Option 2: Use model name (lowercased)
        if hasattr(obj, '__class__'):
            return obj.__class__.__name__.lower() + 's'

        return None

    def _object_to_document(self, obj) -> Optional[Document]:
        """Convert Django model instance to Document."""
        try:
            doc_id = str(obj.id) if hasattr(obj, 'id') else str(obj.pk)

            # Extract data
            if hasattr(obj, 'data') and isinstance(obj.data, dict):
                # If model has a 'data' JSONField
                data = obj.data
            else:
                # Use model fields
                data = {
                    field.name: getattr(obj, field.name, None)
                    for field in obj._meta.fields
                    if field.name not in ('id', 'project_id', 'created_by', 'updated_by', 'created_at', 'updated_at')
                }

            # Extract owner_id
            owner_id = None
            if hasattr(obj, 'owner_id'):
                owner_id = obj.owner_id
            elif hasattr(obj, 'owner'):
                owner_id = getattr(obj.owner, 'id', None)
            elif hasattr(obj, 'created_by_id'):
                owner_id = obj.created_by_id

            return Document(id=doc_id, data=data, owner_id=owner_id)

        except Exception as e:
            logger.error(f"Failed to convert object to Document: {e}")
            return None

    def _get_project_id(self, request, obj) -> Optional[str]:
        """Extract project ID from request or object."""
        # Option 1: From request context (set by middleware)
        if hasattr(request, 'tenant_project_id'):
            return request.tenant_project_id

        # Option 2: From object
        if hasattr(obj, 'project_id'):
            return obj.project_id

        return None

    def _check_rules(
        self,
        user,
        project_id,
        collection: str,
        operation: str,
        document: Document,
    ) -> bool:
        """
        Evaluate all active rules for this (project, collection, operation).

        Rules are evaluated in priority order (highest first).
        First rule to explicitly allow or deny wins.

        If no rules match, default is DENY (fail-safe).
        """
        from django.contrib.auth.models import AnonymousUser

        # Load all active rules for this collection + operation
        rules = SecurityPolicy.objects.filter(
            project_id=project_id,
            collection=collection,
            rule_type=operation,
            active=True,
        ).order_by('-priority', 'id')

        if not rules.exists():
            # No rules = deny by default (fail-safe)
            logger.debug(f"No rules found for {project_id}/{collection}:{operation}. Denying by default.")
            return False

        # Set up request context
        is_admin = user.is_staff if not isinstance(user, AnonymousUser) else False
        auth_uid = str(user.id) if user.is_authenticated else None

        request_ctx = RequestContext(
            auth_user=user if user.is_authenticated else None,
            auth_uid=auth_uid,
            operation=operation,
            is_admin=is_admin,
        )

        # Evaluate rules
        engine = RuleEngine()
        for rule in rules:
            try:
                result = engine.check(rule.condition_json, request_ctx, document)
                if result:
                    logger.debug(f"Rule {rule.id} ALLOWED {operation} {collection}/{document.id}")
                    return True
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")
                continue

        # No rule allowed it
        logger.debug(f"No rules allowed {operation} {collection}/{document.id}. Denying.")
        return False

    def _log_decision(
        self,
        user,
        project_id,
        collection: str,
        operation: str,
        document_id: str,
        allowed: bool,
        reason: str,
    ):
        """Log the rule evaluation decision."""
        if not hasattr(self, 'enable_audit') or not self.enable_audit:
            # Audit disabled
            return

        try:
            PolicyAuditLog.objects.create(
                project_id=project_id,
                user=user,
                collection=collection,
                operation=operation,
                document_id=document_id,
                allowed=allowed,
                reason=reason,
            )
        except Exception as e:
            logger.error(f"Failed to log policy audit: {e}")


class DocumentRulesNoAudit(DocumentRules):
    """
    Version of DocumentRules that skips audit logging (for high-volume scenarios).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_audit = False
