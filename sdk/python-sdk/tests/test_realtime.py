"""Tests for OwnFirebase Realtime SDK."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.realtime import RealtimeSDK


class TestRealtimeSDK:
    """Tests for the Realtime SDK."""

    def test_realtime_init(self):
        """Test Realtime SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)
        assert realtime.base_url == 'http://localhost:8000'
        assert realtime.project_id == 'test-project'

    @patch('requests.request')
    def test_get_realtime_url(self, mock_request):
        """Test getting WebSocket URL for realtime connection."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ws_url': 'ws://localhost:8000/ws/test-project/realtime',
            'token': 'ws-token-123'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        result = realtime.request(
            'GET',
            realtime.project_url('realtime/connect')
        )

        assert result['ws_url'] == 'ws://localhost:8000/ws/test-project/realtime'
        assert result['token'] == 'ws-token-123'

    @patch('requests.request')
    def test_subscribe_to_collection(self, mock_request):
        """Test subscribing to collection changes."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subscription_id': 'sub-123',
            'collection': 'users',
            'status': 'subscribed'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        result = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={'collection': 'users'}
        )

        assert result['subscription_id'] == 'sub-123'
        assert result['status'] == 'subscribed'

    @patch('requests.request')
    def test_subscribe_to_document(self, mock_request):
        """Test subscribing to specific document changes."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subscription_id': 'sub-doc-456',
            'collection': 'users',
            'document_id': 'user-123',
            'status': 'subscribed'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        result = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={'collection': 'users', 'document_id': 'user-123'}
        )

        assert result['document_id'] == 'user-123'

    @patch('requests.request')
    def test_unsubscribe(self, mock_request):
        """Test unsubscribing from realtime updates."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        result = realtime.request(
            'DELETE',
            realtime.project_url('realtime/subscriptions/sub-123')
        )

        assert result is None

    @patch('requests.request')
    def test_list_subscriptions(self, mock_request):
        """Test listing active subscriptions."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subscriptions': [
                {
                    'subscription_id': 'sub-1',
                    'collection': 'users',
                    'created_at': '2024-01-01T00:00:00Z'
                },
                {
                    'subscription_id': 'sub-2',
                    'collection': 'posts',
                    'document_id': 'post-123',
                    'created_at': '2024-01-01T00:05:00Z'
                }
            ],
            'total': 2
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        result = realtime.request(
            'GET',
            realtime.project_url('realtime/subscriptions')
        )

        assert len(result['subscriptions']) == 2

    @patch('requests.request')
    def test_subscribe_with_filters(self, mock_request):
        """Test subscribing to collection with filters."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subscription_id': 'sub-filtered',
            'collection': 'users',
            'filter': {'status': 'active'},
            'status': 'subscribed'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        result = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={
                'collection': 'users',
                'filter': {'status': 'active'}
            }
        )

        assert result['subscription_id'] == 'sub-filtered'

    @patch('requests.request')
    def test_get_subscription_info(self, mock_request):
        """Test getting subscription details."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'subscription_id': 'sub-123',
            'collection': 'users',
            'status': 'subscribed',
            'created_at': '2024-01-01T00:00:00Z',
            'message_count': 42
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        result = realtime.request(
            'GET',
            realtime.project_url('realtime/subscriptions/sub-123')
        )

        assert result['message_count'] == 42

    @patch('requests.request')
    def test_subscription_not_found(self, mock_request):
        """Test retrieving non-existent subscription."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.reason = 'Not Found'
        mock_response.json.return_value = {'error': 'Subscription not found'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        with pytest.raises(APIError) as exc_info:
            realtime.request(
                'GET',
                realtime.project_url('realtime/subscriptions/nonexistent')
            )

        assert exc_info.value.status == 404


class TestRealtimeSubscriptionFlow:
    """Integration tests for realtime subscription workflows."""

    @patch('requests.request')
    def test_complete_subscription_lifecycle(self, mock_request):
        """Test complete lifecycle: subscribe -> get updates -> unsubscribe."""
        responses = [
            # Subscribe to collection
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscription_id': 'sub-lifecycle',
                'collection': 'users',
                'status': 'subscribed'
            })),
            # Get subscription info
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscription_id': 'sub-lifecycle',
                'collection': 'users',
                'status': 'subscribed',
                'message_count': 5
            })),
            # Unsubscribe
            Mock(ok=True, status_code=204)
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        # Subscribe
        sub_response = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={'collection': 'users'}
        )
        sub_id = sub_response['subscription_id']

        # Check subscription status
        info = realtime.request(
            'GET',
            realtime.project_url(f'realtime/subscriptions/{sub_id}')
        )
        assert info['message_count'] == 5

        # Unsubscribe
        result = realtime.request(
            'DELETE',
            realtime.project_url(f'realtime/subscriptions/{sub_id}')
        )
        assert result is None

    @patch('requests.request')
    def test_multiple_subscriptions(self, mock_request):
        """Test managing multiple subscriptions."""
        responses = [
            # Subscribe to users
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscription_id': 'sub-users',
                'collection': 'users'
            })),
            # Subscribe to posts
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscription_id': 'sub-posts',
                'collection': 'posts'
            })),
            # Subscribe to comments
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscription_id': 'sub-comments',
                'collection': 'comments'
            })),
            # List all subscriptions
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscriptions': [
                    {'subscription_id': 'sub-users', 'collection': 'users'},
                    {'subscription_id': 'sub-posts', 'collection': 'posts'},
                    {'subscription_id': 'sub-comments', 'collection': 'comments'}
                ],
                'total': 3
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        # Subscribe to multiple collections
        sub1 = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={'collection': 'users'}
        )

        sub2 = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={'collection': 'posts'}
        )

        sub3 = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={'collection': 'comments'}
        )

        # List all subscriptions
        subs_list = realtime.request(
            'GET',
            realtime.project_url('realtime/subscriptions')
        )

        assert subs_list['total'] == 3

    @patch('requests.request')
    def test_subscription_with_query_filters(self, mock_request):
        """Test subscription with specific query filters."""
        responses = [
            # Subscribe with filters
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscription_id': 'sub-filtered',
                'collection': 'posts',
                'filter': {'author_id': 'user-123', 'status': 'published'},
                'status': 'subscribed'
            })),
            # Get filtered subscription info
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'subscription_id': 'sub-filtered',
                'collection': 'posts',
                'filter': {'author_id': 'user-123', 'status': 'published'},
                'message_count': 10
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        realtime = RealtimeSDK(config)

        # Subscribe with filters
        sub = realtime.request(
            'POST',
            realtime.project_url('realtime/subscribe'),
            json_data={
                'collection': 'posts',
                'filter': {'author_id': 'user-123', 'status': 'published'}
            }
        )

        # Get subscription details
        info = realtime.request(
            'GET',
            realtime.project_url(f'realtime/subscriptions/{sub["subscription_id"]}')
        )

        assert info['message_count'] == 10
