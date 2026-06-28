"""App Check token exchange and validation logic."""

import hashlib
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


def hash_token(token_str):
    return hashlib.sha256(str(token_str).encode()).hexdigest()


def get_token_expiry(minutes=60):
    return timezone.now() + timedelta(minutes=minutes)


def exchange_debug_token(project, raw_token, platform):
    """Exchange a debug token for an AppCheckToken."""
    from .models import DebugToken, AppCheckToken

    try:
        debug = DebugToken.objects.get(project=project, token=raw_token, is_active=True)
    except DebugToken.DoesNotExist:
        return None, 'Invalid or inactive debug token.'

    token_hash = hash_token(f"debug:{raw_token}:{timezone.now().isoformat()}")
    app_check_token = AppCheckToken.objects.create(
        project=project,
        token_hash=token_hash,
        platform=platform,
        app_id='debug',
        expires_at=get_token_expiry(minutes=3600),
    )
    return app_check_token, None


def validate_app_check_token(project, token_hash):
    """Validate an existing AppCheck token hash."""
    from .models import AppCheckToken
    try:
        token = AppCheckToken.objects.get(project=project, token_hash=token_hash)
        if not token.is_valid():
            return False, 'Token expired or revoked.'
        return True, None
    except AppCheckToken.DoesNotExist:
        return False, 'Token not found.'
