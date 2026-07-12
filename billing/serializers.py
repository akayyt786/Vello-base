from rest_framework import serializers
from .models import ProjectSubscription, QuotaUsage, TIER_LIMITS


class ProjectSubscriptionSerializer(serializers.ModelSerializer):
    limits = serializers.SerializerMethodField()

    class Meta:
        model = ProjectSubscription
        fields = ['id', 'tier', 'limits', 'billing_email', 'trial_ends_at', 'created_at', 'updated_at']
        # tier is deliberately read-only here: it must only change via a
        # verified Stripe checkout/webhook flow (billing/stripe_service.py),
        # never directly through this API — otherwise any project editor
        # could PATCH themselves straight to 'enterprise' for free.
        read_only_fields = ['id', 'tier', 'limits', 'created_at', 'updated_at']

    def get_limits(self, obj):
        return obj.get_limits()


class QuotaUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotaUsage
        fields = ['year', 'month', 'api_calls', 'function_invocations', 'ai_tokens', 'storage_bytes', 'updated_at']
