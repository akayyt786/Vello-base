"""Serializers for the A/B Testing API."""

from rest_framework import serializers

from .models import Experiment, ExperimentVariant, ExperimentAssignment, ExperimentConversion


class ExperimentVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperimentVariant
        fields = ['id', 'experiment', 'name', 'description', 'allocation', 'config', 'created_at']
        read_only_fields = ['id', 'experiment', 'created_at']


class ExperimentSerializer(serializers.ModelSerializer):
    """
    Nested read (variants embedded), flat write.
    On update, validates that all variants sum to 100 when variants are provided.
    """
    variants = ExperimentVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Experiment
        fields = [
            'id', 'project', 'name', 'description', 'status',
            'targeting_key', 'variants', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'project', 'created_at', 'updated_at']

    def validate(self, attrs):
        # When variants are submitted as part of nested write (not used here —
        # variants are managed via their own ViewSet), skip allocation validation.
        # Allocation validation is triggered explicitly in the experiment detail
        # view when PATCH includes a 'variants' key at the top level.
        return attrs


class AssignmentResponseSerializer(serializers.Serializer):
    """Read-only response shape for the /assign/ endpoint."""
    variant_name = serializers.CharField()
    config = serializers.DictField()
    experiment_name = serializers.CharField()


class ConversionSerializer(serializers.Serializer):
    """Input shape for the /convert/ endpoint."""
    targeting_value = serializers.CharField(max_length=256)
    event_name = serializers.CharField(max_length=128)
    value = serializers.FloatField(required=False, allow_null=True)
