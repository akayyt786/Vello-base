"""Serializers for the Analytics API."""

from rest_framework import serializers
from .models import Event, UserProperty, ConversionEvent


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'id', 'project',
            'user_id', 'session_id',
            'event_name', 'event_params',
            'platform', 'app_version', 'device_id',
            'geo_country', 'geo_city',
            'occurred_at', 'created_at',
        ]
        read_only_fields = ['id', 'project', 'created_at']

    def validate_event_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('event_name must not be blank.')
        return value.strip()

    def validate_occurred_at(self, value):
        if value is None:
            raise serializers.ValidationError('occurred_at is required.')
        return value


class UserPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProperty
        fields = ['id', 'project', 'user_id', 'name', 'value', 'updated_at']
        read_only_fields = ['id', 'project', 'updated_at']

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Property name must not be blank.')
        return value.strip()


class ConversionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionEvent
        fields = ['id', 'project', 'event_name', 'created_at']
        read_only_fields = ['id', 'project', 'created_at']

    def validate_event_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('event_name must not be blank.')
        return value.strip()
