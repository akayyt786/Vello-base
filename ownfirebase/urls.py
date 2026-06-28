"""
URL configuration for Own Firebase (ownfirebase) project.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from enhanced_auth.views import IssueCustomTokenView

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # DRF auth endpoints
    path('api/auth/', include('rest_framework.urls')),

    # API v1
    path('api/v1/', include('api.urls')),

    # Data API (Firestore-like)
    path('api/', include('data.urls')),

    # Cloud Storage API
    path('api/projects/<uuid:project_id>/storage/', include('storage.urls', namespace='storage')),

    # Cloud Functions API
    path('api/projects/<uuid:project_id>/functions/', include('functions.urls', namespace='functions')),

    # Push Notifications API
    path('api/projects/<uuid:project_id>/push/', include('push.urls', namespace='push')),

    # Analytics API
    path('api/projects/<uuid:project_id>/analytics/', include('analytics.urls', namespace='analytics')),

    # Remote Config + A/B Testing API
    path('api/projects/<uuid:project_id>/config/', include('config.urls', namespace='remoteconfig')),

    # Crashlytics + Performance Monitoring API
    path('api/projects/<uuid:project_id>/crashlytics/', include('crashlytics.urls', namespace='crashlytics')),

    # Enhanced Auth (user-level: phone, MFA, magic-link)
    path('api/v1/auth/', include('enhanced_auth.urls', namespace='enhanced_auth')),

    # Enhanced Auth (project-scoped: custom token issuance)
    path('api/projects/<uuid:project_id>/auth/custom-token/', IssueCustomTokenView.as_view(), name='issue-custom-token'),

    # App Check API
    path('api/projects/<uuid:project_id>/app-check/', include('app_check.urls', namespace='app_check')),

    # Social Auth (Google, GitHub sign-in + linked accounts)
    path('api/v1/auth/social/', include('social_auth.urls', namespace='social_auth')),

    # A/B Testing API
    path('api/projects/<uuid:project_id>/abtesting/', include('abtesting.urls', namespace='abtesting')),
]

if settings.DEBUG:
    urlpatterns += [
        # API schema (OpenAPI / Swagger) — debug/dev only
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
        path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    ]
