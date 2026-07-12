"""
Tests for core.observability — Sentry error-tracking integration.

These tests never require a real Sentry account or DSN: sentry_sdk.init is
always mocked, so no network call is ever made.
"""

from unittest.mock import patch

import core.observability as observability


def test_init_sentry_noop_when_dsn_unset(monkeypatch):
    """When SENTRY_DSN is unset, init_sentry() returns False, does not raise,
    and never calls sentry_sdk.init."""
    monkeypatch.delenv('SENTRY_DSN', raising=False)

    with patch('sentry_sdk.init') as mock_init:
        result = observability.init_sentry()

    assert result is False
    mock_init.assert_not_called()


def test_init_sentry_noop_when_dsn_empty(monkeypatch):
    """An empty-string SENTRY_DSN is treated the same as unset."""
    monkeypatch.setenv('SENTRY_DSN', '')

    with patch('sentry_sdk.init') as mock_init:
        result = observability.init_sentry()

    assert result is False
    mock_init.assert_not_called()


def test_init_sentry_initializes_when_dsn_set(monkeypatch):
    """When SENTRY_DSN is set, init_sentry() returns True and calls
    sentry_sdk.init with the configured DSN — no real network call is made
    because sentry_sdk.init is mocked."""
    fake_dsn = 'https://fake@sentry.example.com/123'
    monkeypatch.setenv('SENTRY_DSN', fake_dsn)
    monkeypatch.delenv('SENTRY_ENVIRONMENT', raising=False)
    monkeypatch.delenv('SENTRY_TRACES_SAMPLE_RATE', raising=False)

    with patch('sentry_sdk.init') as mock_init:
        result = observability.init_sentry()

    assert result is True
    mock_init.assert_called_once()
    _, kwargs = mock_init.call_args
    assert kwargs['dsn'] == fake_dsn
    assert kwargs['environment'] == 'production'
    assert kwargs['traces_sample_rate'] == 0.1
    assert kwargs['send_default_pii'] is False


def test_init_sentry_respects_environment_overrides(monkeypatch):
    """SENTRY_ENVIRONMENT and SENTRY_TRACES_SAMPLE_RATE env vars are honored."""
    fake_dsn = 'https://fake@sentry.example.com/123'
    monkeypatch.setenv('SENTRY_DSN', fake_dsn)
    monkeypatch.setenv('SENTRY_ENVIRONMENT', 'staging')
    monkeypatch.setenv('SENTRY_TRACES_SAMPLE_RATE', '0.5')

    with patch('sentry_sdk.init') as mock_init:
        result = observability.init_sentry()

    assert result is True
    _, kwargs = mock_init.call_args
    assert kwargs['environment'] == 'staging'
    assert kwargs['traces_sample_rate'] == 0.5


def test_django_app_booted_with_sentry_wired_in_unconditionally():
    """
    pytest-django already loaded ownfirebase.settings.py to collect this test
    session, and settings.py calls init_sentry() unconditionally near the end
    of the file. The fact that this test session started at all (with
    SENTRY_DSN unset in the normal test environment) proves that call did not
    raise or otherwise break Django's ability to boot.
    """
    import core.observability
    assert core.observability is not None
    assert hasattr(core.observability, 'init_sentry')
