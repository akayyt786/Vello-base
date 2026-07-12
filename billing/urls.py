from django.urls import path
from .views import (
    SubscriptionView,
    QuotaUsageView,
    TiersView,
    CreateCheckoutSessionView,
    BillingPortalView,
)

app_name = 'billing'

urlpatterns = [
    path('subscription/', SubscriptionView.as_view(), name='subscription'),
    path('usage/', QuotaUsageView.as_view(), name='usage'),
    path('checkout/', CreateCheckoutSessionView.as_view(), name='checkout'),
    path('portal/', BillingPortalView.as_view(), name='portal'),
]
