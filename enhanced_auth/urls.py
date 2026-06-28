"""URL configuration for enhanced_auth app."""

from django.urls import path
from . import views

app_name = 'enhanced_auth'

urlpatterns = [
    # Phone OTP
    path('phone/send-otp/', views.SendOTPView.as_view(), name='phone-send-otp'),
    path('phone/verify-otp/', views.VerifyOTPView.as_view(), name='phone-verify-otp'),

    # MFA — TOTP
    path('mfa/enroll/totp/', views.EnrollTOTPView.as_view(), name='mfa-enroll-totp'),
    path('mfa/confirm/totp/', views.ConfirmTOTPView.as_view(), name='mfa-confirm-totp'),
    path('mfa/verify/totp/', views.VerifyTOTPView.as_view(), name='mfa-verify-totp'),

    # MFA — SMS
    path('mfa/enroll/sms/', views.EnrollSMSView.as_view(), name='mfa-enroll-sms'),
    path('mfa/confirm/sms/', views.ConfirmSMSView.as_view(), name='mfa-confirm-sms'),
    path('mfa/verify/sms/', views.VerifySMSView.as_view(), name='mfa-verify-sms'),
    path('mfa/send-sms-code/<uuid:device_id>/', views.SendSMSCodeView.as_view(), name='mfa-send-sms-code'),

    # MFA device management
    path('mfa/devices/', views.MFADeviceListView.as_view(), name='mfa-devices'),
    path('mfa/devices/<uuid:device_id>/', views.MFADeviceDeleteView.as_view(), name='mfa-device-delete'),

    # Passwordless Magic Link
    path('magic-link/send/', views.SendMagicLinkView.as_view(), name='magic-link-send'),
    path('magic-link/verify/', views.VerifyMagicLinkView.as_view(), name='magic-link-verify'),

    # Anonymous account upgrade / password management / email linking
    path('upgrade/', views.AnonymousUpgradeView.as_view(), name='anonymous-upgrade'),
    path('set-password/', views.SetPasswordView.as_view(), name='set-password'),
    path('link-email/', views.LinkEmailView.as_view(), name='link-email'),
    path('verify-email-change/', views.VerifyEmailChangeView.as_view(), name='verify-email-change'),
]
