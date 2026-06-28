"""URL configuration for the Analytics app."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'analytics'

from .views import (
    EventViewSet,
    UserPropertyViewSet,
    ConversionEventViewSet,
    AnalyticsQueryView,
    TrackEventView,
    BatchTrackView,
    SDKEventSummaryView,
    SDKEventListView,
)

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'user-properties', UserPropertyViewSet, basename='userproperty')
router.register(r'conversion-events', ConversionEventViewSet, basename='conversionevent')

urlpatterns = [
    path('', include(router.urls)),
    path('query/', AnalyticsQueryView.as_view(), name='analytics-query'),
    # Phase 6 SDK endpoints
    path('track/', TrackEventView.as_view(), name='track'),
    path('batch/', BatchTrackView.as_view(), name='batch'),
    path('sdk-summary/', SDKEventSummaryView.as_view(), name='sdk-summary'),
    path('sdk-events/', SDKEventListView.as_view(), name='sdk-events'),
]
