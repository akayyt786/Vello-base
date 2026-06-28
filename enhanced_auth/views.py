"""
Enhanced Auth API views.

Phone OTP:
  POST /api/v1/auth/phone/send-otp/        — send OTP to phone
  POST /api/v1/auth/phone/verify-otp/      — verify OTP, return JWT

MFA:
  GET  /api/v1/auth/mfa/devices/           — list user MFA devices
  POST /api/v1/auth/mfa/enroll/totp/       — start TOTP enrollment (returns secret + URI)
  POST /api/v1/auth/mfa/confirm/totp/      — confirm TOTP (activate device)
  POST /api/v1/auth/mfa/verify/totp/       — verify TOTP code (returns JWT)
  POST /api/v1/auth/mfa/enroll/sms/        — enroll SMS MFA device
  POST /api/v1/auth/mfa/confirm/sms/       — confirm SMS device with code
  POST /api/v1/auth/mfa/verify/sms/        — send + verify SMS code (returns JWT)
  DELETE /api/v1/auth/mfa/devices/{id}/    — delete MFA device

Magic Link:
  POST /api/v1/auth/magic-link/send/       — email a login link
  GET  /api/v1/auth/magic-link/verify/     — verify token, return JWT

Custom Tokens (project-scoped):
  POST /api/projects/{project_id}/auth/custom-token/  — issue custom JWT
"""

import logging
import time

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from .models import PhoneVerification, MFADevice, MFASMSCode, MagicLink, CustomToken
from .serializers import (
    SendOTPSerializer, VerifyOTPSerializer,
    EnrollTOTPSerializer, ConfirmTOTPSerializer, VerifyTOTPSerializer,
    EnrollSMSSerializer, ConfirmSMSSerializer, VerifySMSSerializer,
    MFADeviceSerializer, SendMagicLinkSerializer, IssueCustomTokenSerializer,
    AnonymousUpgradeSerializer, SetPasswordSerializer, LinkEmailSerializer,
)
from .services import (
    generate_otp, send_sms, send_magic_link_email, hash_token, hash_otp,
    get_otp_expiry, get_magic_link_expiry, get_custom_token_expiry,
)

logger = logging.getLogger(__name__)
User = get_user_model()

MAX_OTP_ATTEMPTS = 5


def _jwt_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


# ---------------------------------------------------------------------------
# Phone OTP
# ---------------------------------------------------------------------------

class SendOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SendOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data['phone_number']

        # Rate limit: max 3 OTP SMS per phone number per hour.
        rate_key = f"sms_otp_rate:{phone}"
        sms_count = cache.get(rate_key, 0)
        if sms_count >= 3:
            return Response(
                {'error': 'Too many OTP requests. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp = generate_otp()
        PhoneVerification.objects.create(
            user=request.user,
            phone_number=phone,
            otp_code=hash_otp(otp),  # store hash, never plaintext
            expires_at=get_otp_expiry(),
        )
        try:
            send_sms(phone, f"Your OwnFirebase OTP is: {otp}")
        except Exception:
            return Response({'error': 'Failed to send SMS.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        cache.set(rate_key, sms_count + 1, 3600)
        return Response({'detail': 'OTP sent.', 'phone_number': phone}, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = VerifyOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data['phone_number']
        code = ser.validated_data['otp_code']

        verif = PhoneVerification.objects.filter(
            user=request.user,
            phone_number=phone,
            status=PhoneVerification.STATUS_PENDING,
        ).order_by('-created_at').first()

        if not verif:
            return Response({'error': 'No pending OTP for this number.'}, status=status.HTTP_400_BAD_REQUEST)

        if verif.is_expired():
            verif.status = PhoneVerification.STATUS_EXPIRED
            verif.save(update_fields=['status'])
            return Response({'error': 'OTP expired.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check attempt limit BEFORE incrementing to prevent off-by-one bypass.
        if verif.attempts >= MAX_OTP_ATTEMPTS:
            verif.status = PhoneVerification.STATUS_EXPIRED
            verif.save(update_fields=['status', 'attempts'])
            return Response({'error': 'Too many attempts.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Compare against stored hash — never compare plaintext OTPs.
        if verif.otp_code != hash_otp(code):
            verif.attempts += 1
            verif.save(update_fields=['attempts'])
            return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        verif.status = PhoneVerification.STATUS_VERIFIED
        verif.save(update_fields=['status', 'attempts'])
        return Response({'detail': 'Phone verified.', 'phone_number': phone}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# MFA — TOTP
# ---------------------------------------------------------------------------

class EnrollTOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = EnrollTOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            import pyotp
        except ImportError:
            return Response({'error': 'pyotp not installed.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        secret = pyotp.random_base32()
        device = MFADevice.objects.create(
            user=request.user,
            method=MFADevice.METHOD_TOTP,
            name=ser.validated_data['name'],
            totp_secret=secret,
            is_active=False,
        )
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=request.user.email,
            issuer_name='OwnFirebase',
        )
        return Response({
            'device_id': str(device.id),
            'secret': secret,
            'provisioning_uri': provisioning_uri,
        }, status=status.HTTP_201_CREATED)


class ConfirmTOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ConfirmTOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        device = get_object_or_404(
            MFADevice,
            id=ser.validated_data['device_id'],
            user=request.user,
            method=MFADevice.METHOD_TOTP,
            is_active=False,
        )

        try:
            import pyotp
        except ImportError:
            return Response({'error': 'pyotp not installed.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        totp = pyotp.TOTP(device.totp_secret)
        if not totp.verify(ser.validated_data['totp_code'], valid_window=1):
            return Response({'error': 'Invalid TOTP code.'}, status=status.HTTP_400_BAD_REQUEST)

        device.is_active = True
        device.confirmed_at = timezone.now()
        device.save(update_fields=['is_active', 'confirmed_at'])
        return Response({'detail': 'TOTP device confirmed.', 'device_id': str(device.id)})


class VerifyTOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = VerifyTOTPSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        device = get_object_or_404(
            MFADevice,
            id=ser.validated_data['device_id'],
            user=request.user,
            method=MFADevice.METHOD_TOTP,
            is_active=True,
        )

        try:
            import pyotp
        except ImportError:
            return Response({'error': 'pyotp not installed.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        totp = pyotp.TOTP(device.totp_secret)
        code = ser.validated_data['totp_code']
        current_counter = int(time.time() // 30)

        if not totp.verify(code, valid_window=1):
            return Response({'error': 'Invalid TOTP code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine the exact counter that matched (window covers current-1..current+1).
        # Storing matched_counter prevents replaying a look-ahead code in its real window.
        matched_counter = next(
            (current_counter + d for d in (-1, 0, 1)
             if totp.at((current_counter + d) * 30) == code),
            current_counter,
        )
        if device.last_used_counter >= matched_counter:
            return Response({'error': 'TOTP code already used.'}, status=status.HTTP_400_BAD_REQUEST)
        device.last_used_counter = matched_counter
        device.save(update_fields=['last_used_counter'])

        return Response(_jwt_for_user(request.user))


# ---------------------------------------------------------------------------
# MFA — SMS
# ---------------------------------------------------------------------------

class EnrollSMSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = EnrollSMSSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        device = MFADevice.objects.create(
            user=request.user,
            method=MFADevice.METHOD_SMS,
            name=ser.validated_data['name'],
            phone_number=ser.validated_data['phone_number'],
            is_active=False,
        )

        code = generate_otp()
        from datetime import timedelta
        MFASMSCode.objects.create(
            device=device,
            code=hash_otp(code),  # store hash, never plaintext
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        try:
            send_sms(device.phone_number, f"Your OwnFirebase MFA code: {code}")
        except Exception:
            device.delete()
            return Response({'error': 'Failed to send SMS.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'device_id': str(device.id), 'detail': 'Verification code sent.'}, status=status.HTTP_201_CREATED)


class ConfirmSMSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ConfirmSMSSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        device = get_object_or_404(
            MFADevice,
            id=ser.validated_data['device_id'],
            user=request.user,
            method=MFADevice.METHOD_SMS,
            is_active=False,
        )

        sms_code = device.sms_codes.filter(is_used=False).order_by('-created_at').first()
        if not sms_code or sms_code.is_expired():
            return Response({'error': 'Code expired. Re-enroll to get a new code.'}, status=status.HTTP_400_BAD_REQUEST)

        if sms_code.code != hash_otp(ser.validated_data['code']):
            return Response({'error': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)

        sms_code.is_used = True
        sms_code.save(update_fields=['is_used'])
        device.is_active = True
        device.confirmed_at = timezone.now()
        device.save(update_fields=['is_active', 'confirmed_at'])
        return Response({'detail': 'SMS MFA device confirmed.', 'device_id': str(device.id)})


class VerifySMSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = VerifySMSSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        device = get_object_or_404(
            MFADevice,
            id=ser.validated_data['device_id'],
            user=request.user,
            method=MFADevice.METHOD_SMS,
            is_active=True,
        )

        # Find unused code matching the submitted code hash.
        valid = device.sms_codes.filter(
            is_used=False,
            code=hash_otp(ser.validated_data['code']),
        ).order_by('-created_at').first()

        if not valid or valid.is_expired():
            return Response({'error': 'Invalid or expired code.'}, status=status.HTTP_400_BAD_REQUEST)

        valid.is_used = True
        valid.save(update_fields=['is_used'])
        return Response(_jwt_for_user(request.user))


class SendSMSCodeView(APIView):
    """Send a new SMS code to an active SMS MFA device."""
    permission_classes = [IsAuthenticated]

    def post(self, request, device_id):
        device = get_object_or_404(
            MFADevice,
            id=device_id,
            user=request.user,
            method=MFADevice.METHOD_SMS,
            is_active=True,
        )

        # Rate limit: max 3 MFA SMS per phone number per hour.
        rate_key = f"sms_mfa_rate:{device.phone_number}"
        sms_count = cache.get(rate_key, 0)
        if sms_count >= 3:
            return Response(
                {'error': 'Too many SMS code requests. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        from datetime import timedelta
        code = generate_otp()
        MFASMSCode.objects.create(
            device=device,
            code=hash_otp(code),  # store hash, never plaintext
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        try:
            send_sms(device.phone_number, f"Your OwnFirebase MFA code: {code}")
        except Exception:
            return Response({'error': 'Failed to send SMS.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        cache.set(rate_key, sms_count + 1, 3600)
        return Response({'detail': 'Code sent.'})


class MFADeviceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices = MFADevice.objects.filter(user=request.user, is_active=True)
        return Response(MFADeviceSerializer(devices, many=True).data)


class MFADeviceDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, device_id):
        device = get_object_or_404(MFADevice, id=device_id, user=request.user)
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Magic Link (Passwordless Email)
# ---------------------------------------------------------------------------

class SendMagicLinkView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = SendMagicLinkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data['email']
        redirect_url = ser.validated_data.get('redirect_url', '')

        # Rate limit: max 3 magic links per email per hour.
        rate_key = f"magic_link_rate:{email.lower()}"
        ml_count = cache.get(rate_key, 0)
        if ml_count >= 3:
            return Response(
                {'error': 'Too many login link requests. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Don't reveal if email exists — but still burn a rate-limit slot.
            cache.set(rate_key, ml_count + 1, 3600)
            return Response({'detail': 'If that email is registered, a login link has been sent.'})

        link = MagicLink.objects.create(
            user=user,
            redirect_url=redirect_url,
            expires_at=get_magic_link_expiry(),
        )
        try:
            send_magic_link_email(user, str(link.token), redirect_url)
        except Exception:
            link.delete()
            return Response({'error': 'Failed to send email.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        cache.set(rate_key, ml_count + 1, 3600)
        return Response({'detail': 'If that email is registered, a login link has been sent.'})


class VerifyMagicLinkView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # select_for_update() inside atomic() prevents TOCTOU: two concurrent
        # requests cannot both read is_used=False and both issue tokens.
        with transaction.atomic():
            try:
                link = MagicLink.objects.select_for_update().get(
                    token=token, is_used=False,
                )
            except MagicLink.DoesNotExist:
                return Response(
                    {'error': 'Link not found or already used.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if link.is_expired():
                return Response({'error': 'Link expired.'}, status=status.HTTP_400_BAD_REQUEST)

            link.is_used = True
            link.save(update_fields=['is_used'])
            user = link.user  # capture while inside atomic block

        return Response({
            'detail': 'Login successful.',
            **_jwt_for_user(user),
        })


# ---------------------------------------------------------------------------
# Custom Tokens (project-scoped)
# ---------------------------------------------------------------------------

class IssueCustomTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id, is_active=True)
        membership = get_object_or_404(ProjectMembership, project=project, user=request.user)
        if membership.role not in ('owner', 'editor'):
            return Response({'error': 'Editor role required.'}, status=status.HTTP_403_FORBIDDEN)

        ser = IssueCustomTokenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        import jwt
        import uuid as _uuid
        from django.conf import settings as _settings

        token_id = str(_uuid.uuid4())
        payload = {
            'jti': token_id,
            'project_id': str(project.id),
            'uid': ser.validated_data['uid'],
            'claims': ser.validated_data['claims'],
            'exp': get_custom_token_expiry().timestamp(),
        }
        secret = getattr(_settings, 'JWT_SIGNING_KEY', _settings.SECRET_KEY)
        token = jwt.encode(payload, secret, algorithm='HS256')
        token_hash = hash_token(token)

        CustomToken.objects.create(
            project=project,
            issued_by=request.user,
            uid=ser.validated_data['uid'],
            claims=ser.validated_data['claims'],
            token_hash=token_hash,
            expires_at=get_custom_token_expiry(),
        )

        return Response({'token': token, 'expires_at': get_custom_token_expiry().isoformat()}, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Anonymous account upgrade / password management / email linking
# ---------------------------------------------------------------------------

def _is_anonymous_user(user):
    """Return True if the user is an anonymous (guest) account."""
    if user.username.startswith('anon_'):
        return True
    try:
        return user.profile.sign_in_provider == 'anonymous'
    except UserProfile.DoesNotExist:
        return False


def _unique_username_for_email(email, exclude_pk):
    """
    Derive a unique username from an email address.
    Falls back to email+integer suffix if the base is already taken.
    """
    base = email[:150]
    username = base
    i = 1
    while User.objects.filter(username=username).exclude(pk=exclude_pk).exists():
        suffix = str(i)
        username = base[: 150 - len(suffix)] + suffix
        i += 1
    return username


class AnonymousUpgradeView(APIView):
    """
    POST /api/v1/auth/upgrade/
    Upgrade an anonymous account to a permanent email/password account.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = AnonymousUpgradeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = request.user

        if not _is_anonymous_user(user):
            return Response(
                {'detail': 'Account already has credentials.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = ser.validated_data['email']

        # Validate email not already taken by another user.
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            return Response(
                {'email': 'This email is already in use.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_username = _unique_username_for_email(email, exclude_pk=user.pk)

        with transaction.atomic():
            user.email = email
            user.username = new_username
            user.set_password(ser.validated_data['password'])
            user.save(update_fields=['email', 'username', 'password'])

            try:
                profile = user.profile
                profile.sign_in_provider = 'password'
                profile.save(update_fields=['sign_in_provider'])
            except UserProfile.DoesNotExist:
                pass

        return Response({
            'detail': 'Account upgraded successfully.',
            **_jwt_for_user(user),
        }, status=status.HTTP_200_OK)


class SetPasswordView(APIView):
    """
    POST /api/v1/auth/set-password/
    Set or change the account password. If the user has no usable password
    (e.g. OAuth-only account), current_password may be omitted.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = SetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = request.user
        current_password = ser.validated_data.get('current_password', '')

        # If user already has a usable password, require current_password to match.
        if user.has_usable_password():
            if not current_password:
                return Response(
                    {'current_password': 'Current password is required.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not user.check_password(current_password):
                return Response(
                    {'current_password': 'Incorrect password.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user.set_password(ser.validated_data['new_password'])
        user.save(update_fields=['password'])

        return Response({'detail': 'Password updated.'}, status=status.HTTP_200_OK)


class LinkEmailView(APIView):
    """
    POST /api/v1/auth/link-email/
    Initiate email-change/link flow. Sends a verification token to the requested
    address; the email is NOT updated until the token is confirmed via
    VerifyEmailChangeView. This prevents account takeover via unverified email claim.
    """
    permission_classes = [IsAuthenticated]

    _CACHE_TTL = 900  # 15 minutes

    def post(self, request):
        ser = LinkEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        email = ser.validated_data['email']

        if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
            return Response(
                {'email': 'This email is already in use.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import uuid as _uuid
        token = str(_uuid.uuid4())
        cache_key = f'email_change:{token}'
        cache.set(cache_key, {'user_id': request.user.pk, 'email': email}, timeout=self._CACHE_TTL)

        # Send verification email to the *new* address.
        try:
            from django.core.mail import send_mail
            from django.conf import settings as _settings
            base_url = getattr(_settings, 'MAGIC_LINK_BASE_URL', 'http://localhost:8000')
            verify_url = f"{base_url}/api/v1/auth/verify-email-change/?token={token}"
            send_mail(
                subject='Confirm your new email address',
                message=f'Click to confirm: {verify_url}\n\nThis link expires in 15 minutes.',
                from_email=_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except Exception as exc:
            logger.error('Email change verification email failed for user %s: %s', request.user.pk, exc)
            return Response(
                {'detail': 'Failed to send verification email. Please try again.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {'detail': 'Verification email sent. Check your inbox to confirm the new address.'},
            status=status.HTTP_200_OK,
        )


class VerifyEmailChangeView(APIView):
    """
    GET /api/v1/auth/verify-email-change/?token=<uuid>
    Confirm a pending email change initiated by LinkEmailView.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '').strip()
        if not token:
            return Response({'error': 'Token required.'}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f'email_change:{token}'
        pending = cache.get(cache_key)
        if not pending:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = pending['user_id']
        new_email = pending['email']

        # Recheck uniqueness at confirmation time (race: another user may have claimed it).
        if User.objects.filter(email__iexact=new_email).exclude(pk=user_id).exists():
            cache.delete(cache_key)
            return Response(
                {'error': 'This email address is already in use.'},
                status=status.HTTP_409_CONFLICT,
            )

        user = User.objects.filter(pk=user_id).first()
        if not user:
            cache.delete(cache_key)
            return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)

        user.email = new_email
        user.save(update_fields=['email'])
        cache.delete(cache_key)

        return Response({'detail': 'Email address updated successfully.'}, status=status.HTTP_200_OK)
