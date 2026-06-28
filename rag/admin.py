from django.contrib import admin
from .models import VectorCollection, VectorDocument


@admin.register(VectorCollection)
class VectorCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'embedding_model', 'dimensions', 'created_at']


@admin.register(VectorDocument)
class VectorDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'collection', 'external_id', 'created_at']
    search_fields = ['content', 'external_id']
