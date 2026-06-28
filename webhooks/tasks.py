import logging
import time

import requests
from celery import shared_task
from django.utils import timezone

from .models import WebhookEndpoint, WebhookDelivery
from .signing import sign_payload
from .ssrf import assert_url_safe

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_webhook(self, delivery_id: str):
    """Deliver a webhook payload with up to 3 retries (exponential backoff)."""
    try:
        delivery = WebhookDelivery.objects.select_related('endpoint').get(pk=delivery_id)
    except WebhookDelivery.DoesNotExist:
        return

    endpoint = delivery.endpoint
    if not endpoint.is_active:
        delivery.status = 'failed'
        delivery.response_body = 'Endpoint deactivated.'
        delivery.save(update_fields=['status', 'response_body'])
        return

    # Re-validate URL at delivery time — defends against DNS rebinding attacks
    # where a hostname passed write-time validation but now resolves to internal IP.
    try:
        assert_url_safe(endpoint.url)
    except ValueError as exc:
        delivery.status = 'failed'
        delivery.response_body = f'SSRF block: {exc}'
        delivery.save(update_fields=['status', 'response_body'])
        return

    signature = sign_payload(endpoint.secret, delivery.payload)
    headers = {
        'Content-Type': 'application/json',
        'X-OwnFirebase-Signature': signature,
        'X-OwnFirebase-Event': delivery.event_type,
    }

    delivery.attempt_count += 1
    t0 = time.time()
    try:
        resp = requests.post(
            endpoint.url,
            json=delivery.payload,
            headers=headers,
            timeout=10,
            allow_redirects=False,  # Never follow redirects — re-validation would be bypassed
        )
        latency_ms = int((time.time() - t0) * 1000)
        delivery.response_status = resp.status_code
        # Store only status + length — never exfiltrate internal response body
        delivery.response_body = f'[{len(resp.content)} bytes]' if not (200 <= resp.status_code < 300) else ''
        delivery.latency_ms = latency_ms
        delivery.delivered_at = timezone.now()
        if 200 <= resp.status_code < 300:
            delivery.status = 'success'
        else:
            delivery.status = 'failed'
            raise self.retry(countdown=60 * (2 ** self.request.retries))
    except requests.RequestException as exc:
        delivery.status = 'failed'
        delivery.response_body = type(exc).__name__
        try:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            pass
    finally:
        delivery.save()


def fire_event(project_id, event_type: str, payload: dict):
    """
    Called by signals/views to fan out a webhook event to all matching endpoints.
    Creates WebhookDelivery records and enqueues Celery tasks.
    """
    endpoints = WebhookEndpoint.objects.filter(
        project_id=project_id,
        is_active=True,
    )
    full_payload = {'event': event_type, 'project_id': str(project_id), 'data': payload}
    for ep in endpoints:
        if event_type in ep.events or '*' in ep.events:
            d = WebhookDelivery.objects.create(
                endpoint=ep,
                event_type=event_type,
                payload=full_payload,
            )
            try:
                deliver_webhook.delay(str(d.id))
            except Exception as exc:
                logger.error('Failed to enqueue webhook delivery %s: %s', d.id, exc)
