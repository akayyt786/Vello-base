"""Tests for OwnFirebase App Check SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.appcheck import AppCheckSDK

BASE_URL = 'http://localhost:8000'
PROJECT_ID = 'test-project'
TOKEN = 'test-token'
PROJECT_PREFIX = f'{BASE_URL}/api/projects/{PROJECT_ID}'


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
    return AppCheckSDK(config)


class TestAppCheckSDK:
    """Tests for the App Check SDK."""

    def test_appcheck_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_exchange_token(self, mock_request, sdk):
        _ok(mock_request, {'token': 'app-check-tok', 'expires_at': '2024-01-01T01:00:00Z'})
        result = sdk.exchange_token(
            provider='recaptcha_v3', platform='web', raw_token='raw-attestation-token'
        )
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/app-check/exchange/'
        assert kw['json'] == {
            'provider': 'recaptcha_v3',
            'platform': 'web',
            'raw_token': 'raw-attestation-token',
        }
        assert result['token'] == 'app-check-tok'

    @patch('requests.request')
    def test_exchange_token_android_play_integrity(self, mock_request, sdk):
        _ok(mock_request, {'token': 'tok2', 'expires_at': '2024-01-01T01:00:00Z'})
        sdk.exchange_token(provider='play_integrity', platform='android', raw_token='assertion')
        kw = _kwargs(mock_request)
        assert kw['json'] == {
            'provider': 'play_integrity',
            'platform': 'android',
            'raw_token': 'assertion',
        }
