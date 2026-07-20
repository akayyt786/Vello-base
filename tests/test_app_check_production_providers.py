"""
Tests for the real (non-debug) App Check providers: Play Integrity (Android),
DeviceCheck (iOS), reCAPTCHA v3, and reCAPTCHA Enterprise (both web). Covers:
  - app_check.encryption: Fernet round-trip for stored secrets
  - app_check.services.verify_play_integrity_token / verify_device_check_token:
    real RSA/EC-signed JWT assertions against a mocked HTTP layer (only the
    network call is mocked -- the crypto is real)
  - app_check.services.verify_recaptcha_v3_token / verify_recaptcha_enterprise_token:
    score-threshold and validity-flag branch logic against a mocked HTTP layer
  - ExchangeTokenView: end-to-end dispatch, config secret encryption on
    write, and secret masking on read
"""

import json
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app_check.encryption import decrypt_secret, encrypt_secret
from app_check.models import AppCheckConfig
from app_check.services import (
    verify_device_check_token,
    verify_play_integrity_token,
    verify_recaptcha_enterprise_token,
    verify_recaptcha_v3_token,
)


# ---------------------------------------------------------------------------
# URL helpers (mirrors tests/test_phase5_appcheck.py)
# ---------------------------------------------------------------------------

def config_list_url(project_id):
    return f'/api/projects/{project_id}/app-check/config/'


def exchange_url(project_id):
    return f'/api/projects/{project_id}/app-check/exchange/'


class FakeResp:
    def __init__(self, json_data, status_code=200, text=''):
        self._json = json_data
        self.status_code = status_code
        self.text = text or str(json_data)

    def json(self):
        return self._json


# ---------------------------------------------------------------------------
# TestEncryption
# ---------------------------------------------------------------------------

class TestEncryption:
    def test_roundtrip(self):
        plaintext = '{"client_email": "svc@example.iam.gserviceaccount.com"}'
        ciphertext = encrypt_secret(plaintext)
        assert ciphertext != plaintext
        assert decrypt_secret(ciphertext) == plaintext


# ---------------------------------------------------------------------------
# TestPlayIntegrityVerification (real RSA-signed JWT, mocked HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPlayIntegrityVerification:
    def _service_account_info(self):
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        return {
            'client_email': 'svc@example.iam.gserviceaccount.com',
            'private_key': pem,
        }

    def _config(self, project, service_account_info, package_name='com.example.app'):
        return AppCheckConfig.objects.create(
            project=project,
            platform='android',
            provider='play_integrity',
            config={
                'package_name': package_name,
                'service_account_key_encrypted': encrypt_secret(json.dumps(service_account_info)),
            },
            is_enabled=True,
        )

    def test_missing_config_fields(self, test_project):
        config = AppCheckConfig.objects.create(
            project=test_project, platform='android', provider='play_integrity', config={},
        )
        app_id, error = verify_play_integrity_token(config, 'some-token')
        assert app_id is None
        assert 'missing' in error.lower()

    def test_recognized_app_and_device(self, test_project):
        info = self._service_account_info()
        config = self._config(test_project, info)

        oauth_resp = FakeResp({'access_token': 'fake-access-token'})
        decode_resp = FakeResp({
            'tokenPayloadExternal': {
                'appIntegrity': {
                    'appRecognitionVerdict': 'PLAY_RECOGNIZED',
                    'packageName': 'com.example.app',
                },
                'deviceIntegrity': {
                    'deviceRecognitionVerdict': ['MEETS_DEVICE_INTEGRITY'],
                },
            }
        })

        with patch('app_check.services.requests.post', side_effect=[oauth_resp, decode_resp]) as mock_post:
            app_id, error = verify_play_integrity_token(config, 'raw-integrity-token')

        assert error is None
        assert app_id == 'com.example.app'

        # First call was the real OAuth JWT-bearer exchange -- verify the
        # assertion is a genuinely RS256-signed, well-formed JWT (decode
        # against the actual matching public key, not just parse it).
        oauth_call = mock_post.call_args_list[0]
        assertion = oauth_call.kwargs['data']['assertion']
        public_key = serialization.load_pem_private_key(
            info['private_key'].encode(), password=None
        ).public_key()
        decoded = jwt.decode(
            assertion, public_key, algorithms=['RS256'], audience='https://oauth2.googleapis.com/token',
        )
        assert decoded['iss'] == 'svc@example.iam.gserviceaccount.com'
        assert decoded['scope'] == 'https://www.googleapis.com/auth/playintegrity'

        # Second call was the decode request, carrying the raw token.
        decode_call = mock_post.call_args_list[1]
        assert decode_call.kwargs['json'] == {'integrityToken': 'raw-integrity-token'}
        assert decode_call.kwargs['headers']['Authorization'] == 'Bearer fake-access-token'

    def test_app_not_recognized(self, test_project):
        info = self._service_account_info()
        config = self._config(test_project, info)

        oauth_resp = FakeResp({'access_token': 'fake-access-token'})
        decode_resp = FakeResp({
            'tokenPayloadExternal': {
                'appIntegrity': {'appRecognitionVerdict': 'UNRECOGNIZED_VERSION'},
                'deviceIntegrity': {'deviceRecognitionVerdict': ['MEETS_DEVICE_INTEGRITY']},
            }
        })
        with patch('app_check.services.requests.post', side_effect=[oauth_resp, decode_resp]):
            app_id, error = verify_play_integrity_token(config, 'raw-token')
        assert app_id is None
        assert 'app failed' in error.lower()

    def test_device_not_recognized(self, test_project):
        info = self._service_account_info()
        config = self._config(test_project, info)

        oauth_resp = FakeResp({'access_token': 'fake-access-token'})
        decode_resp = FakeResp({
            'tokenPayloadExternal': {
                'appIntegrity': {'appRecognitionVerdict': 'PLAY_RECOGNIZED'},
                'deviceIntegrity': {'deviceRecognitionVerdict': ['MEETS_BASIC_INTEGRITY']},
            }
        })
        with patch('app_check.services.requests.post', side_effect=[oauth_resp, decode_resp]):
            app_id, error = verify_play_integrity_token(config, 'raw-token')
        assert app_id is None
        assert 'device failed' in error.lower()

    def test_decode_endpoint_error(self, test_project):
        info = self._service_account_info()
        config = self._config(test_project, info)

        oauth_resp = FakeResp({'access_token': 'fake-access-token'})
        decode_resp = FakeResp({}, status_code=400, text='invalid token')
        with patch('app_check.services.requests.post', side_effect=[oauth_resp, decode_resp]):
            app_id, error = verify_play_integrity_token(config, 'bad-token')
        assert app_id is None
        assert 'invalid play integrity token' in error.lower()

    def test_oauth_exchange_failure(self, test_project):
        info = self._service_account_info()
        config = self._config(test_project, info)

        oauth_resp = FakeResp({}, status_code=401, text='invalid_grant')
        with patch('app_check.services.requests.post', return_value=oauth_resp):
            app_id, error = verify_play_integrity_token(config, 'raw-token')
        assert app_id is None
        assert error is not None


# ---------------------------------------------------------------------------
# TestDeviceCheckVerification (real ES256-signed JWT, mocked HTTP)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeviceCheckVerification:
    def _keypair_pem(self):
        priv = ec.generate_private_key(ec.SECP256R1())
        pem = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        return priv, pem

    def _config(self, project, private_key_pem, key_id='TESTKEYID123', team_id='TESTTEAMID1', **extra):
        cfg = {
            'key_id': key_id,
            'team_id': team_id,
            'private_key_encrypted': encrypt_secret(private_key_pem),
        }
        cfg.update(extra)
        return AppCheckConfig.objects.create(
            project=project, platform='ios', provider='device_check', config=cfg, is_enabled=True,
        )

    def test_missing_config_fields(self, test_project):
        config = AppCheckConfig.objects.create(
            project=test_project, platform='ios', provider='device_check', config={},
        )
        app_id, error = verify_device_check_token(config, 'some-token')
        assert app_id is None
        assert 'missing' in error.lower()

    def test_valid_device_token(self, test_project):
        priv, pem = self._keypair_pem()
        config = self._config(test_project, pem)

        with patch('app_check.services.requests.post', return_value=FakeResp({}, status_code=200)) as mock_post:
            app_id, error = verify_device_check_token(config, 'raw-device-token')

        assert error is None
        assert app_id == 'ios-device'

        call = mock_post.call_args
        assert call.args[0] == 'https://api.devicecheck.apple.com/v1/query_two_bits'
        assert call.kwargs['json']['device_token'] == 'raw-device-token'

        # The Authorization header carries a real ES256 JWT signed with the
        # configured private key -- verify signature + claims against the
        # matching public key (proves the crypto path is genuinely correct,
        # not just "some string was sent").
        auth_header = call.kwargs['headers']['Authorization']
        assertion = auth_header.split('Bearer ')[1]
        header = jwt.get_unverified_header(assertion)
        assert header['kid'] == 'TESTKEYID123'
        decoded = jwt.decode(assertion, priv.public_key(), algorithms=['ES256'])
        assert decoded['iss'] == 'TESTTEAMID1'

    def test_development_environment_uses_sandbox_url(self, test_project):
        priv, pem = self._keypair_pem()
        config = self._config(test_project, pem, environment='development')

        with patch('app_check.services.requests.post', return_value=FakeResp({}, status_code=200)) as mock_post:
            verify_device_check_token(config, 'raw-device-token')

        assert mock_post.call_args.args[0] == 'https://api.development.devicecheck.apple.com/v1/query_two_bits'

    def test_forged_token_rejected_by_apple(self, test_project):
        priv, pem = self._keypair_pem()
        config = self._config(test_project, pem)

        with patch('app_check.services.requests.post', return_value=FakeResp({}, status_code=400, text='forged')):
            app_id, error = verify_device_check_token(config, 'forged-token')

        assert app_id is None
        assert 'invalid devicecheck token' in error.lower()


# ---------------------------------------------------------------------------
# TestExchangeViewProductionProviders (end-to-end through the API)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExchangeViewProductionProviders:
    def test_play_integrity_success_issues_token(self, authenticated_client, test_project):
        AppCheckConfig.objects.create(
            project=test_project, platform='android', provider='play_integrity',
            config={'package_name': 'com.example.app', 'service_account_key_encrypted': 'x'},
            is_enabled=True,
        )
        with patch('app_check.services.verify_play_integrity_token', return_value=('com.example.app', None)):
            resp = authenticated_client.post(
                exchange_url(test_project.id),
                {'raw_token': 'tok', 'platform': 'android', 'provider': 'play_integrity'},
                format='json',
            )
        assert resp.status_code == 200
        data = resp.json()
        assert 'token' in data
        assert len(data['token']) == 64

    def test_play_integrity_verification_failure(self, authenticated_client, test_project):
        AppCheckConfig.objects.create(
            project=test_project, platform='android', provider='play_integrity',
            config={'package_name': 'com.example.app', 'service_account_key_encrypted': 'x'},
            is_enabled=True,
        )
        with patch('app_check.services.verify_play_integrity_token', return_value=(None, 'App failed Play Integrity recognition check.')):
            resp = authenticated_client.post(
                exchange_url(test_project.id),
                {'raw_token': 'tok', 'platform': 'android', 'provider': 'play_integrity'},
                format='json',
            )
        assert resp.status_code == 400
        assert 'error' in resp.json()

    def test_device_check_success_issues_token(self, authenticated_client, test_project):
        AppCheckConfig.objects.create(
            project=test_project, platform='ios', provider='device_check',
            config={'key_id': 'k', 'team_id': 't', 'private_key_encrypted': 'x'},
            is_enabled=True,
        )
        with patch('app_check.services.verify_device_check_token', return_value=('ios-device', None)):
            resp = authenticated_client.post(
                exchange_url(test_project.id),
                {'raw_token': 'tok', 'platform': 'ios', 'provider': 'device_check'},
                format='json',
            )
        assert resp.status_code == 200
        assert 'token' in resp.json()

    def test_recaptcha_v3_success_issues_token(self, authenticated_client, test_project):
        AppCheckConfig.objects.create(
            project=test_project, platform='web', provider='recaptcha_v3',
            config={'secret_key_encrypted': 'x'}, is_enabled=True,
        )
        with patch('app_check.services.verify_recaptcha_v3_token', return_value=('example.com', None)):
            resp = authenticated_client.post(
                exchange_url(test_project.id),
                {'raw_token': 'tok', 'platform': 'web', 'provider': 'recaptcha_v3'},
                format='json',
            )
        assert resp.status_code == 200
        assert 'token' in resp.json()

    def test_recaptcha_enterprise_success_issues_token(self, authenticated_client, test_project):
        AppCheckConfig.objects.create(
            project=test_project, platform='web', provider='recaptcha_enterprise',
            config={'gcp_project_id': 'p', 'site_key': 's', 'api_key_encrypted': 'x'}, is_enabled=True,
        )
        with patch('app_check.services.verify_recaptcha_enterprise_token', return_value=('s', None)):
            resp = authenticated_client.post(
                exchange_url(test_project.id),
                {'raw_token': 'tok', 'platform': 'web', 'provider': 'recaptcha_enterprise'},
                format='json',
            )
        assert resp.status_code == 200
        assert 'token' in resp.json()


# ---------------------------------------------------------------------------
# TestConfigSecretHandling
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConfigSecretHandling:
    def test_service_account_key_encrypted_on_write_and_masked_on_read(self, authenticated_client, test_project):
        plaintext_key = '{"client_email": "svc@example.iam.gserviceaccount.com", "private_key": "-----BEGIN..."}'
        resp = authenticated_client.post(
            config_list_url(test_project.id),
            {
                'platform': 'android',
                'provider': 'play_integrity',
                'config': {'package_name': 'com.example.app', 'service_account_key': plaintext_key},
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()

        # Never echo the plaintext or ciphertext back through the API.
        assert 'service_account_key' not in data['config']
        assert data['config']['service_account_key_encrypted'] == '***'

        # But the DB must hold real, decryptable ciphertext (not plaintext).
        config = AppCheckConfig.objects.get(id=data['id'])
        stored = config.config['service_account_key_encrypted']
        assert stored != plaintext_key
        assert decrypt_secret(stored) == plaintext_key

    def test_private_key_encrypted_on_write_and_masked_on_read(self, authenticated_client, test_project):
        plaintext_pem = '-----BEGIN PRIVATE KEY-----\nFAKEKEYDATA\n-----END PRIVATE KEY-----'
        resp = authenticated_client.post(
            config_list_url(test_project.id),
            {
                'platform': 'ios',
                'provider': 'device_check',
                'config': {'key_id': 'ABC123', 'team_id': 'TEAM123', 'private_key': plaintext_pem},
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert 'private_key' not in data['config']
        assert data['config']['private_key_encrypted'] == '***'

        config = AppCheckConfig.objects.get(id=data['id'])
        stored = config.config['private_key_encrypted']
        assert decrypt_secret(stored) == plaintext_pem


# ---------------------------------------------------------------------------
# TestRecaptchaV3Verification
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRecaptchaV3Verification:
    def _config(self, project, secret_key='fake-secret', **extra):
        cfg = {'secret_key_encrypted': encrypt_secret(secret_key)}
        cfg.update(extra)
        return AppCheckConfig.objects.create(
            project=project, platform='web', provider='recaptcha_v3', config=cfg, is_enabled=True,
        )

    def test_missing_config_fields(self, test_project):
        config = AppCheckConfig.objects.create(
            project=test_project, platform='web', provider='recaptcha_v3', config={},
        )
        app_id, error = verify_recaptcha_v3_token(config, 'some-token')
        assert app_id is None
        assert 'missing' in error.lower()

    def test_success_above_threshold(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({'success': True, 'score': 0.9, 'hostname': 'example.com'})
        with patch('app_check.services.requests.post', return_value=resp) as mock_post:
            app_id, error = verify_recaptcha_v3_token(config, 'raw-token')
        assert error is None
        assert app_id == 'example.com'
        assert mock_post.call_args.kwargs['data'] == {'secret': 'fake-secret', 'response': 'raw-token'}

    def test_score_below_default_threshold(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({'success': True, 'score': 0.2, 'hostname': 'example.com'})
        with patch('app_check.services.requests.post', return_value=resp):
            app_id, error = verify_recaptcha_v3_token(config, 'raw-token')
        assert app_id is None
        assert 'below required minimum' in error.lower()

    def test_custom_min_score_respected(self, test_project):
        config = self._config(test_project, min_score=0.1)
        resp = FakeResp({'success': True, 'score': 0.2, 'hostname': 'example.com'})
        with patch('app_check.services.requests.post', return_value=resp):
            app_id, error = verify_recaptcha_v3_token(config, 'raw-token')
        assert error is None
        assert app_id == 'example.com'

    def test_google_reports_failure(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({'success': False, 'error-codes': ['invalid-input-response']})
        with patch('app_check.services.requests.post', return_value=resp):
            app_id, error = verify_recaptcha_v3_token(config, 'bad-token')
        assert app_id is None
        assert 'verification failed' in error.lower()

    def test_siteverify_http_error(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({}, status_code=500, text='server error')
        with patch('app_check.services.requests.post', return_value=resp):
            app_id, error = verify_recaptcha_v3_token(config, 'raw-token')
        assert app_id is None
        assert error is not None


# ---------------------------------------------------------------------------
# TestRecaptchaEnterpriseVerification
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRecaptchaEnterpriseVerification:
    def _config(self, project, api_key='fake-api-key', gcp_project_id='my-gcp-project', site_key='my-site-key', **extra):
        cfg = {
            'gcp_project_id': gcp_project_id,
            'site_key': site_key,
            'api_key_encrypted': encrypt_secret(api_key),
        }
        cfg.update(extra)
        return AppCheckConfig.objects.create(
            project=project, platform='web', provider='recaptcha_enterprise', config=cfg, is_enabled=True,
        )

    def test_missing_config_fields(self, test_project):
        config = AppCheckConfig.objects.create(
            project=test_project, platform='web', provider='recaptcha_enterprise', config={},
        )
        app_id, error = verify_recaptcha_enterprise_token(config, 'some-token')
        assert app_id is None
        assert 'missing' in error.lower()

    def test_success_above_threshold(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({
            'tokenProperties': {'valid': True, 'action': 'login'},
            'riskAnalysis': {'score': 0.8},
        })
        with patch('app_check.services.requests.post', return_value=resp) as mock_post:
            app_id, error = verify_recaptcha_enterprise_token(config, 'raw-token')
        assert error is None
        assert app_id == 'my-site-key'
        assert mock_post.call_args.kwargs['params'] == {'key': 'fake-api-key'}
        assert mock_post.call_args.kwargs['json'] == {
            'event': {'token': 'raw-token', 'siteKey': 'my-site-key'}
        }

    def test_invalid_token_property(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({
            'tokenProperties': {'valid': False, 'invalidReason': 'EXPIRED'},
        })
        with patch('app_check.services.requests.post', return_value=resp):
            app_id, error = verify_recaptcha_enterprise_token(config, 'raw-token')
        assert app_id is None
        assert 'expired' in error.lower()

    def test_score_below_threshold(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({
            'tokenProperties': {'valid': True},
            'riskAnalysis': {'score': 0.1},
        })
        with patch('app_check.services.requests.post', return_value=resp):
            app_id, error = verify_recaptcha_enterprise_token(config, 'raw-token')
        assert app_id is None
        assert 'below required minimum' in error.lower()

    def test_assessment_http_error(self, test_project):
        config = self._config(test_project)
        resp = FakeResp({}, status_code=403, text='forbidden')
        with patch('app_check.services.requests.post', return_value=resp):
            app_id, error = verify_recaptcha_enterprise_token(config, 'raw-token')
        assert app_id is None
        assert error is not None
