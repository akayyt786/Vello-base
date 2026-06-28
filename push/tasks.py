"""
Celery tasks: deliver individual push notifications and send broadcast campaigns.
"""

import json
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_push_notification(self, notification_id):
    """
    Move a PushNotification to 'queued' and push a delivery job onto the
    Redis list ``ownfb:push:queue`` for consumption by a push gateway worker.

    The job format is intentionally platform-agnostic so the gateway can route
    by ``platform``:

        {
            "notification_id": "<uuid>",
            "platform":        "fcm" | "apns" | "web",
            "token":           "<device token string>",
            "title":           "...",
            "body":            "...",
            "data":            {...},
            "image_url":       "..."
        }
    """
    from push.models import PushNotification

    try:
        notification = PushNotification.objects.select_related('device_token').get(id=notification_id)
    except PushNotification.DoesNotExist:
        logger.warning('deliver_push_notification: notification %s not found', notification_id)
        return {'skipped': True, 'reason': 'notification_not_found'}

    notification.status = PushNotification.STATUS_QUEUED
    notification.save(update_fields=['status', 'updated_at'])

    token = notification.device_token
    if not token or not token.is_active:
        notification.status = PushNotification.STATUS_FAILED
        notification.error = 'No active device token associated with this notification.'
        notification.save(update_fields=['status', 'error', 'updated_at'])
        logger.warning(
            'deliver_push_notification: notification %s has no active device token', notification_id
        )
        return {'status': 'failed', 'reason': 'no_active_token'}

    job = {
        'notification_id': str(notification.id),
        'platform': token.platform,
        'token': token.token,
        'title': notification.title,
        'body': notification.body,
        'data': notification.data,
        'image_url': notification.image_url,
    }

    try:
        from django_redis import get_redis_connection
        redis = get_redis_connection('default')
        redis.rpush('ownfb:push:queue', json.dumps(job))
    except Exception as exc:
        logger.error(
            'deliver_push_notification: failed to enqueue notification %s: %s',
            notification_id, exc,
        )
        notification.status = PushNotification.STATUS_FAILED
        notification.error = str(exc)
        notification.save(update_fields=['status', 'error', 'updated_at'])
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

    logger.info(
        'deliver_push_notification: notification %s queued for %s delivery',
        notification_id, token.platform,
    )
    return {'queued': True, 'notification_id': str(notification.id)}


@shared_task(bind=True)
def send_campaign(self, campaign_id):
    """
    Broadcast a NotificationCampaign to all active device tokens in the project,
    optionally filtered by the campaign's target_platforms list.

    For each matching token a PushNotification is created and
    deliver_push_notification is queued asynchronously.
    """
    from push.models import NotificationCampaign, DeviceToken, PushNotification, TopicSubscription

    try:
        campaign = NotificationCampaign.objects.select_related('project', 'topic').get(id=campaign_id)
    except NotificationCampaign.DoesNotExist:
        logger.warning('send_campaign: campaign %s not found', campaign_id)
        return {'skipped': True, 'reason': 'campaign_not_found'}

    campaign.status = NotificationCampaign.STATUS_SENDING
    campaign.save(update_fields=['status', 'updated_at'])

    tokens_qs = DeviceToken.objects.filter(project=campaign.project, is_active=True)
    if campaign.target_platforms:
        tokens_qs = tokens_qs.filter(platform__in=campaign.target_platforms)
    # If the campaign targets a specific topic, limit delivery to subscribed devices only.
    if campaign.topic:
        subscribed_ids = TopicSubscription.objects.filter(
            topic=campaign.topic,
        ).values_list('device_token_id', flat=True)
        tokens_qs = tokens_qs.filter(id__in=subscribed_ids)

    total_sent = 0
    total_failed = 0

    with transaction.atomic():
        for token in tokens_qs.iterator():
            try:
                notification = PushNotification.objects.create(
                    project=campaign.project,
                    title=campaign.title,
                    body=campaign.body,
                    data=campaign.data,
                    image_url=campaign.image_url,
                    device_token=token,
                    status=PushNotification.STATUS_PENDING,
                )
                deliver_push_notification.delay(str(notification.id))
                total_sent += 1
            except Exception as exc:
                logger.error(
                    'send_campaign: failed to create/queue notification for token %s in campaign %s: %s',
                    token.id, campaign_id, exc,
                )
                total_failed += 1

        campaign.status = NotificationCampaign.STATUS_SENT
        campaign.sent_at = timezone.now()
        campaign.total_sent = total_sent
        campaign.total_failed = total_failed
        campaign.save(update_fields=['status', 'sent_at', 'total_sent', 'total_failed', 'updated_at'])

    logger.info(
        'send_campaign: campaign %s complete — sent=%d failed=%d',
        campaign_id, total_sent, total_failed,
    )
    return {
        'campaign_id': str(campaign_id),
        'total_sent': total_sent,
        'total_failed': total_failed,
    }
