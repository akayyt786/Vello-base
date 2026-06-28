"""Serializers for enhanced auth endpoints."""

from rest_framework import serializers
from .models import PhoneVerification, MFADevice, MagicLink, CustomToken


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        value = value.strip()
        if not value.startswith('+'):
            raise serializers.ValidationError('Phone number must be in E.164 format (e.g. +12125551234).')
        return value


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(min_length=6, max_length=6, write_only=True)


class EnrollTOTPSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, default='My Authenticator')


class ConfirmTOTPSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    totp_code = serializers.CharField(min_length=6, max_length=6, write_only=True)


class VerifyTOTPSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    totp_code = serializers.CharField(min_length=6, max_length=6, write_only=True)


class EnrollSMSSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=100, default='My Phone')

    def validate_phone_number(self, value):
        value = value.strip()
        if not value.startswith('+'):
            raise serializers.ValidationError('Phone number must be in E.164 format.')
        return value


class ConfirmSMSSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    code = serializers.CharField(min_length=6, max_length=6, write_only=True)


class VerifySMSSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    code = serializers.CharField(min_length=6, max_length=6, write_only=True)


class MFADeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MFADevice
        fields = ['id', 'method', 'name', 'phone_number', 'is_active', 'confirmed_at', 'created_at']
        read_only_fields = ['id', 'is_active', 'confirmed_at', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Never expose TOTP secret in responses
        data.pop('totp_secret', None)
        return data


class SendMagicLinkSerializer(serializers.Serializer):
    email = serializers.EmailField()
    redirect_url = serializers.URLField(required=False, default='')


class IssueCustomTokenSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=255)
    claims = serializers.DictField(required=False, default=dict)
