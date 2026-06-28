from rest_framework import serializers
from .models import VectorCollection, VectorDocument


class VectorCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorCollection
        fields = ['id', 'name', 'description', 'embedding_model', 'dimensions', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class VectorDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VectorDocument
        fields = ['id', 'external_id', 'content', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']


class IngestDocumentSerializer(serializers.Serializer):
    documents = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=100,
        help_text="List of {content: str, metadata?: dict, external_id?: str}"
    )
    embed = serializers.BooleanField(default=True, help_text="Automatically embed using collection's model")


class SearchSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=50)
    threshold = serializers.FloatField(default=0.0, min_value=0.0, max_value=1.0)
    include_metadata = serializers.BooleanField(default=True)


class RAGQuerySerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=20)
    provider = serializers.ChoiceField(choices=['anthropic', 'google'], default='anthropic')
    model = serializers.CharField(default='claude-haiku-4-5-20251001')
    system = serializers.CharField(required=False, allow_blank=True)
    max_tokens = serializers.IntegerField(default=1024, min_value=1, max_value=4096)
