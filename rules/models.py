"""
Security Policy model: stores declarative access control rules per project + collection.
Rules are evaluated by RuleEngine on every read/write request.
"""

import uuid
import json
from django.db import models
from django.core.exceptions import ValidationError
from core.models import MultiTenantModel, Project


class SecurityPolicy(MultiTenantModel):
    """
    A security rule for a specific collection in a project.

    Example:
      project_id: <project-uuid>
      collection: "documents"
      rule_type: "read"
      condition_json: '{"operator": "and", "conditions": [
        {"type": "auth_check", "value": {"field": "request.auth", "op": "!=", "rhs": "null"}},
        {"type": "field_check", "value": {"path": "data.owner", "op": "==", "rhs_field": "request.auth.uid"}}
      ]}'
      active: True
    """

    RULE_TYPE_CHOICES = [
        ('read', 'Read'),
        ('write', 'Write'),
        ('delete', 'Delete'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Which collection this rule applies to
    collection = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Collection name (e.g., 'documents', 'posts', 'users')"
    )

    # Type of operation
    rule_type = models.CharField(
        max_length=20,
        choices=RULE_TYPE_CHOICES,
        db_index=True,
        help_text="Operation type: read, write, or delete"
    )

    # Condition DSL as JSON
    # Structure: { "operator": "and|or", "conditions": [...] }
    # Each condition can be:
    #   - {"type": "auth_check", "value": {...}}       # check request.auth
    #   - {"type": "field_check", "value": {...}}      # check document field
    #   - {"type": "owner_check", "value": {...}}      # check ownership
    #   - {"type": "role_check", "value": {...}}       # check user role
    condition_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Condition tree in JSON format"
    )

    # Whether this rule is active
    active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive rules are not evaluated"
    )

    # Human-readable description
    description = models.TextField(
        blank=True,
        help_text="Description of what this rule does"
    )

    # Priority: higher numbers are evaluated first (for early exit optimization)
    priority = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Evaluation priority (higher = evaluated first)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rules_security_policy'
        unique_together = [['project', 'collection', 'rule_type', 'id']]
        indexes = [
            models.Index(fields=['project', 'collection', 'rule_type', 'active']),
            models.Index(fields=['project', 'active', 'priority']),
        ]
        ordering = ['-priority', 'collection', 'rule_type']

    def __str__(self):
        return f"{self.project.slug}/{self.collection}:{self.rule_type}"

    def clean(self):
        """Validate the condition_json structure."""
        if self.condition_json:
            try:
                if not isinstance(self.condition_json, dict):
                    raise ValidationError("condition_json must be a dict")
                if 'operator' not in self.condition_json:
                    raise ValidationError("condition_json must have 'operator' key")
                if self.condition_json['operator'] not in ['and', 'or']:
                    raise ValidationError("operator must be 'and' or 'or'")
                if 'conditions' not in self.condition_json:
                    raise ValidationError("condition_json must have 'conditions' key")
            except (TypeError, ValueError) as e:
                raise ValidationError(f"Invalid condition_json: {e}")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class PolicyAuditLog(models.Model):
    """
    Log of policy evaluation for debugging and auditing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Request context
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='policy_audit_logs')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    # Operation
    collection = models.CharField(max_length=255, db_index=True)
    operation = models.CharField(max_length=20, choices=[('read', 'Read'), ('write', 'Write'), ('delete', 'Delete')])
    document_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Result
    allowed = models.BooleanField(default=False)
    reason = models.TextField(blank=True, help_text="Why the decision was made")

    # Evaluated policies
    matched_policies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of policy IDs that were evaluated"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'rules_policy_audit_log'
        indexes = [
            models.Index(fields=['project', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['collection', 'operation']),
        ]

    def __str__(self):
        return f"{self.user.email if self.user else 'anon'} {self.operation} {self.collection}/{self.document_id}: {self.allowed}"
