"""
Custom throttle classes for hardening specific endpoints (e.g. login) against
brute-force / credential-stuffing attacks, without enabling global throttling.

These are applied per-action via @action(throttle_classes=[...]) rather than
through REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'], so only the endpoints that
explicitly reference them are rate-limited.
"""

from rest_framework.throttling import ScopedRateThrottle


class LoginRateThrottle(ScopedRateThrottle):
    """
    Rate-limits the login endpoint by client IP (ScopedRateThrottle keys on the
    request's cache_format, which for anonymous requests uses the client IP).
    Rate is configured via REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'].
    """
    scope = 'login'
