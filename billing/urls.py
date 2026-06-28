from django.urls import path
from .views import SubscriptionView, QuotaUsageView, TiersView

app_name = 'billing'

urlpatterns = [
    path('subscription/', SubscriptionView.as_view(), name='subscription'),
    path('usage/', QuotaUsageView.as_view(), name='usage'),
]
