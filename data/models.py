"""
Data models: Collections and Documents (Firestore-like).
Single Document model with JSONB data column, similar to Firestore's Entities table.
"""

import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from core.models import MultiTenantModel


class Collection(MultiTenantModel):
    """
    A collection is a logical grouping of documents.
    Collections have no physical representation in Firestore — they exist only as common prefixes.
    In this implementation, we track collection metadata (name, schema hints) for admin/console use.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)

    # Path: encodes hierarchy for subcollections (e.g., "users", "users/alice/posts")
    path = models.TextField(db_index=True, unique=True)

    # Schema metadata (optional, for admin console and validation hints)
    schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional schema metadata: field types, indexes, validation rules"
    )

    # Document count cache (updated periodically, not real-time)
    document_count = models.IntegerField(default=0, editable=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'data_collection'
        unique_together = [['project', 'path']]
        indexes = [
            models.Index(fields=['project', 'name']),
            models.Index(fields=['project', 'created_at']),
        ]
        ordering = ['path']

    def __str__(self):
        return f"{self.project.slug}/{self.path}"


class Document(MultiTenantModel):
    """
    A document is a key-value map stored under a path (e.g., "users/alice").
    This model mirrors Firestore's Entities table exactly.

    Supports:
    - Full document paths: "users/alice/posts/post1" (encoded in collection_path + doc_id)
    - Nested JSONB data with arbitrary field types
    - Optimistic locking via __v (version field)
    - Automatic timestamps
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Collection path: "users", "users/alice/posts", etc.
    # Encodes the full hierarchy, allowing subcollections.
    collection_path = models.TextField(db_index=True)

    # Document ID within the collection (e.g., "alice", "post1")
    doc_id = models.TextField()

    # JSONB data: stores arbitrary nested document content
    # Supports all Firestore types: string, number, boolean, null, array, object, timestamp
    data = models.JSONField(default=dict)

    # Optimistic locking version counter (incremented on every write)
    # Prevents lost updates in concurrent scenarios
    v = models.IntegerField(default=0, db_column='version')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = 'data_document'
        unique_together = [['project', 'collection_path', 'doc_id']]
        indexes = [
            # GIN index for JSONB containment queries (?where=field:value)
            GinIndex(fields=['data'], name='document_data_gin'),
            # Index for ordering by created/updated timestamps
            models.Index(fields=['project', 'collection_path', 'created_at']),
            models.Index(fields=['project', 'collection_path', 'updated_at']),
        ]
        ordering = ['-updated_at']

    @property
    def full_path(self):
        """Full document path: collection_path/doc_id (e.g., 'users/alice/posts/post1')"""
        return f"{self.collection_path}/{self.doc_id}"

    def __str__(self):
        return f"{self.project.slug}/{self.full_path}"
