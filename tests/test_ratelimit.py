"""
Tests for login rate limiting (ScopedRateThrottle applied to AuthViewSet.login only).

Confirms:
  1. The login endpoint throttles after DEFAULT_THROTTLE_RATES['login'] (5/min)
     requests from the same client, returning 429.
  2. An unrelated endpoint is NOT throttled, proving the throttle is scoped to
     the login action only and not applied globally.

The DRF cache-based throttle needs a clean cache to get deterministic counts.
tests/conftest.py overrides CACHES with a LocMemCache shared for the entire
test session (see pytest_configure), so we explicitly clear it at the start
of each test here to avoid interference from request counts left behind by
other tests running earlier in the same session.
"""

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestLoginRateLimit:
    """Tests for the login-scoped rate throttle."""

    def test_login_throttled_after_five_attempts(self, api_client, test_user):
        """
        The 6th login attempt within the throttle window must be rejected
        with 429, while the first 5 (invalid-credential) attempts must be
        handled normally (401), proving the throttle kicks in at exactly the
        configured 'login': '5/min' rate.
        """
        cache.clear()

        url = reverse('auth-login')
        data = {
            'email': test_user.email,
            'password': 'wrong-password',
        }

        for attempt in range(1, 6):
            response = api_client.post(url, data)
            assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS, (
                f"Attempt {attempt} was throttled prematurely; expected the "
                f"first 5 attempts to be allowed through (401 for bad creds)."
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # 6th attempt within the same window must be throttled.
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_unrelated_endpoint_not_throttled(self, authenticated_client, test_project):
        """
        Hammering an unrelated authenticated endpoint many more times than the
        login throttle's threshold must never return 429 — proving throttling
        was applied only to AuthViewSet.login, not globally via
        DEFAULT_THROTTLE_CLASSES.
        """
        cache.clear()

        url = reverse('project-list')

        for attempt in range(1, 21):
            response = authenticated_client.get(url)
            assert response.status_code == status.HTTP_200_OK, (
                f"Attempt {attempt} to unrelated endpoint returned "
                f"{response.status_code}, expected 200."
            )
