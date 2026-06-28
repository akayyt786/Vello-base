from rest_framework import serializers
from .models import RemoteConfigParameter


class RemoteConfigParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteConfigParameter
        fields = ['id', 'key', 'value', 'param_type', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RemoteConfigFetchSerializer(serializers.Serializer):
    """Returned by the client-facing fetch endpoint — typed values."""
    key = serializers.CharField()
    value = serializers.SerializerMethodField()
    param_type = serializers.CharField()

    def get_value(self, obj):
        return obj.cast_value()
