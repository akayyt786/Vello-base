import secrets
from rest_framework import serializers
from .models import WebhookEndpoint, WebhookDelivery, WEBHOOK_EVENTS
from .ssrf import validate_webhook_url


class WebhookEndpointSerializer(serializers.ModelSerializer):
    secret = serializers.CharField(read_only=True)
    available_events = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WebhookEndpoint
        fields = ['id', 'url', 'secret', 'events', 'is_active', 'description', 'available_events', 'created_at', 'updated_at']
        read_only_fields = ['id', 'secret', 'created_at', 'updated_at']

    def get_available_events(self, obj):
        return [e[0] for e in WEBHOOK_EVENTS]

    def validate_url(self, value):
        return validate_webhook_url(value)

    def validate_events(self, value):
        valid = {e[0] for e in WEBHOOK_EVENTS} | {'*'}
        invalid = set(value) - valid
        if invalid:
            raise serializers.ValidationError(f"Unknown events: {invalid}")
        return value

    def create(self, validated_data):
        validated_data['secret'] = secrets.token_hex(32)
        return super().create(validated_data)


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = ['id', 'event_type', 'status', 'response_status', 'latency_ms', 'attempt_count', 'delivered_at', 'created_at']
