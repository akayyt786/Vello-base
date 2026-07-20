"""Serializers for App Check API."""

from rest_framework import serializers
from .models import AppCheckConfig, AppCheckToken, DebugToken


class AppCheckConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppCheckConfig
        fields = ['id', 'platform', 'provider', 'config', 'is_enabled', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        """Mask encrypted provider secrets -- never echo ciphertext back through the API."""
        data = super().to_representation(instance)
        config = data.get('config')
        if isinstance(config, dict):
            data['config'] = {
                k: ('***' if k.endswith('_encrypted') else v) for k, v in config.items()
            }
        return data


class AppCheckTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppCheckToken
        fields = ['id', 'platform', 'app_id', 'is_revoked', 'expires_at', 'issued_at']
        read_only_fields = ['id', 'is_revoked', 'expires_at', 'issued_at']


class DebugTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebugToken
        fields = ['id', 'name', 'token', 'is_active', 'created_at']
        read_only_fields = ['id', 'token', 'created_at']


class ExchangeTokenSerializer(serializers.Serializer):
    raw_token = serializers.CharField()
    platform = serializers.ChoiceField(choices=['web', 'android', 'ios'])
    provider = serializers.ChoiceField(
        choices=['recaptcha_v3', 'recaptcha_enterprise', 'play_integrity', 'device_check', 'debug']
    )
