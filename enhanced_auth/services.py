"""Business logic helpers for enhanced auth."""

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_otp(length=6):
    return ''.join(str(secrets.randbelow(10)) for _ in range(length))


def send_sms(phone_number, message):
    """Send SMS via Twilio if configured, otherwise log."""
    twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    if twilio_sid:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number,
            )
            logger.info("SMS sent to %s", phone_number)
        except Exception as exc:
            logger.error("SMS send failed to %s: %s", phone_number, exc)
            raise
    else:
        logger.info("[DEV] SMS to %s: %s", phone_number, message)


def send_magic_link_email(user, token, redirect_url):
    """Send magic link email using Django's email backend."""
    from django.core.mail import send_mail
    base_url = getattr(settings, 'MAGIC_LINK_BASE_URL', 'http://localhost:8000')
    link = f"{base_url}/api/v1/auth/magic-link/verify/?token={token}"
    if redirect_url:
        link += f"&next={redirect_url}"
    subject = "Your login link"
    message = f"Click to log in: {link}\n\nThis link expires in 15 minutes."
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        logger.info("Magic link sent to %s", user.email)
    except Exception as exc:
        logger.error("Magic link email failed for %s: %s", user.email, exc)
        raise


def hash_token(token_str):
    return hashlib.sha256(str(token_str).encode()).hexdigest()


def get_otp_expiry():
    return timezone.now() + timedelta(minutes=10)


def get_magic_link_expiry():
    return timezone.now() + timedelta(minutes=15)


def get_custom_token_expiry():
    return timezone.now() + timedelta(hours=1)
