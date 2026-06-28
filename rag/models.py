import uuid
from django.db import models
from django.conf import settings


def _is_postgres():
    db_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    return 'postgresql' in db_engine or 'postgis' in db_engine


class VectorCollection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='vector_collections')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    embedding_model = models.CharField(max_length=64, default='text-embedding-3-small')
    dimensions = models.IntegerField(default=1536)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('project', 'name')]

    def __str__(self):
        return f"{self.project} / {self.name}"


class VectorDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(VectorCollection, on_delete=models.CASCADE, related_name='documents')
    external_id = models.CharField(max_length=255, blank=True, help_text="Optional caller-provided ID")
    content = models.TextField()
    metadata = models.JSONField(default=dict)
    # Store embedding as JSON list of floats — works on SQLite + Postgres.
    # On Postgres with pgvector installed, a migration can alter this to vector type.
    embedding = models.JSONField(null=True, blank=True, help_text="List of floats — embedding vector")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['collection', 'external_id'])]

    def __str__(self):
        return f"Doc {self.id} in {self.collection.name}"
