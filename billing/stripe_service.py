"""
Stripe integration: checkout sessions, billing portal, webhook processing.

Configure via env vars: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
STRIPE_PRICE_STARTER/PRO/ENTERPRISE (see ownfirebase/settings.py).
STRIPE_API_BASE lets local dev/tests point at a stripe-mock instance
instead of the real Stripe API.
"""

import logging

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


def _configure():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.api_base = settings.STRIPE_API_BASE or stripe.api_base


def get_or_create_stripe_customer(subscription, user):
    """Return the Stripe customer id for a project, creating it on first use."""
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id

    _configure()
    customer = stripe.Customer.create(
        email=subscription.billing_email or user.email,
        metadata={'project_id': str(subscription.project_id)},
    )
    subscription.stripe_customer_id = customer['id']
    subscription.save(update_fields=['stripe_customer_id', 'updated_at'])
    return customer['id']


def create_checkout_session(subscription, user, tier, success_url, cancel_url):
    """Start a Stripe Checkout session upgrading `subscription`'s project to `tier`."""
    price_id = settings.STRIPE_PRICE_IDS.get(tier)
    if not price_id:
        raise ValueError(f'No Stripe price configured for tier "{tier}"')

    _configure()
    customer_id = get_or_create_stripe_customer(subscription, user)
    return stripe.checkout.Session.create(
        customer=customer_id,
        mode='subscription',
        line_items=[{'price': price_id, 'quantity': 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'project_id': str(subscription.project_id), 'tier': tier},
    )


def create_billing_portal_session(subscription, return_url):
    """Open the Stripe-hosted billing portal for a project's existing customer."""
    if not subscription.stripe_customer_id:
        raise ValueError('Project has no Stripe customer yet — start a checkout first.')

    _configure()
    return stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=return_url,
    )


def construct_webhook_event(payload, sig_header):
    """Verify a webhook payload's signature and return the parsed Stripe event.

    Raises ValueError (bad payload) or stripe.error.SignatureVerificationError
    (bad/missing signature) — callers should treat both as "reject with 400".
    """
    _configure()
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)


def handle_webhook_event(event):
    """
    Apply a verified Stripe event to local billing state.

    Idempotent by construction: every branch is a plain field update keyed
    on stripe_subscription_id/project_id, so replaying the same event (Stripe
    retries on any non-2xx response) just re-applies the same values.
    """
    event_type = event['type']
    # event['data']['object'] is a stripe.StripeObject, not a plain dict — it
    # supports item access (obj['x']) and attribute access (obj.x) but NOT
    # .get(), which the handlers below rely on. Convert once, up front.
    data = event['data']['object'].to_dict()

    if event_type == 'checkout.session.completed':
        _handle_checkout_completed(data)
    elif event_type == 'customer.subscription.updated':
        _sync_subscription_status(data)
    elif event_type == 'customer.subscription.deleted':
        _handle_subscription_deleted(data)
    else:
        logger.debug('Unhandled Stripe event type: %s', event_type)


def _handle_checkout_completed(session):
    from core.models import Project
    from .models import ProjectSubscription

    project_id = session.get('metadata', {}).get('project_id')
    tier = session.get('metadata', {}).get('tier')
    if not project_id or not tier:
        logger.warning('checkout.session.completed missing project_id/tier metadata; ignoring')
        return

    if not Project.objects.filter(id=project_id).exists():
        logger.warning('checkout.session.completed for unknown project_id=%s', project_id)
        return

    # update_or_create rather than filter().update(): a ProjectSubscription
    # row is normally created lazily on first access (billing/services.py:
    # get_subscription), but a webhook is an external, asynchronous system —
    # never assume that row already exists by the time Stripe calls back.
    ProjectSubscription.objects.update_or_create(
        project_id=project_id,
        defaults={
            'tier': tier,
            'stripe_subscription_id': session.get('subscription') or '',
        },
    )


def _sync_subscription_status(stripe_subscription):
    from .models import ProjectSubscription

    sub_id = stripe_subscription['id']
    status = stripe_subscription.get('status')

    if status in ('canceled', 'unpaid', 'incomplete_expired'):
        ProjectSubscription.objects.filter(stripe_subscription_id=sub_id).update(
            tier='free', stripe_subscription_id='',
        )
        return

    # The plan may have changed via the Stripe-hosted billing portal (not a
    # new checkout), so re-derive the tier from the subscription's current price.
    try:
        price_id = stripe_subscription['items']['data'][0]['price']['id']
    except (KeyError, IndexError):
        return

    price_to_tier = {v: k for k, v in settings.STRIPE_PRICE_IDS.items() if v}
    tier = price_to_tier.get(price_id)
    if tier:
        ProjectSubscription.objects.filter(stripe_subscription_id=sub_id).update(tier=tier)


def _handle_subscription_deleted(stripe_subscription):
    from .models import ProjectSubscription

    ProjectSubscription.objects.filter(
        stripe_subscription_id=stripe_subscription['id']
    ).update(tier='free', stripe_subscription_id='')
