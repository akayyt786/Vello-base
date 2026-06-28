import uuid
from django.db import models


class PlanTier(models.TextChoices):
    FREE = 'free', 'Free'
    STARTER = 'starter', 'Starter'
    PRO = 'pro', 'Pro'
    ENTERPRISE = 'enterprise', 'Enterprise'


# Default limits per tier
TIER_LIMITS = {
    'free':       {'api_calls_monthly': 10_000,  'storage_bytes': 500_000_000,   'function_invocations': 1_000,    'ai_tokens': 50_000},
    'starter':    {'api_calls_monthly': 100_000, 'storage_bytes': 5_000_000_000,  'function_invocations': 50_000,   'ai_tokens': 500_000},
    'pro':        {'api_calls_monthly': 1_000_000,'storage_bytes': 50_000_000_000,'function_invocations': 500_000,  'ai_tokens': 5_000_000},
    'enterprise': {'api_calls_monthly': -1,       'storage_bytes': -1,            'function_invocations': -1,       'ai_tokens': -1},
}


class ProjectSubscription(models.Model):
    """Billing plan attached to a project."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.OneToOneField('core.Project', on_delete=models.CASCADE, related_name='subscription')
    tier = models.CharField(max_length=32, choices=PlanTier.choices, default=PlanTier.FREE)
    # Override limits (None = use tier defaults)
    custom_api_calls_monthly = models.IntegerField(null=True, blank=True)
    custom_storage_bytes = models.BigIntegerField(null=True, blank=True)
    custom_function_invocations = models.IntegerField(null=True, blank=True)
    custom_ai_tokens = models.IntegerField(null=True, blank=True)
    billing_email = models.EmailField(blank=True)
    stripe_customer_id = models.CharField(max_length=128, blank=True)
    stripe_subscription_id = models.CharField(max_length=128, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_limits(self):
        base = TIER_LIMITS.get(self.tier, TIER_LIMITS['free']).copy()
        if self.custom_api_calls_monthly is not None:
            base['api_calls_monthly'] = self.custom_api_calls_monthly
        if self.custom_storage_bytes is not None:
            base['storage_bytes'] = self.custom_storage_bytes
        if self.custom_function_invocations is not None:
            base['function_invocations'] = self.custom_function_invocations
        if self.custom_ai_tokens is not None:
            base['ai_tokens'] = self.custom_ai_tokens
        return base

    def __str__(self):
        return f"{self.project} [{self.tier}]"


class QuotaUsage(models.Model):
    """Monthly usage counters per project. Reset monthly."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name='quota_usages')
    year = models.IntegerField()
    month = models.IntegerField()
    api_calls = models.BigIntegerField(default=0)
    function_invocations = models.BigIntegerField(default=0)
    ai_tokens = models.BigIntegerField(default=0)
    storage_bytes = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('project', 'year', 'month')]

    def __str__(self):
        return f"{self.project} {self.year}/{self.month}"
