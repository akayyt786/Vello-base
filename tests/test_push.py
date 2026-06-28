"""
Phase 4: Push Notifications tests.
Covers DeviceToken, Topic, PushNotification, and NotificationCampaign
models, views, and Celery tasks (mocked Redis + Celery).
"""

import json
import uuid
from unittest.mock import MagicMock, patch, call

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Project, ProjectMembership, UserProfile
from push.models import (
    DeviceToken,
    Topic,
    TopicSubscription,
    PushNotification,
    NotificationCampaign,
)
from push import tasks as push_tasks


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_client(user):
    refresh = RefreshToken.for_user(user)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return c


@pytest.fixture
def owner(db):
    u = User.objects.create_user('push_owner@ex.com', 'push_owner@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def viewer(db):
    u = User.objects.create_user('push_viewer@ex.com', 'push_viewer@ex.com', 'pass123')
    UserProfile.objects.create(user=u, sign_in_provider='password', email_verified=True)
    return u


@pytest.fixture
def project(db, owner):
    p = Project.objects.create(name='PushProj', slug='push-proj', owner=owner, is_active=True)
    ProjectMembership.objects.create(project=p, user=owner, role='owner')
    return p


@pytest.fixture
def project_with_viewer(db, project, viewer):
    ProjectMembership.objects.create(project=project, user=viewer, role='viewer')
    return project


@pytest.fixture
def owner_client(owner):
    return make_client(owner)


@pytest.fixture
def viewer_client(viewer):
    return make_client(viewer)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def fcm_token(db, project):
    return DeviceToken.objects.create(
        project=project,
        platform=DeviceToken.PLATFORM_FCM,
        token='fcm-test-token-abcdefg',
        is_active=True,
    )


@pytest.fixture
def apns_token(db, project):
    return DeviceToken.objects.create(
        project=project,
        platform=DeviceToken.PLATFORM_APNS,
        token='apns-test-token-hijklmn',
        is_active=True,
    )


@pytest.fixture
def web_token(db, project):
    return DeviceToken.objects.create(
        project=project,
        platform=DeviceToken.PLATFORM_WEB,
        token='web-test-token-opqrstu',
        is_active=True,
    )


@pytest.fixture
def topic(db, project):
    return Topic.objects.create(
        project=project,
        name='news',
        description='Breaking news topic',
    )


@pytest.fixture
def push_notification(db, project, fcm_token):
    return PushNotification.objects.create(
        project=project,
        title='Hello',
        body='World',
        device_token=fcm_token,
        status=PushNotification.STATUS_PENDING,
    )


@pytest.fixture
def campaign(db, project):
    return NotificationCampaign.objects.create(
        project=project,
        name='Summer Sale',
        title='Big Sale!',
        body='50% off everything today.',
        status=NotificationCampaign.STATUS_DRAFT,
    )


# ---------------------------------------------------------------------------
# TestDeviceTokenAPI
# ---------------------------------------------------------------------------

class TestDeviceTokenAPI:
    LIST_URL = '/api/projects/{project_id}/push/tokens/'
    REGISTER_URL = '/api/projects/{project_id}/push/tokens/register/'
    UNREGISTER_URL = '/api/projects/{project_id}/push/tokens/{pk}/unregister/'

    def test_register_device_token_fcm(self, owner_client, project):
        resp = owner_client.post(
            self.REGISTER_URL.format(project_id=project.id),
            {'platform': 'fcm', 'token': 'fcm-registration-token-12345'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['platform'] == 'fcm'
        assert data['token'] == 'fcm-registration-token-12345'
        assert data['is_active'] is True

    def test_register_device_token_apns(self, owner_client, project):
        resp = owner_client.post(
            self.REGISTER_URL.format(project_id=project.id),
            {'platform': 'apns', 'token': 'apns-device-token-xyz987'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['platform'] == 'apns'
        assert data['is_active'] is True

    def test_register_device_token_web(self, owner_client, project):
        resp = owner_client.post(
            self.REGISTER_URL.format(project_id=project.id),
            {'platform': 'web', 'token': 'web-push-subscription-endpoint-abc'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['platform'] == 'web'
        assert data['is_active'] is True

    def test_register_duplicate_token_updates_existing(self, owner_client, project, fcm_token):
        # fcm_token already exists in DB; register the same (project, platform, token) triple
        resp = owner_client.post(
            self.REGISTER_URL.format(project_id=project.id),
            {'platform': 'fcm', 'token': fcm_token.token},
            format='json',
        )
        # upsert → HTTP 200 (not 201)
        assert resp.status_code == 200
        data = resp.json()
        assert data['id'] == str(fcm_token.id)
        assert data['is_active'] is True
        # Only one record should exist
        assert DeviceToken.objects.filter(
            project=project, platform='fcm', token=fcm_token.token
        ).count() == 1

    def test_unregister_device_token(self, owner_client, project, fcm_token):
        resp = owner_client.post(
            self.UNREGISTER_URL.format(project_id=project.id, pk=fcm_token.id),
        )
        assert resp.status_code == 200
        assert resp.json()['detail'] == 'Token deactivated.'
        fcm_token.refresh_from_db()
        assert fcm_token.is_active is False

    def test_unauthenticated_cannot_register(self, api_client, project):
        resp = api_client.post(
            self.REGISTER_URL.format(project_id=project.id),
            {'platform': 'fcm', 'token': 'some-token'},
            format='json',
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TestTopicAPI
# ---------------------------------------------------------------------------

class TestTopicAPI:
    LIST_URL = '/api/projects/{project_id}/push/topics/'
    DETAIL_URL = '/api/projects/{project_id}/push/topics/{pk}/'
    SUBSCRIBE_URL = '/api/projects/{project_id}/push/topics/{pk}/subscribe/'
    UNSUBSCRIBE_URL = '/api/projects/{project_id}/push/topics/{pk}/unsubscribe/'

    def test_create_topic(self, owner_client, project):
        resp = owner_client.post(
            self.LIST_URL.format(project_id=project.id),
            {'name': 'promotions', 'description': 'Promo notifications'},
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == 'promotions'
        assert data['description'] == 'Promo notifications'

    def test_list_topics(self, owner_client, project, topic):
        resp = owner_client.get(self.LIST_URL.format(project_id=project.id))
        assert resp.status_code == 200
        data = resp.json()
        # DRF router returns a list for ModelViewSet
        results = data if isinstance(data, list) else data.get('results', data)
        names = [t['name'] for t in results]
        assert 'news' in names

    def test_subscribe_to_topic(self, owner_client, project, topic, fcm_token):
        resp = owner_client.post(
            self.SUBSCRIBE_URL.format(project_id=project.id, pk=topic.id),
            {'device_token_id': str(fcm_token.id)},
            format='json',
        )
        assert resp.status_code == 201
        assert TopicSubscription.objects.filter(topic=topic, device_token=fcm_token).exists()

    def test_unsubscribe_from_topic(self, owner_client, project, topic, fcm_token):
        TopicSubscription.objects.create(topic=topic, device_token=fcm_token)
        resp = owner_client.post(
            self.UNSUBSCRIBE_URL.format(project_id=project.id, pk=topic.id),
            {'device_token_id': str(fcm_token.id)},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.json()['detail'] == 'Unsubscribed.'
        assert not TopicSubscription.objects.filter(topic=topic, device_token=fcm_token).exists()

    def test_duplicate_subscription_fails_gracefully(self, owner_client, project, topic, fcm_token):
        # First subscription
        owner_client.post(
            self.SUBSCRIBE_URL.format(project_id=project.id, pk=topic.id),
            {'device_token_id': str(fcm_token.id)},
            format='json',
        )
        # Second subscription for the same (topic, device_token) pair
        resp = owner_client.post(
            self.SUBSCRIBE_URL.format(project_id=project.id, pk=topic.id),
            {'device_token_id': str(fcm_token.id)},
            format='json',
        )
        # get_or_create → returns the existing record with HTTP 200
        assert resp.status_code == 200
        assert TopicSubscription.objects.filter(topic=topic, device_token=fcm_token).count() == 1


# ---------------------------------------------------------------------------
# TestPushNotificationAPI
# ---------------------------------------------------------------------------

class TestPushNotificationAPI:
    LIST_URL = '/api/projects/{project_id}/push/notifications/'

    @patch('push.tasks.deliver_push_notification')
    def test_send_to_device_token(self, mock_task, owner_client, project, fcm_token):
        mock_task.delay.return_value = MagicMock(id='task-abc')
        resp = owner_client.post(
            self.LIST_URL.format(project_id=project.id),
            {
                'title': 'Alert',
                'body': 'Something happened',
                'device_token': str(fcm_token.id),
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['title'] == 'Alert'
        # The view queues the task after saving; verify status starts as 'pending'
        assert data['status'] == 'pending'
        mock_task.delay.assert_called_once_with(data['id'])

    @patch('push.tasks.deliver_push_notification')
    def test_send_to_topic(self, mock_task, owner_client, project, topic):
        mock_task.delay.return_value = MagicMock(id='task-def')
        resp = owner_client.post(
            self.LIST_URL.format(project_id=project.id),
            {
                'title': 'News Flash',
                'body': 'Big news today',
                'topic': str(topic.id),
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['topic'] == str(topic.id)
        mock_task.delay.assert_called_once_with(data['id'])

    def test_list_notifications(self, owner_client, project, push_notification):
        resp = owner_client.get(self.LIST_URL.format(project_id=project.id))
        assert resp.status_code == 200
        results = resp.json()
        items = results if isinstance(results, list) else results.get('results', results)
        ids = [n['id'] for n in items]
        assert str(push_notification.id) in ids

    def test_notification_requires_token_or_topic(self, owner_client, project):
        resp = owner_client.post(
            self.LIST_URL.format(project_id=project.id),
            {'title': 'Missing target', 'body': 'No device or topic specified'},
            format='json',
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TestCampaignAPI
# ---------------------------------------------------------------------------

class TestCampaignAPI:
    LIST_URL = '/api/projects/{project_id}/push/campaigns/'
    DETAIL_URL = '/api/projects/{project_id}/push/campaigns/{pk}/'
    SEND_URL = '/api/projects/{project_id}/push/campaigns/{pk}/send/'

    def test_create_campaign_draft(self, owner_client, project):
        resp = owner_client.post(
            self.LIST_URL.format(project_id=project.id),
            {
                'name': 'Black Friday',
                'title': '50% OFF',
                'body': 'Limited time deal',
            },
            format='json',
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == 'Black Friday'
        assert data['status'] == 'draft'

    @patch('push.tasks.send_campaign')
    def test_send_campaign(self, mock_send_campaign, owner_client, project, campaign, fcm_token):
        mock_send_campaign.delay.return_value = MagicMock(id='camp-task-1')

        resp = owner_client.post(
            self.SEND_URL.format(project_id=project.id, pk=campaign.id),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data['status'] == 'queued'
        assert data['task_id'] == 'camp-task-1'
        mock_send_campaign.delay.assert_called_once_with(str(campaign.id))

    @pytest.mark.django_db
    def test_campaign_filters_by_platform(self, db, project, owner):
        """
        The send_campaign task must respect target_platforms filtering.
        Verify that with target_platforms=['apns'] only APNs tokens are targeted.
        """
        # Create tokens for each platform
        fcm = DeviceToken.objects.create(
            project=project, platform='fcm', token='fcm-camp-filter', is_active=True
        )
        apns = DeviceToken.objects.create(
            project=project, platform='apns', token='apns-camp-filter', is_active=True
        )
        web = DeviceToken.objects.create(
            project=project, platform='web', token='web-camp-filter', is_active=True
        )

        campaign = NotificationCampaign.objects.create(
            project=project,
            name='APNs Only',
            title='iOS Exclusive',
            body='Only for Apple devices',
            target_platforms=['apns'],
            status=NotificationCampaign.STATUS_DRAFT,
        )

        with patch('push.tasks.deliver_push_notification') as mock_deliver:
            mock_deliver.delay.return_value = MagicMock(id='x')
            result = push_tasks.send_campaign(str(campaign.id))

        assert result['total_sent'] == 1
        # One PushNotification should exist and it must target the APNs token
        notifications = PushNotification.objects.filter(project=project)
        assert notifications.count() == 1
        assert notifications.first().device_token_id == apns.id


# ---------------------------------------------------------------------------
# TestDeliverTask
# ---------------------------------------------------------------------------

class TestDeliverTask:
    @pytest.mark.django_db
    def test_deliver_push_notification_enqueues_to_redis(self, db, project, fcm_token):
        """
        deliver_push_notification should call redis.rpush with the job JSON
        on the 'ownfb:push:queue' key.
        """
        notification = PushNotification.objects.create(
            project=project,
            title='Test Push',
            body='Test body',
            device_token=fcm_token,
            status=PushNotification.STATUS_PENDING,
        )

        mock_redis = MagicMock()

        with patch('django_redis.get_redis_connection', return_value=mock_redis):
            result = push_tasks.deliver_push_notification(str(notification.id))

        assert result['queued'] is True
        assert result['notification_id'] == str(notification.id)

        # Verify RPUSH was called with the correct queue key
        mock_redis.rpush.assert_called_once()
        call_args = mock_redis.rpush.call_args
        queue_key = call_args[0][0]
        job_payload = json.loads(call_args[0][1])

        assert queue_key == 'ownfb:push:queue'
        assert job_payload['notification_id'] == str(notification.id)
        assert job_payload['platform'] == 'fcm'
        assert job_payload['token'] == fcm_token.token
        assert job_payload['title'] == 'Test Push'
        assert job_payload['body'] == 'Test body'

        # Notification status should be updated to 'queued'
        notification.refresh_from_db()
        assert notification.status == PushNotification.STATUS_QUEUED

    @pytest.mark.django_db
    def test_deliver_push_notification_skips_missing_notification(self, db):
        result = push_tasks.deliver_push_notification(str(uuid.uuid4()))
        assert result['skipped'] is True
        assert result['reason'] == 'notification_not_found'

    @pytest.mark.django_db
    def test_deliver_push_notification_fails_on_inactive_token(self, db, project):
        inactive_token = DeviceToken.objects.create(
            project=project,
            platform='fcm',
            token='inactive-token',
            is_active=False,
        )
        notification = PushNotification.objects.create(
            project=project,
            title='Will Fail',
            body='No active token',
            device_token=inactive_token,
            status=PushNotification.STATUS_PENDING,
        )
        result = push_tasks.deliver_push_notification(str(notification.id))
        assert result['status'] == 'failed'
        assert result['reason'] == 'no_active_token'
        notification.refresh_from_db()
        assert notification.status == PushNotification.STATUS_FAILED

    @pytest.mark.django_db
    def test_send_campaign_task_creates_notifications(self, db, project, owner):
        """
        send_campaign should create one PushNotification per active device token
        and call deliver_push_notification.delay for each one.
        """
        tokens = [
            DeviceToken.objects.create(
                project=project,
                platform='fcm',
                token=f'token-{i}',
                is_active=True,
            )
            for i in range(3)
        ]

        camp = NotificationCampaign.objects.create(
            project=project,
            name='All Devices',
            title='Hello Everyone',
            body='Global broadcast',
            status=NotificationCampaign.STATUS_DRAFT,
        )

        with patch('push.tasks.deliver_push_notification') as mock_deliver:
            mock_deliver.delay.return_value = MagicMock(id='x')
            result = push_tasks.send_campaign(str(camp.id))

        assert result['total_sent'] == 3
        assert result['total_failed'] == 0
        assert PushNotification.objects.filter(project=project).count() == 3
        assert mock_deliver.delay.call_count == 3

        camp.refresh_from_db()
        assert camp.status == NotificationCampaign.STATUS_SENT
        assert camp.total_sent == 3
        assert camp.total_failed == 0
        assert camp.sent_at is not None

    @pytest.mark.django_db
    def test_send_campaign_task_skips_missing_campaign(self, db):
        result = push_tasks.send_campaign(str(uuid.uuid4()))
        assert result['skipped'] is True
        assert result['reason'] == 'campaign_not_found'

    @pytest.mark.django_db
    def test_send_campaign_task_skips_inactive_tokens(self, db, project, owner):
        """Inactive tokens should not receive PushNotifications."""
        DeviceToken.objects.create(
            project=project, platform='fcm', token='active-tok', is_active=True
        )
        DeviceToken.objects.create(
            project=project, platform='fcm', token='inactive-tok', is_active=False
        )

        camp = NotificationCampaign.objects.create(
            project=project,
            name='Active Only',
            title='Hi',
            body='Only active devices',
            status=NotificationCampaign.STATUS_DRAFT,
        )

        with patch('push.tasks.deliver_push_notification') as mock_deliver:
            mock_deliver.delay.return_value = MagicMock(id='y')
            result = push_tasks.send_campaign(str(camp.id))

        assert result['total_sent'] == 1
        assert PushNotification.objects.filter(project=project).count() == 1
