"""App Check token exchange and validation logic."""

import hashlib
import json
import logging
import time
from datetime import timedelta

import jwt
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
PLAY_INTEGRITY_DECODE_URL = "https://playintegrity.googleapis.com/v1/{package_name}:decodeIntegrityToken"
APPLE_DEVICECHECK_URL_PRODUCTION = "https://api.devicecheck.apple.com/v1/query_two_bits"
APPLE_DEVICECHECK_URL_DEVELOPMENT = "https://api.development.devicecheck.apple.com/v1/query_two_bits"
RECAPTCHA_SITEVERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
RECAPTCHA_ENTERPRISE_ASSESSMENT_URL = "https://recaptchaenterprise.googleapis.com/v1/projects/{project_id}/assessments"
DEFAULT_RECAPTCHA_MIN_SCORE = 0.5


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


def _google_service_account_access_token(service_account_info, scope):
    """
    Manual OAuth2 service-account JWT-bearer flow (RFC 7523). Avoids adding
    google-auth as a dependency -- PyJWT + cryptography (already required)
    are enough to sign the assertion and exchange it for an access token.
    """
    now = int(time.time())
    assertion = jwt.encode(
        {
            'iss': service_account_info['client_email'],
            'scope': scope,
            'aud': GOOGLE_OAUTH_TOKEN_URL,
            'iat': now,
            'exp': now + 3600,
        },
        service_account_info['private_key'],
        algorithm='RS256',
    )
    resp = requests.post(
        GOOGLE_OAUTH_TOKEN_URL,
        data={
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f'Google OAuth token exchange failed: {resp.text}')
    return resp.json()['access_token']


def verify_play_integrity_token(config, raw_token):
    """
    Verify an Android Play Integrity token via Google's decodeIntegrityToken
    REST API (https://developer.android.com/google/play/integrity/verdicts#decrypt-verify).

    config.config must hold:
      - package_name: the Android app's package name
      - service_account_key_encrypted: a GCP service-account JSON key (with
        Play Integrity API access) encrypted via app_check.encryption.encrypt_secret

    Returns (app_id, error).
    """
    from .encryption import decrypt_secret

    cfg = config.config or {}
    package_name = cfg.get('package_name')
    encrypted_key = cfg.get('service_account_key_encrypted')
    if not package_name or not encrypted_key:
        return None, 'Play Integrity config missing package_name or service_account_key.'

    try:
        service_account_info = json.loads(decrypt_secret(encrypted_key))
        access_token = _google_service_account_access_token(
            service_account_info, scope='https://www.googleapis.com/auth/playintegrity'
        )
        resp = requests.post(
            PLAY_INTEGRITY_DECODE_URL.format(package_name=package_name),
            headers={'Authorization': f'Bearer {access_token}'},
            json={'integrityToken': raw_token},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning('Play Integrity decode failed: %s', resp.text)
            return None, 'Invalid Play Integrity token.'

        payload = resp.json().get('tokenPayloadExternal', {})
        app_integrity = payload.get('appIntegrity', {}) or {}
        if app_integrity.get('appRecognitionVerdict') != 'PLAY_RECOGNIZED':
            return None, 'App failed Play Integrity recognition check.'

        device_integrity = payload.get('deviceIntegrity', {}) or {}
        if 'MEETS_DEVICE_INTEGRITY' not in (device_integrity.get('deviceRecognitionVerdict') or []):
            return None, 'Device failed Play Integrity recognition check.'

        return app_integrity.get('packageName', package_name), None
    except Exception as exc:
        logger.error('Play Integrity verification failed: %s', exc)
        return None, 'Play Integrity token verification failed.'


def verify_device_check_token(config, raw_token):
    """
    Verify an iOS DeviceCheck token via Apple's query_two_bits endpoint
    (https://developer.apple.com/documentation/devicecheck/accessing_and_modifying_per-device_data).

    config.config must hold:
      - key_id: the DeviceCheck key's Key ID (from the Apple Developer portal)
      - team_id: the Apple Developer Team ID
      - private_key_encrypted: the DeviceCheck .p8 private key (PEM), encrypted
        via app_check.encryption.encrypt_secret
      - environment (optional): "development" for sandbox/TestFlight builds,
        defaults to "production"

    A 200 response means Apple recognizes device_token as genuine; any other
    status means it's forged, expired, or malformed. Returns (app_id, error).
    """
    from .encryption import decrypt_secret

    cfg = config.config or {}
    key_id = cfg.get('key_id')
    team_id = cfg.get('team_id')
    encrypted_key = cfg.get('private_key_encrypted')
    if not key_id or not team_id or not encrypted_key:
        return None, 'DeviceCheck config missing key_id, team_id, or private_key.'

    try:
        private_key_pem = decrypt_secret(encrypted_key)
        now = int(time.time())
        assertion = jwt.encode(
            {'iss': team_id, 'iat': now},
            private_key_pem,
            algorithm='ES256',
            headers={'kid': key_id},
        )
        url = (
            APPLE_DEVICECHECK_URL_DEVELOPMENT
            if cfg.get('environment') == 'development'
            else APPLE_DEVICECHECK_URL_PRODUCTION
        )
        resp = requests.post(
            url,
            headers={'Authorization': f'Bearer {assertion}', 'Content-Type': 'application/json'},
            json={
                'device_token': raw_token,
                'transaction_id': hash_token(f'{raw_token}:{now}')[:32],
                'timestamp': now * 1000,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning('Apple DeviceCheck query failed (%s): %s', resp.status_code, resp.text)
            return None, 'Invalid DeviceCheck token.'
        return 'ios-device', None
    except Exception as exc:
        logger.error('DeviceCheck verification failed: %s', exc)
        return None, 'DeviceCheck token verification failed.'


def verify_recaptcha_v3_token(config, raw_token):
    """
    Verify a reCAPTCHA v3 token via Google's siteverify endpoint
    (https://developers.google.com/recaptcha/docs/verify).

    config.config must hold:
      - secret_key_encrypted: the reCAPTCHA v3 secret key, encrypted via
        app_check.encryption.encrypt_secret
      - min_score (optional): reject scores below this threshold, default 0.5

    Returns (app_id, error).
    """
    from .encryption import decrypt_secret

    cfg = config.config or {}
    encrypted_key = cfg.get('secret_key_encrypted')
    if not encrypted_key:
        return None, 'reCAPTCHA v3 config missing secret_key.'
    min_score = cfg.get('min_score', DEFAULT_RECAPTCHA_MIN_SCORE)

    try:
        secret_key = decrypt_secret(encrypted_key)
        resp = requests.post(
            RECAPTCHA_SITEVERIFY_URL,
            data={'secret': secret_key, 'response': raw_token},
            timeout=10,
        )
        if resp.status_code != 200:
            return None, 'Invalid reCAPTCHA token.'

        data = resp.json()
        if not data.get('success'):
            logger.warning('reCAPTCHA v3 verification failed: %s', data.get('error-codes'))
            return None, 'reCAPTCHA verification failed.'

        score = data.get('score', 0)
        if score < min_score:
            return None, f'reCAPTCHA score {score} below required minimum {min_score}.'

        return data.get('hostname', 'web'), None
    except Exception as exc:
        logger.error('reCAPTCHA v3 verification failed: %s', exc)
        return None, 'reCAPTCHA token verification failed.'


def verify_recaptcha_enterprise_token(config, raw_token):
    """
    Verify a reCAPTCHA Enterprise token via the createAssessment REST API
    (https://cloud.google.com/recaptcha/docs/create-assessment).

    config.config must hold:
      - gcp_project_id: the GCP project the reCAPTCHA Enterprise key belongs to
      - site_key: the reCAPTCHA Enterprise site key
      - api_key_encrypted: a GCP API key with the reCAPTCHA Enterprise API
        enabled, encrypted via app_check.encryption.encrypt_secret
      - min_score (optional): reject scores below this threshold, default 0.5

    Returns (app_id, error).
    """
    from .encryption import decrypt_secret

    cfg = config.config or {}
    gcp_project_id = cfg.get('gcp_project_id')
    site_key = cfg.get('site_key')
    encrypted_key = cfg.get('api_key_encrypted')
    if not gcp_project_id or not site_key or not encrypted_key:
        return None, 'reCAPTCHA Enterprise config missing gcp_project_id, site_key, or api_key.'
    min_score = cfg.get('min_score', DEFAULT_RECAPTCHA_MIN_SCORE)

    try:
        api_key = decrypt_secret(encrypted_key)
        resp = requests.post(
            RECAPTCHA_ENTERPRISE_ASSESSMENT_URL.format(project_id=gcp_project_id),
            params={'key': api_key},
            json={'event': {'token': raw_token, 'siteKey': site_key}},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning('reCAPTCHA Enterprise assessment failed: %s', resp.text)
            return None, 'Invalid reCAPTCHA Enterprise token.'

        data = resp.json()
        token_properties = data.get('tokenProperties', {}) or {}
        if not token_properties.get('valid'):
            reason = token_properties.get('invalidReason', 'unknown')
            return None, f'reCAPTCHA Enterprise token invalid: {reason}.'

        score = (data.get('riskAnalysis', {}) or {}).get('score', 0)
        if score < min_score:
            return None, f'reCAPTCHA Enterprise score {score} below required minimum {min_score}.'

        return site_key, None
    except Exception as exc:
        logger.error('reCAPTCHA Enterprise verification failed: %s', exc)
        return None, 'reCAPTCHA Enterprise token verification failed.'
