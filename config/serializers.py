"""Serializers for the Remote Config API."""

from rest_framework import serializers
from .models import RemoteConfig, ConfigCondition, ConfigVersion


class RemoteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteConfig
        fields = [
            'id', 'project', 'key', 'value_type', 'default_value',
            'description', 'is_active', 'is_secret', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'project', 'created_at', 'updated_at']

    def validate_key(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Config key must not be blank.')
        return value.strip()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Mask the secret value in list responses; expose it only on explicit retrieve.
        if instance.is_secret:
            view = self.context.get('view')
            action = getattr(view, 'action', None)
            if action == 'list':
                raw = data.get('default_value', '')
                data['default_value'] = (raw[:4] + '****') if len(raw) > 4 else '****'
        return data


class ConfigConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigCondition
        fields = [
            'id', 'config', 'name', 'condition_type', 'condition_params',
            'value', 'priority', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ConfigVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigVersion
        fields = [
            'id', 'project', 'version_number', 'params',
            'description', 'published_by', 'published_at',
        ]
        read_only_fields = ['id', 'project', 'version_number', 'published_at']
