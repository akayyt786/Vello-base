"""Tests for OwnFirebase Push Notifications SDK."""

import pytest
from unittest.mock import Mock, patch
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.push import PushSDK


class TestPushSDK:
    """Tests for the Push Notifications SDK."""

    def test_push_init(self):
        """Test Push SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)
        assert push.base_url == 'http://localhost:8000'
        assert push.project_id == 'test-project'

    @patch('requests.request')
    def test_register_device(self, mock_request):
        """Test registering a device for push notifications."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'device_id': 'device-123',
            'user_id': 'user-456',
            'token': 'push-token-xyz',
            'platform': 'ios',
            'registered_at': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'POST',
            push.project_url('push/devices'),
            json_data={
                'token': 'push-token-xyz',
                'platform': 'ios',
                'user_id': 'user-456'
            }
        )

        assert result['device_id'] == 'device-123'
        assert result['platform'] == 'ios'

    @patch('requests.request')
    def test_send_notification(self, mock_request):
        """Test sending a push notification."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'notification_id': 'notif-123',
            'status': 'sent',
            'recipient_count': 1,
            'sent_at': '2024-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'POST',
            push.project_url('push/send'),
            json_data={
                'to': 'device-123',
                'title': 'Hello',
                'body': 'This is a test notification',
                'data': {'action': 'open_app'}
            }
        )

        assert result['notification_id'] == 'notif-123'
        assert result['status'] == 'sent'

    @patch('requests.request')
    def test_send_notification_to_topic(self, mock_request):
        """Test sending notification to a topic."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'notification_id': 'notif-topic-1',
            'topic': 'sports_news',
            'status': 'sent',
            'recipient_count': 5000
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'POST',
            push.project_url('push/send-to-topic'),
            json_data={
                'topic': 'sports_news',
                'title': 'Breaking News',
                'body': 'New sports update available'
            }
        )

        assert result['topic'] == 'sports_news'
        assert result['recipient_count'] == 5000

    @patch('requests.request')
    def test_send_notification_to_condition(self, mock_request):
        """Test sending notification to users matching condition."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'notification_id': 'notif-cond-1',
            'condition': "'premium' in topics && 'news' in topics",
            'status': 'sent',
            'recipient_count': 1500
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'POST',
            push.project_url('push/send-to-condition'),
            json_data={
                'condition': "'premium' in topics && 'news' in topics",
                'title': 'Premium News',
                'body': 'Exclusive news for premium users'
            }
        )

        assert result['recipient_count'] == 1500

    @patch('requests.request')
    def test_subscribe_to_topic(self, mock_request):
        """Test subscribing a device to a topic."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'subscribed'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'POST',
            push.project_url('push/devices/device-123/subscribe'),
            json_data={'topic': 'sports_news'}
        )

        assert result['status'] == 'subscribed'

    @patch('requests.request')
    def test_unsubscribe_from_topic(self, mock_request):
        """Test unsubscribing a device from a topic."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'DELETE',
            push.project_url('push/devices/device-123/unsubscribe'),
            json_data={'topic': 'sports_news'}
        )

        assert result is None

    @patch('requests.request')
    def test_get_notification_status(self, mock_request):
        """Test getting notification delivery status."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'notification_id': 'notif-123',
            'status': 'delivered',
            'sent_count': 1000,
            'delivered_count': 950,
            'failed_count': 50
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'GET',
            push.project_url('push/notifications/notif-123')
        )

        assert result['delivered_count'] == 950

    @patch('requests.request')
    def test_delete_device(self, mock_request):
        """Test deleting a device registration."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        result = push.request(
            'DELETE',
            push.project_url('push/devices/device-123')
        )

        assert result is None


class TestPushWorkflow:
    """Integration tests for push notification workflows."""

    @patch('requests.request')
    def test_complete_push_workflow(self, mock_request):
        """Test complete workflow: register -> subscribe -> send."""
        responses = [
            # Register device
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'device_id': 'device-flow',
                'token': 'token-xyz',
                'platform': 'android'
            })),
            # Subscribe to topic
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'status': 'subscribed'
            })),
            # Send notification
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'notification_id': 'notif-flow',
                'status': 'sent',
                'recipient_count': 1
            })),
            # Get status
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'notification_id': 'notif-flow',
                'status': 'delivered',
                'delivered_count': 1
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        # Register device
        device = push.request(
            'POST',
            push.project_url('push/devices'),
            json_data={'token': 'token-xyz', 'platform': 'android'}
        )

        # Subscribe to topic
        push.request(
            'POST',
            push.project_url(f"push/devices/{device['device_id']}/subscribe"),
            json_data={'topic': 'updates'}
        )

        # Send notification
        notif = push.request(
            'POST',
            push.project_url('push/send-to-topic'),
            json_data={'topic': 'updates', 'title': 'Update'}
        )

        # Check status
        status = push.request(
            'GET',
            push.project_url(f"push/notifications/{notif['notification_id']}")
        )

        assert status['delivered_count'] == 1

    @patch('requests.request')
    def test_multidevice_notification(self, mock_request):
        """Test sending to multiple devices."""
        responses = [
            # Register device 1
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'device_id': 'device-1'
            })),
            # Register device 2
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'device_id': 'device-2'
            })),
            # Send to topic
            Mock(ok=True, status_code=201, json=Mock(return_value={
                'notification_id': 'notif-multi',
                'recipient_count': 2,
                'status': 'sent'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        push = PushSDK(config)

        # Register multiple devices
        dev1 = push.request(
            'POST',
            push.project_url('push/devices'),
            json_data={'token': 'token-1', 'platform': 'ios'}
        )

        dev2 = push.request(
            'POST',
            push.project_url('push/devices'),
            json_data={'token': 'token-2', 'platform': 'android'}
        )

        # Send to topic with 2 subscribers
        notif = push.request(
            'POST',
            push.project_url('push/send-to-topic'),
            json_data={'topic': 'updates', 'title': 'Hello'}
        )

        assert notif['recipient_count'] == 2
