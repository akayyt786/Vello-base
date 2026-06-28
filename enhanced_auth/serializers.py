"""Serializers for enhanced auth endpoints."""

from django.contrib.auth.password_validation import validate_password as _validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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


# ---------------------------------------------------------------------------
# Anonymous account upgrade
# ---------------------------------------------------------------------------

class AnonymousUpgradeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})
        try:
            _validate_password(data['password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return data


class SetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({'new_password2': 'Passwords do not match.'})
        try:
            _validate_password(data['new_password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)})
        return data


class LinkEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
