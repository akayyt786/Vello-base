"""Tests for OwnFirebase Realtime SDK.

The Realtime SDK does not bundle a WebSocket client (see ownfirebase/realtime.py
docstring for rationale). These tests cover the connection-agnostic pieces it
does provide: building the correct WebSocket URL and the message envelopes a
caller sends/receives over whatever WS client they bring themselves.
"""

import json

import pytest

from ownfirebase import OwnFirebaseConfig
from ownfirebase.realtime import RealtimeSDK

BASE_URL = 'http://localhost:8000'
PROJECT_ID = 'test-project'
TOKEN = 'test-token'


@pytest.fixture
def sdk():
    config = OwnFirebaseConfig(base_url=BASE_URL, project_id=PROJECT_ID, access_token=TOKEN)
    return RealtimeSDK(config)


class TestRealtimeSDK:
    """Tests for the Realtime SDK."""

    def test_realtime_init(self, sdk):
        assert sdk.base_url == BASE_URL
        assert sdk.project_id == PROJECT_ID

    def test_get_websocket_url_http(self, sdk):
        url = sdk.get_websocket_url()
        assert url == f'ws://localhost:8000/ws/v1/projects/{PROJECT_ID}/listen/'

    def test_get_websocket_url_https_becomes_wss(self):
        config = OwnFirebaseConfig(
            base_url='https://api.example.com', project_id='proj-1', access_token=TOKEN
        )
        sdk = RealtimeSDK(config)
        url = sdk.get_websocket_url()
        assert url == 'wss://api.example.com/ws/v1/projects/proj-1/listen/'

    def test_get_websocket_url_requires_project_id(self):
        config = OwnFirebaseConfig(base_url=BASE_URL, access_token=TOKEN)
        sdk = RealtimeSDK(config)
        with pytest.raises(ValueError, match='project_id is required'):
            sdk.get_websocket_url()

    def test_build_subscribe_message(self, sdk):
        msg = sdk.build_subscribe_message('users', query={'status': 'active'})
        assert msg['type'] == 'subscribe'
        assert msg['path'] == 'users'
        assert msg['query'] == {'status': 'active'}
        assert 'requestId' in msg

    def test_build_subscribe_message_auto_increments_request_id(self, sdk):
        msg1 = sdk.build_subscribe_message('users')
        msg2 = sdk.build_subscribe_message('posts')
        assert msg1['requestId'] != msg2['requestId']

    def test_build_subscribe_message_explicit_request_id(self, sdk):
        msg = sdk.build_subscribe_message('users', request_id='custom-id')
        assert msg['requestId'] == 'custom-id'

    def test_build_unsubscribe_message(self, sdk):
        msg = sdk.build_unsubscribe_message('sub-123')
        assert msg['type'] == 'unsubscribe'
        assert msg['subscriptionId'] == 'sub-123'
        assert 'requestId' in msg

    def test_build_ping_message(self, sdk):
        msg = sdk.build_ping_message()
        assert msg == {'type': 'ping'}

    def test_parse_message_change(self, sdk):
        raw = json.dumps({
            'type': 'change',
            'subscriptionId': 'sub-123',
            'event': 'modified',
            'data': {'name': 'updated'},
            'version': 2,
        })
        parsed = RealtimeSDK.parse_message(raw)
        assert parsed['type'] == 'change'
        assert parsed['event'] == 'modified'
        assert parsed['data']['name'] == 'updated'

    def test_parse_message_pong(self, sdk):
        parsed = RealtimeSDK.parse_message(json.dumps({'type': 'pong'}))
        assert parsed['type'] == 'pong'
