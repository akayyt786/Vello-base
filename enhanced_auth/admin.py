from django.contrib import admin
from .models import PhoneVerification, MFADevice, MagicLink, CustomToken


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'user', 'status', 'expires_at', 'created_at']
    list_filter = ['status']


@admin.register(MFADevice)
class MFADeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'method', 'name', 'is_active', 'confirmed_at']
    list_filter = ['method', 'is_active']


@admin.register(MagicLink)
class MagicLinkAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_used', 'expires_at', 'created_at']


@admin.register(CustomToken)
class CustomTokenAdmin(admin.ModelAdmin):
    list_display = ['project', 'uid', 'issued_by', 'expires_at', 'created_at']
