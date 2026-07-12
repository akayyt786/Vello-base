"""
Sentry error-tracking integration.

Designed to be safe to import and call in every environment — including
local dev and the test suite — where SENTRY_DSN is not configured. All
sentry_sdk imports happen lazily inside init_sentry() so this module never
fails to import, even if sentry-sdk isn't installed.
"""

import os
import logging

logger = logging.getLogger(__name__)


def init_sentry():
    """
    Initialize Sentry error tracking if SENTRY_DSN is configured.

    Reads SENTRY_DSN from the environment. If it's not set (empty or
    missing), this is a no-op and returns False immediately — safe to call
    even when sentry-sdk isn't fully configured (e.g. most dev/test
    environments).

    If SENTRY_DSN is set, initializes sentry_sdk with the Django
    integration and returns True.

    Returns:
        bool: True if Sentry was initialized, False otherwise.
    """
    dsn = os.environ.get('SENTRY_DSN')
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[DjangoIntegration()],
            environment=os.environ.get('SENTRY_ENVIRONMENT', 'production'),
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            send_default_pii=False,
        )
        return True
    except ImportError:
        logger.warning(
            'SENTRY_DSN is set but sentry-sdk is not installed; skipping Sentry initialization.'
        )
        return False
