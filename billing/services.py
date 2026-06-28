"""Quota check + increment helpers. Called from middleware or view decorators."""
import logging
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from .models import ProjectSubscription, QuotaUsage

logger = logging.getLogger(__name__)


def get_or_create_usage(project):
    now = timezone.now()
    usage, _ = QuotaUsage.objects.get_or_create(
        project=project,
        year=now.year,
        month=now.month,
        defaults={},
    )
    return usage


def get_subscription(project):
    try:
        return project.subscription
    except ProjectSubscription.DoesNotExist:
        # Auto-create free tier on first access
        sub, _ = ProjectSubscription.objects.get_or_create(project=project)
        return sub


def check_quota(project, resource: str) -> dict:
    """
    Returns {'allowed': bool, 'used': int, 'limit': int, 'tier': str}.
    resource: 'api_calls_monthly' | 'function_invocations' | 'ai_tokens' | 'storage_bytes'
    """
    sub = get_subscription(project)
    limits = sub.get_limits()
    limit = limits.get(resource, 0)

    if limit == -1:  # enterprise = unlimited
        return {'allowed': True, 'used': 0, 'limit': -1, 'tier': sub.tier}

    usage = get_or_create_usage(project)
    field_map = {
        'api_calls_monthly': 'api_calls',
        'function_invocations': 'function_invocations',
        'ai_tokens': 'ai_tokens',
        'storage_bytes': 'storage_bytes',
    }
    used = getattr(usage, field_map.get(resource, 'api_calls'), 0)
    return {'allowed': used < limit, 'used': used, 'limit': limit, 'tier': sub.tier}


def increment_usage(project, resource: str, amount: int = 1):
    """Atomically increment a usage counter."""
    now = timezone.now()
    field_map = {
        'api_calls_monthly': 'api_calls',
        'function_invocations': 'function_invocations',
        'ai_tokens': 'ai_tokens',
        'storage_bytes': 'storage_bytes',
    }
    field = field_map.get(resource, 'api_calls')
    try:
        with transaction.atomic():
            QuotaUsage.objects.update_or_create(
                project=project,
                year=now.year,
                month=now.month,
                defaults={},
            )
            QuotaUsage.objects.filter(
                project=project, year=now.year, month=now.month
            ).update(**{field: F(field) + amount})
    except Exception as exc:
        logger.warning('increment_usage failed: %s', exc)
