"""URL configuration for the Analytics app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'analytics'

from .views import (
    EventViewSet,
    UserPropertyViewSet,
    ConversionEventViewSet,
    AnalyticsQueryView,
)

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'user-properties', UserPropertyViewSet, basename='userproperty')
router.register(r'conversion-events', ConversionEventViewSet, basename='conversionevent')

urlpatterns = [
    path('', include(router.urls)),
    path('query/', AnalyticsQueryView.as_view(), name='analytics-query'),
]
