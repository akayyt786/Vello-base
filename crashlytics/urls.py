from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'crashlytics'

router = DefaultRouter()
router.register('groups', views.CrashGroupViewSet, basename='crash-group')
router.register('reports', views.CrashReportViewSet, basename='crash-report')
router.register('traces', views.PerformanceTraceViewSet, basename='perf-trace')
router.register('network', views.NetworkRequestViewSet, basename='network-request')

urlpatterns = router.urls + [
    path('summary/', views.CrashSummaryView.as_view(), name='crash-summary'),
]
