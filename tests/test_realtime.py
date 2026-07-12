"""
Phase 2 Realtime Tests: WebSocket consumer, signals, presence.

Tests use Django Channels' WebsocketCommunicator for in-process testing.
No real Redis required for most tests — uses InMemoryChannelLayer.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from django.contrib.auth.models import User
from channels.db import database_sync_to_async


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_user(username='realtime_user@test.com', password='pass1234'):
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={'email': username}
    )
    user.set_password(password)
    user.save()
    return user


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: path parsing
# ─────────────────────────────────────────────────────────────────────────────

class TestPathParsing:
    def test_document_path(self):
        from realtime.consumers import _parse_path
        col, doc = _parse_path('users/alice')
        assert col == 'users'
        assert doc == 'alice'

    def test_collection_path(self):
        from realtime.consumers import _parse_path
        col, doc = _parse_path('users')
        assert col == 'users'
        assert doc is None

    def test_nested_document_path(self):
        from realtime.consumers import _parse_path
        col, doc = _parse_path('users/alice/posts/post1')
        assert col == 'users/alice/posts'
        assert doc == 'post1'

    def test_nested_collection_path(self):
        from realtime.consumers import _parse_path
        col, doc = _parse_path('users/alice/posts')
        assert col == 'users/alice/posts'
        assert doc is None

    def test_empty_path(self):
        from realtime.consumers import _parse_path
        col, doc = _parse_path('')
        assert col is None
        assert doc is None

    def test_leading_trailing_slashes(self):
        from realtime.consumers import _parse_path
        col, doc = _parse_path('/users/alice/')
        assert col == 'users'
        assert doc == 'alice'


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: group name generation
# ─────────────────────────────────────────────────────────────────────────────

class TestGroupNames:
    def test_doc_group_simple(self):
        from realtime.consumers import _doc_group
        name = _doc_group('proj-1', 'users', 'alice')
        assert 'proj' in name
        assert 'users' in name
        assert 'alice' in name
        assert '/' not in name
        assert '-' not in name or name.startswith('p_')

    def test_col_group_simple(self):
        from realtime.consumers import _col_group
        name = _col_group('proj-1', 'users')
        assert 'users' in name

    def test_doc_group_nested(self):
        from realtime.consumers import _doc_group
        name = _doc_group('p1', 'users/alice/posts', 'post1')
        assert '/' not in name

    def test_group_names_differ(self):
        from realtime.consumers import _doc_group, _col_group
        doc_name = _doc_group('p1', 'users', 'alice')
        col_name = _col_group('p1', 'users')
        assert doc_name != col_name


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: query matching
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryMatching:
    def setup_method(self):
        from realtime.consumers import RealtimeConsumer
        self.consumer = RealtimeConsumer()

    def test_no_query_matches_all(self):
        assert self.consumer._matches_query({'name': 'Alice'}, None) is True
        assert self.consumer._matches_query({}, None) is True

    def test_eq_match(self):
        query = {'where': [['status', '==', 'active']]}
        assert self.consumer._matches_query({'status': 'active'}, query) is True
        assert self.consumer._matches_query({'status': 'inactive'}, query) is False

    def test_neq_match(self):
        query = {'where': [['status', '!=', 'deleted']]}
        assert self.consumer._matches_query({'status': 'active'}, query) is True
        assert self.consumer._matches_query({'status': 'deleted'}, query) is False

    def test_gt_match(self):
        query = {'where': [['age', '>', 18]]}
        assert self.consumer._matches_query({'age': 25}, query) is True
        assert self.consumer._matches_query({'age': 18}, query) is False
        assert self.consumer._matches_query({'age': 10}, query) is False

    def test_gte_match(self):
        query = {'where': [['age', '>=', 18]]}
        assert self.consumer._matches_query({'age': 18}, query) is True
        assert self.consumer._matches_query({'age': 17}, query) is False

    def test_lt_match(self):
        query = {'where': [['score', '<', 100]]}
        assert self.consumer._matches_query({'score': 50}, query) is True
        assert self.consumer._matches_query({'score': 100}, query) is False

    def test_lte_match(self):
        query = {'where': [['score', '<=', 100]]}
        assert self.consumer._matches_query({'score': 100}, query) is True
        assert self.consumer._matches_query({'score': 101}, query) is False

    def test_multiple_conditions_and(self):
        query = {'where': [['status', '==', 'active'], ['age', '>=', 18]]}
        assert self.consumer._matches_query({'status': 'active', 'age': 25}, query) is True
        assert self.consumer._matches_query({'status': 'active', 'age': 10}, query) is False
        assert self.consumer._matches_query({'status': 'inactive', 'age': 25}, query) is False

    def test_missing_field_fails(self):
        query = {'where': [['age', '>', 18]]}
        assert self.consumer._matches_query({'name': 'Alice'}, query) is False

    def test_none_data_returns_true(self):
        assert self.consumer._matches_query(None, {'where': [['x', '==', 1]]}) is True


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: signals broadcasting
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalsBroadcast:
    @patch('realtime.signals.get_channel_layer')
    @patch('realtime.signals.async_to_sync')
    def test_post_save_broadcasts_to_both_groups(self, mock_async_to_sync, mock_get_layer):
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer
        mock_broadcast = MagicMock()
        mock_async_to_sync.return_value = mock_broadcast

        from realtime.signals import on_document_saved
        mock_instance = MagicMock()
        mock_instance.project_id = 'proj-123'
        mock_instance.collection_path = 'users'
        mock_instance.doc_id = 'alice'
        mock_instance.data = {'name': 'Alice'}
        mock_instance.v = 1

        on_document_saved(sender=None, instance=mock_instance, created=False)

        assert mock_broadcast.call_count == 2

    @patch('realtime.signals.get_channel_layer')
    @patch('realtime.signals.async_to_sync')
    def test_post_save_created_sends_added_event(self, mock_async_to_sync, mock_get_layer):
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer
        mock_broadcast = MagicMock()
        mock_async_to_sync.return_value = mock_broadcast

        from realtime.signals import on_document_saved
        mock_instance = MagicMock()
        mock_instance.project_id = 'proj-123'
        mock_instance.collection_path = 'users'
        mock_instance.doc_id = 'bob'
        mock_instance.data = {'name': 'Bob'}
        mock_instance.v = 1

        on_document_saved(sender=None, instance=mock_instance, created=True)

        calls = mock_broadcast.call_args_list
        for call in calls:
            msg = call[0][1]  # second positional arg: the message dict
            assert msg['event'] == 'added'

    @patch('realtime.signals.get_channel_layer')
    @patch('realtime.signals.async_to_sync')
    def test_post_delete_sends_removed_event(self, mock_async_to_sync, mock_get_layer):
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer
        mock_broadcast = MagicMock()
        mock_async_to_sync.return_value = mock_broadcast

        from realtime.signals import on_document_deleted
        mock_instance = MagicMock()
        mock_instance.project_id = 'proj-123'
        mock_instance.collection_path = 'users'
        mock_instance.doc_id = 'alice'
        mock_instance.v = 2

        on_document_deleted(sender=None, instance=mock_instance)

        calls = mock_broadcast.call_args_list
        for call in calls:
            msg = call[0][1]  # second positional arg: the message dict
            assert msg['event'] == 'removed'
            assert msg['data'] is None

    @patch('realtime.signals.get_channel_layer')
    def test_broadcast_skips_when_no_channel_layer(self, mock_get_layer):
        mock_get_layer.return_value = None
        from realtime.signals import _broadcast
        _broadcast('some_group', {'event': 'added'})


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: presence system
# ─────────────────────────────────────────────────────────────────────────────

class TestPresenceSystem:
    @patch('realtime.presence.cache')
    def test_set_presence_stores_in_cache(self, mock_cache):
        from realtime.presence import set_presence
        set_presence('proj1', 'user1', 'channel1', {'online': True})
        assert mock_cache.set.called
        call_args = mock_cache.set.call_args
        assert 'proj1' in call_args[0][0]
        assert 'user1' in call_args[0][0]

    @patch('realtime.presence.cache')
    def test_remove_presence_deletes_from_cache(self, mock_cache):
        from realtime.presence import remove_presence
        remove_presence('proj1', 'user1', 'channel1')
        assert mock_cache.delete.called

    @patch('realtime.presence.cache')
    def test_refresh_presence_extends_ttl(self, mock_cache):
        mock_cache.get.return_value = '{"user_id":"u1"}'
        from realtime.presence import refresh_presence
        refresh_presence('proj1', 'user1', 'chan1')
        assert mock_cache.set.called

    @patch('realtime.presence.cache')
    def test_register_on_disconnect(self, mock_cache):
        from realtime.presence import register_on_disconnect
        register_on_disconnect('p1', 'u1', 'ch1', 'users', 'alice', {'status': 'offline'})
        assert mock_cache.set.called

    @patch('realtime.presence.cache')
    def test_fire_on_disconnect_no_payload(self, mock_cache):
        mock_cache.get.return_value = None
        from realtime.presence import fire_on_disconnect
        fire_on_disconnect('p1', 'u1', 'ch1')
        assert not mock_cache.delete.called


# ─────────────────────────────────────────────────────────────────────────────
# Integration: WebSocket consumer (async, in-memory channel layer)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestRealtimeConsumerConnect:
    async def test_unauthenticated_closes_4401(self):
        from channels.testing import WebsocketCommunicator
        from channels.layers import get_channel_layer
        from channels.db import database_sync_to_async
        from django.contrib.auth.models import AnonymousUser
        from realtime.consumers import RealtimeConsumer

        app = RealtimeConsumer.as_asgi()
        communicator = WebsocketCommunicator(app, '/ws/v1/projects/test-proj/listen/')
        communicator.scope['url_route'] = {'kwargs': {'project_id': 'test-proj'}}
        communicator.scope['user'] = AnonymousUser()

        connected, code = await communicator.connect()
        assert not connected or code == 4401
        await communicator.disconnect()

    async def test_ping_pong(self, django_db_setup):
        from channels.testing import WebsocketCommunicator
        from channels.layers import get_channel_layer
        from channels.db import database_sync_to_async
        from unittest.mock import patch, AsyncMock
        from realtime.consumers import RealtimeConsumer

        user = await database_sync_to_async(make_user)('pingpong@test.com')

        app = RealtimeConsumer.as_asgi()
        communicator = WebsocketCommunicator(app, '/ws/v1/projects/test-proj/listen/')
        communicator.scope['url_route'] = {'kwargs': {'project_id': 'test-proj'}}
        communicator.scope['user'] = user

        with patch.object(RealtimeConsumer, '_check_project_access', return_value=True):
            connected, _ = await communicator.connect()
            assert connected

            await communicator.send_json_to({'type': 'ping'})
            response = await communicator.receive_json_from()
            assert response['type'] == 'pong'

        await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestRealtimeConsumerSubscriptions:
    async def test_subscribe_invalid_path_returns_error(self):
        from channels.testing import WebsocketCommunicator
        from realtime.consumers import RealtimeConsumer
        from unittest.mock import patch

        user = await database_sync_to_async(make_user)('sub_invalid@test.com')
        app = RealtimeConsumer.as_asgi()
        communicator = WebsocketCommunicator(app, '/ws/v1/projects/test-proj/listen/')
        communicator.scope['url_route'] = {'kwargs': {'project_id': 'test-proj'}}
        communicator.scope['user'] = user

        with patch.object(RealtimeConsumer, '_check_project_access', return_value=True):
            await communicator.connect()
            await communicator.send_json_to({
                'type': 'subscribe',
                'requestId': 'r1',
                'path': '',
            })
            response = await communicator.receive_json_from()
            assert response['type'] == 'error'
            assert response['code'] == 'INVALID'
            assert response['requestId'] == 'r1'

        await communicator.disconnect()

    async def test_unsubscribe_unknown_sub_returns_error(self):
        from channels.testing import WebsocketCommunicator
        from realtime.consumers import RealtimeConsumer
        from unittest.mock import patch

        user = await database_sync_to_async(make_user)('unsub_test@test.com')
        app = RealtimeConsumer.as_asgi()
        communicator = WebsocketCommunicator(app, '/ws/v1/projects/test-proj/listen/')
        communicator.scope['url_route'] = {'kwargs': {'project_id': 'test-proj'}}
        communicator.scope['user'] = user

        with patch.object(RealtimeConsumer, '_check_project_access', return_value=True):
            await communicator.connect()
            await communicator.send_json_to({
                'type': 'unsubscribe',
                'requestId': 'r2',
                'subscriptionId': 'sub_nonexistent',
            })
            response = await communicator.receive_json_from()
            assert response['type'] == 'error'
            assert response['code'] == 'NOT_FOUND'

        await communicator.disconnect()

    async def test_unknown_message_type_returns_error(self):
        from channels.testing import WebsocketCommunicator
        from realtime.consumers import RealtimeConsumer
        from unittest.mock import patch

        user = await database_sync_to_async(make_user)('unknown_type@test.com')
        app = RealtimeConsumer.as_asgi()
        communicator = WebsocketCommunicator(app, '/ws/v1/projects/test-proj/listen/')
        communicator.scope['url_route'] = {'kwargs': {'project_id': 'test-proj'}}
        communicator.scope['user'] = user

        with patch.object(RealtimeConsumer, '_check_project_access', return_value=True):
            await communicator.connect()
            await communicator.send_json_to({'type': 'unknown_type', 'requestId': 'r99'})
            response = await communicator.receive_json_from()
            assert response['type'] == 'error'
            assert 'Unknown type' in response['message']

        await communicator.disconnect()


# ─────────────────────────────────────────────────────────────────────────────
# Routing tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRouting:
    def test_websocket_url_patterns_exist(self):
        from realtime.routing import websocket_urlpatterns
        assert len(websocket_urlpatterns) > 0

    def test_pattern_matches_project_id(self):
        from realtime.routing import websocket_urlpatterns
        import re
        pattern = websocket_urlpatterns[0].pattern
        assert hasattr(pattern, '_route') or hasattr(pattern, 'regex')

    def test_consumer_is_asgi_app(self):
        from realtime.routing import websocket_urlpatterns
        from realtime.consumers import RealtimeConsumer
        route = websocket_urlpatterns[0]
        assert route.callback is not None


# ─────────────────────────────────────────────────────────────────────────────
# Integration: JWT auth bridge (realtime/auth_middleware.py)
#
# Unlike TestRealtimeConsumerConnect above (which wraps the bare consumer and
# injects scope['user'] directly, bypassing auth entirely), these tests wrap
# the real ASGI stack — JWTAuthMiddlewareStack(URLRouter(...)) — the same
# composition used in ownfirebase/asgi.py, so they exercise the actual token
# parsing and validation an API client depends on.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestJWTWebSocketAuth:
    def _app(self):
        from channels.routing import URLRouter
        from realtime.auth_middleware import JWTAuthMiddlewareStack
        from realtime.routing import websocket_urlpatterns
        return JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))

    async def test_valid_token_authenticates_and_connects(self):
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import RefreshToken
        from core.models import Project, ProjectMembership

        user = await database_sync_to_async(make_user)('jwt_ws_valid@test.com')
        project = await database_sync_to_async(Project.objects.create)(
            name='JWT WS Project', slug='jwt-ws-project', owner=user, is_active=True,
        )
        await database_sync_to_async(ProjectMembership.objects.create)(
            project=project, user=user, role='owner',
        )
        access = await database_sync_to_async(
            lambda: str(RefreshToken.for_user(user).access_token)
        )()

        communicator = WebsocketCommunicator(
            self._app(), f'/ws/v1/projects/{project.id}/listen/?token={access}'
        )
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    async def test_missing_token_falls_back_to_anonymous_and_closes(self):
        from channels.testing import WebsocketCommunicator

        communicator = WebsocketCommunicator(
            self._app(), '/ws/v1/projects/some-project/listen/'
        )
        connected, code = await communicator.connect()
        assert not connected or code == 4401

    async def test_invalid_token_falls_back_to_anonymous_and_closes(self):
        from channels.testing import WebsocketCommunicator

        communicator = WebsocketCommunicator(
            self._app(), '/ws/v1/projects/some-project/listen/?token=not-a-real-jwt'
        )
        connected, code = await communicator.connect()
        assert not connected or code == 4401

    async def test_blacklisted_token_falls_back_to_anonymous_and_closes(self):
        from channels.testing import WebsocketCommunicator
        from rest_framework_simplejwt.tokens import RefreshToken
        from jwt import decode as jwt_decode
        from django.conf import settings
        from core.models import RefreshTokenBlacklist

        user = await database_sync_to_async(make_user)('jwt_ws_blacklisted@test.com')
        access_token = await database_sync_to_async(
            lambda: RefreshToken.for_user(user).access_token
        )()
        decoded = jwt_decode(
            str(access_token), settings.SIMPLE_JWT['SIGNING_KEY'], algorithms=['HS256']
        )
        from datetime import datetime, timezone as dt_timezone
        await database_sync_to_async(RefreshTokenBlacklist.objects.create)(
            jti=decoded['jti'], user=user,
            expires_at=datetime.fromtimestamp(decoded['exp'], tz=dt_timezone.utc),
        )

        communicator = WebsocketCommunicator(
            self._app(), f'/ws/v1/projects/some-project/listen/?token={access_token}'
        )
        connected, code = await communicator.connect()
        assert not connected or code == 4401
