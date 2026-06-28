"""
DRF serializers for Data API (Collections and Documents).
"""

import re

from rest_framework import serializers
from data.models import Collection, Document


class CollectionSerializer(serializers.ModelSerializer):
    """
    Serializer for Collection metadata.
    Exposes collection info, not individual documents.
    """
    class Meta:
        model = Collection
        fields = [
            'id', 'project', 'name', 'path', 'schema',
            'document_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'project', 'created_at', 'updated_at', 'document_count']


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for Document read/write.
    Converts between Django model and Firestore REST API shape.

    Firestore REST API shape:
    {
        "name": "projects/proj123/databases/(default)/documents/users/alice",
        "fields": {
            "name": {"stringValue": "Alice"},
            "age": {"integerValue": 30},
            "tags": {"arrayValue": {"values": [{"stringValue": "admin"}]}},
            "address": {"mapValue": {"fields": {"city": {"stringValue": "NYC"}}}},
            "createdAt": {"timestampValue": "2024-01-01T00:00:00Z"}
        },
        "createTime": "2024-01-01T00:00:00Z",
        "updateTime": "2024-01-01T00:00:00Z"
    }

    Our simplified shape:
    {
        "id": "doc-uuid",
        "collection_path": "users",
        "doc_id": "alice",
        "data": {
            "name": "Alice",
            "age": 30,
            "tags": ["admin"],
            "address": {"city": "NYC"},
            "createdAt": "2024-01-01T00:00:00Z"
        },
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "__v": 1
    }
    """
    class Meta:
        model = Document
        fields = [
            'id', 'collection_path', 'doc_id', 'data',
            'created_at', 'updated_at', 'v'
        ]
        read_only_fields = ['id', 'project', 'created_at', 'updated_at', 'v']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['__v'] = ret.pop('v', 0)
        return ret

    def create(self, validated_data):
        """Create a new document with project from context."""
        request = self.context.get('request')
        if request and hasattr(request, 'project'):
            validated_data['project'] = request.project
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update document and increment version counter."""
        instance.v += 1
        return super().update(instance, validated_data)


class DocumentWriteSerializer(serializers.Serializer):
    """
    Serializer for batch write operations.
    Supports create, update, delete operations.
    """
    writes = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of write operations: [{'op': 'set'|'update'|'delete', 'path': '...', 'data': {...}}]"
    )
    options = serializers.DictField(
        required=False,
        help_text="Transaction options: {'startTime': '...', 'previousUpdateTime': '...'}"
    )

    def validate_writes(self, writes):
        """Validate each write operation."""
        for i, write in enumerate(writes):
            if 'op' not in write or write['op'] not in ['set', 'update', 'delete']:
                raise serializers.ValidationError(
                    f"Write {i}: 'op' must be 'set', 'update', or 'delete'"
                )
            if 'path' not in write:
                raise serializers.ValidationError(f"Write {i}: 'path' is required")
            if write['op'] in ['set', 'update'] and 'data' not in write:
                raise serializers.ValidationError(
                    f"Write {i}: 'data' is required for op='{write['op']}'"
                )
        return writes


class DocumentQuerySerializer(serializers.Serializer):
    """
    Serializer for query operations.
    Parses Firestore-style query params into structured form.
    """
    collection_path = serializers.CharField(
        help_text="Collection path to query (e.g., 'users', 'users/alice/posts')"
    )
    where = serializers.JSONField(
        required=False,
        default=list,
        help_text="Array of filter conditions: [{'field': 'status', 'op': '==', 'value': 'active'}]"
    )
    order_by = serializers.JSONField(
        required=False,
        default=list,
        help_text="Array of sort specs: [{'field': 'created_at', 'direction': 'desc'}]"
    )
    limit = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=1000,
        help_text="Max documents to return (default: 20, max: 1000)"
    )
    start_after = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Cursor (document ID) for keyset pagination"
    )
    end_at = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="End cursor (document ID) for keyset pagination"
    )

    def validate_where(self, where):
        """Validate WHERE clause format."""
        if not isinstance(where, list):
            raise serializers.ValidationError("'where' must be a list of conditions")
        for i, condition in enumerate(where):
            if not isinstance(condition, dict):
                raise serializers.ValidationError(
                    f"Condition {i}: must be a dict with 'field', 'op', 'value'"
                )
            required_keys = {'field', 'op', 'value'}
            if not required_keys.issubset(condition.keys()):
                raise serializers.ValidationError(
                    f"Condition {i}: missing keys {required_keys - set(condition.keys())}"
                )
            # Validate field name: reject empty strings, '__' (Django ORM traversal),
            # and any character outside [a-zA-Z0-9_.].
            field = condition['field']
            if not field or not isinstance(field, str):
                raise serializers.ValidationError(
                    f"Condition {i}: 'field' must be a non-empty string"
                )
            if '__' in field:
                raise serializers.ValidationError(
                    f"Condition {i}: field name must not contain '__'"
                )
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', field):
                raise serializers.ValidationError(
                    f"Condition {i}: field name '{field}' contains invalid characters"
                )
            # Operator allowlist — reject unknown ops with 400.
            valid_ops = {'==', '!=', '<', '<=', '>', '>=', 'in', 'not-in', 'array-contains', 'array-contains-any'}
            if condition['op'] not in valid_ops:
                raise serializers.ValidationError(
                    f"Condition {i}: op '{condition['op']}' not supported. Valid: {sorted(valid_ops)}"
                )
        return where

    def validate_order_by(self, order_by):
        """Validate ORDER BY clause format."""
        if not isinstance(order_by, list):
            raise serializers.ValidationError("'order_by' must be a list of sort specs")
        for i, spec in enumerate(order_by):
            if not isinstance(spec, dict) or 'field' not in spec:
                raise serializers.ValidationError(
                    f"Sort spec {i}: must have 'field' key"
                )
            # Validate field name: reject empty strings, '__' (Django ORM traversal),
            # and any character outside [a-zA-Z0-9_.].
            field = spec['field']
            if not field or not isinstance(field, str):
                raise serializers.ValidationError(
                    f"Sort spec {i}: 'field' must be a non-empty string"
                )
            if '__' in field:
                raise serializers.ValidationError(
                    f"Sort spec {i}: field name must not contain '__'"
                )
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*$', field):
                raise serializers.ValidationError(
                    f"Sort spec {i}: field name '{field}' contains invalid characters"
                )
            if spec.get('direction') not in ['asc', 'desc', None]:
                raise serializers.ValidationError(
                    f"Sort spec {i}: 'direction' must be 'asc' or 'desc' (default: asc)"
                )
        return order_by
