"""Serializers for the Remote Config + A/B Testing API."""

from rest_framework import serializers
from .models import RemoteConfig, ConfigCondition, ConfigVersion, Experiment, ExperimentVariant


class RemoteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteConfig
        fields = [
            'id', 'project', 'key', 'value_type', 'default_value',
            'description', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'project', 'created_at', 'updated_at']

    def validate_key(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Config key must not be blank.')
        return value.strip()


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


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = [
            'id', 'project', 'name', 'description', 'status',
            'start_date', 'end_date', 'traffic_fraction', 'metric_event',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'project', 'created_at', 'updated_at']

    def validate_traffic_fraction(self, value):
        if not (0.0 <= value <= 1.0):
            raise serializers.ValidationError(
                'traffic_fraction must be between 0.0 and 1.0.'
            )
        return value


class ExperimentVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperimentVariant
        fields = [
            'id', 'experiment', 'name', 'description', 'is_control',
            'traffic_weight', 'config_overrides', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_traffic_weight(self, value):
        if value <= 0:
            raise serializers.ValidationError('traffic_weight must be greater than 0.')
        return value
