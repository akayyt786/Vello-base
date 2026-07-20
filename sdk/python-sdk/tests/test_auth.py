"""Tests for OwnFirebase Auth SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.auth import AuthSDK

BASE_URL = 'http://localhost:8000'
PROJECT_ID = 'test-project'
TOKEN = 'test-token'


def _ok(mock_request, json_data=None, status=200):
    resp = Mock()
    resp.ok = True
    resp.status_code = status
    resp.json.return_value = {} if json_data is None else json_data
    mock_request.return_value = resp
    return resp


def _kwargs(mock_request):
    return mock_request.call_args[1]


@pytest.fixture
def sdk():
    config = OwnFirebaseConfig(base_url=BASE_URL, project_id=PROJECT_ID, access_token=TOKEN)
    return AuthSDK(config)


class TestAuthSDK:
    """Tests for the Auth SDK — one test per real method, asserting HTTP verb, URL, body."""

    def test_auth_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID
        assert sdk.access_token == TOKEN

    @patch('requests.request')
    def test_register(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a', 'refresh': 'r', 'user_id': 'u1'}, status=201)
        result = sdk.register('a@b.com', 'pw123', username='bob')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/register/'
        assert kw['json'] == {'email': 'a@b.com', 'password': 'pw123', 'username': 'bob'}
        assert 'Authorization' not in kw['headers']
        assert result['access'] == 'a'

    @patch('requests.request')
    def test_register_without_username(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.register('a@b.com', 'pw123')
        kw = _kwargs(mock_request)
        assert kw['json'] == {'email': 'a@b.com', 'password': 'pw123'}

    @patch('requests.request')
    def test_login(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a', 'refresh': 'r', 'user_id': 'u1'})
        result = sdk.login('a@b.com', 'pw123')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/login/'
        assert kw['json'] == {'email': 'a@b.com', 'password': 'pw123'}
        assert 'Authorization' not in kw['headers']
        assert result['user_id'] == 'u1'

    @patch('requests.request')
    def test_refresh_token(self, mock_request, sdk):
        _ok(mock_request, {'access': 'new-access'})
        result = sdk.refresh_token('refresh-tok')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/refresh/'
        assert kw['json'] == {'refresh': 'refresh-tok'}
        assert 'Authorization' not in kw['headers']
        assert result['access'] == 'new-access'

    @patch('requests.request')
    def test_logout(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.logout('refresh-tok')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/logout/'
        assert kw['json'] == {'refresh': 'refresh-tok'}
        assert kw['headers']['Authorization'] == f'Bearer {TOKEN}'
        assert result is None

    @patch('requests.request')
    def test_get_me(self, mock_request, sdk):
        _ok(mock_request, {'id': 'u1', 'email': 'a@b.com'})
        result = sdk.get_me()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/me/'
        assert result['id'] == 'u1'

    @patch('requests.request')
    def test_anonymous_sign_in(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a', 'user_id': 'anon-1'})
        result = sdk.anonymous_sign_in()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/anonymous-signin/'
        assert kw['json'] == {}
        assert 'Authorization' not in kw['headers']
        assert result['user_id'] == 'anon-1'

    @patch('requests.request')
    def test_set_custom_claims(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'ok'})
        result = sdk.set_custom_claims({'role': 'admin'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/set-custom-claims/'
        assert kw['json'] == {'claims': {'role': 'admin'}}
        assert result['detail'] == 'ok'

    @patch('requests.request')
    def test_google_sign_in(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.google_sign_in('google-id-token')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/social/google/'
        assert kw['json'] == {'id_token': 'google-id-token'}
        assert 'Authorization' not in kw['headers']

    @patch('requests.request')
    def test_github_sign_in(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.github_sign_in('gh-access-token')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/social/github/'
        assert kw['json'] == {'access_token': 'gh-access-token'}
        assert 'Authorization' not in kw['headers']

    @patch('requests.request')
    def test_list_linked_accounts(self, mock_request, sdk):
        _ok(mock_request, [{'id': 'l1', 'provider': 'google'}])
        result = sdk.list_linked_accounts()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/social/linked/'
        assert result[0]['provider'] == 'google'

    @patch('requests.request')
    def test_unlink_social_account(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.unlink_social_account('link-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/social/linked/link-1/'
        assert result is None

    @patch('requests.request')
    def test_send_phone_otp(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'sent'})
        sdk.send_phone_otp('+15551234567')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/phone/send-otp/'
        assert kw['json'] == {'phone_number': '+15551234567'}
        assert 'Authorization' not in kw['headers']

    @patch('requests.request')
    def test_verify_phone_otp(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.verify_phone_otp('+15551234567', '123456')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/phone/verify-otp/'
        assert kw['json'] == {'phone_number': '+15551234567', 'otp_code': '123456'}
        assert 'Authorization' not in kw['headers']

    @patch('requests.request')
    def test_enroll_totp(self, mock_request, sdk):
        _ok(mock_request, {
            'device_id': 'dev-1', 'secret': 'SECRET', 'provisioning_uri': 'otpauth://...'
        })
        result = sdk.enroll_totp()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/enroll/totp/'
        assert kw['json'] == {}
        assert result['provisioning_uri'] == 'otpauth://...'

    @patch('requests.request')
    def test_confirm_totp(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'confirmed'})
        sdk.confirm_totp('dev-1', '123456')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/confirm/totp/'
        assert kw['json'] == {'device_id': 'dev-1', 'totp_code': '123456'}

    @patch('requests.request')
    def test_verify_totp(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.verify_totp('dev-1', '234567')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/verify/totp/'
        assert kw['json'] == {'device_id': 'dev-1', 'totp_code': '234567'}

    @patch('requests.request')
    def test_enroll_sms(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'ok'})
        sdk.enroll_sms('+15551234567')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/enroll/sms/'
        assert kw['json'] == {'phone_number': '+15551234567'}

    @patch('requests.request')
    def test_confirm_sms(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'ok'})
        sdk.confirm_sms('dev-2', '111222')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/confirm/sms/'
        assert kw['json'] == {'device_id': 'dev-2', 'code': '111222'}

    @patch('requests.request')
    def test_verify_sms(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.verify_sms('dev-2', '111222')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/verify/sms/'
        assert kw['json'] == {'device_id': 'dev-2', 'code': '111222'}

    @patch('requests.request')
    def test_send_sms_code(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'sent'})
        sdk.send_sms_code('dev-2')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/send-sms-code/dev-2/'
        assert kw['json'] == {}

    @patch('requests.request')
    def test_list_mfa_devices(self, mock_request, sdk):
        _ok(mock_request, [{'id': 'dev-1', 'type': 'totp'}])
        result = sdk.list_mfa_devices()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/devices/'
        assert result[0]['type'] == 'totp'

    @patch('requests.request')
    def test_delete_mfa_device(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_mfa_device('dev-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/mfa/devices/dev-1/'
        assert result is None

    @patch('requests.request')
    def test_send_magic_link(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'sent'})
        sdk.send_magic_link('a@b.com')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/magic-link/send/'
        assert kw['json'] == {'email': 'a@b.com'}
        assert 'Authorization' not in kw['headers']

    @patch('requests.request')
    def test_verify_magic_link(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.verify_magic_link('magic-token')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/magic-link/verify/'
        assert kw['json'] == {'token': 'magic-token'}
        assert 'Authorization' not in kw['headers']

    @patch('requests.request')
    def test_upgrade_anonymous(self, mock_request, sdk):
        _ok(mock_request, {'access': 'a'})
        sdk.upgrade_anonymous('a@b.com', 'pw123', 'pw123')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/upgrade/'
        assert kw['json'] == {'email': 'a@b.com', 'password': 'pw123', 'password2': 'pw123'}

    @patch('requests.request')
    def test_set_password(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'ok'})
        sdk.set_password('newpw123', 'newpw123', current_password='oldpw')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/set-password/'
        assert kw['json'] == {
            'new_password': 'newpw123',
            'new_password2': 'newpw123',
            'current_password': 'oldpw',
        }

    @patch('requests.request')
    def test_set_password_without_current(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'ok'})
        sdk.set_password('newpw123', 'newpw123')
        kw = _kwargs(mock_request)
        assert kw['json'] == {'new_password': 'newpw123', 'new_password2': 'newpw123'}

    @patch('requests.request')
    def test_link_email(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'ok'})
        sdk.link_email('a@b.com', 'pw123')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/link-email/'
        assert kw['json'] == {'email': 'a@b.com', 'password': 'pw123'}

    @patch('requests.request')
    def test_verify_email_change(self, mock_request, sdk):
        _ok(mock_request, {'detail': 'ok'})
        sdk.verify_email_change('email-change-token')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/v1/auth/verify-email-change/'
        assert kw['json'] == {'token': 'email-change-token'}
        assert 'Authorization' not in kw['headers']

    @patch('requests.request')
    def test_issue_custom_token(self, mock_request, sdk):
        _ok(mock_request, {'custom_token': 'tok'})
        sdk.issue_custom_token('user-1', claims={'admin': True})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{BASE_URL}/api/projects/{PROJECT_ID}/auth/custom-token/'
        assert kw['json'] == {'user_id': 'user-1', 'claims': {'admin': True}}

    @patch('requests.request')
    def test_issue_custom_token_without_claims(self, mock_request, sdk):
        _ok(mock_request, {'custom_token': 'tok'})
        sdk.issue_custom_token('user-1')
        kw = _kwargs(mock_request)
        assert kw['json'] == {'user_id': 'user-1'}
