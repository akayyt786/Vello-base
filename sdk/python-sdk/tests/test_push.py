"""Tests for OwnFirebase Push Notifications SDK."""

from unittest.mock import Mock, patch

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.push import PushSDK

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
    return PushSDK(config)


class TestPushSDK:
    """Tests for the Push Notifications SDK — one test per real method."""

    def test_push_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    @patch('requests.request')
    def test_register_token(self, mock_request, sdk):
        _ok(mock_request, {'id': 'tok-1', 'token': 'fcm-tok', 'platform': 'fcm'}, status=201)
        result = sdk.register_token('fcm-tok', 'fcm')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/tokens/'
        assert kw['json'] == {'token': 'fcm-tok', 'platform': 'fcm'}
        assert result['id'] == 'tok-1'

    @patch('requests.request')
    def test_list_tokens(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'next': None, 'previous': None, 'results': []})
        sdk.list_tokens()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/tokens/'

    @patch('requests.request')
    def test_delete_token(self, mock_request, sdk):
        _ok(mock_request, status=204)
        result = sdk.delete_token('tok-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'DELETE'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/tokens/tok-1/'
        assert result is None

    @patch('requests.request')
    def test_list_topics(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_topics()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/topics/'

    @patch('requests.request')
    def test_create_topic(self, mock_request, sdk):
        _ok(mock_request, {'id': 'topic-1', 'name': 'news'}, status=201)
        result = sdk.create_topic('news')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/topics/'
        assert kw['json'] == {'name': 'news'}
        assert result['name'] == 'news'

    @patch('requests.request')
    def test_subscribe_topic(self, mock_request, sdk):
        _ok(mock_request, {'id': 'sub-1', 'topic': 'topic-1', 'device_token': 'tok-1'}, status=201)
        result = sdk.subscribe_topic('topic-1', 'tok-1')
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/topics/topic-1/subscribe/'
        assert kw['json'] == {'device_token_id': 'tok-1'}
        assert result['id'] == 'sub-1'

    @patch('requests.request')
    def test_send_to_device(self, mock_request, sdk):
        _ok(mock_request, {'id': 'notif-1', 'status': 'sent'}, status=201)
        result = sdk.send_to_device('tok-1', {'title': 'Hello', 'body': 'World'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/notifications/'
        assert kw['json'] == {'device_token': 'tok-1', 'title': 'Hello', 'body': 'World'}
        assert result['status'] == 'sent'

    @patch('requests.request')
    def test_send_to_topic(self, mock_request, sdk):
        _ok(mock_request, {'id': 'notif-2', 'status': 'sent'}, status=201)
        result = sdk.send_to_topic('topic-1', {'title': 'Hi', 'body': 'There'})
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/notifications/'
        assert kw['json'] == {'topic': 'topic-1', 'title': 'Hi', 'body': 'There'}
        assert result['status'] == 'sent'

    @patch('requests.request')
    def test_list_notifications(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_notifications()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/notifications/'

    @patch('requests.request')
    def test_list_campaigns(self, mock_request, sdk):
        _ok(mock_request, {'count': 0, 'results': []})
        sdk.list_campaigns()
        kw = _kwargs(mock_request)
        assert kw['method'] == 'GET'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/campaigns/'

    @patch('requests.request')
    def test_create_campaign(self, mock_request, sdk):
        notification = {
            'title': 'Sale',
            'body': '50% off',
            'scheduled_at': '2024-02-01T00:00:00Z',
            'audience': {'segment': 'all'},
        }
        _ok(mock_request, {'id': 'camp-1', **notification}, status=201)
        result = sdk.create_campaign(notification)
        kw = _kwargs(mock_request)
        assert kw['method'] == 'POST'
        assert kw['url'] == f'{PROJECT_PREFIX}/push/campaigns/'
        assert kw['json'] == notification
        assert result['id'] == 'camp-1'
