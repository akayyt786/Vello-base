"""
URL configuration for API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    AuthViewSet,
    ProjectViewSet,
    ProjectMembershipViewSet,
    DataViewSet,
    RulesViewSet,
    DocumentViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'memberships', ProjectMembershipViewSet, basename='membership')
router.register(r'documents', DocumentViewSet, basename='document')

# Auth endpoints (singleton views)
auth_urls = [
    path('auth/register/', AuthViewSet.as_view({'post': 'register'}), name='auth-register'),
    path('auth/login/', AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
    path('auth/refresh/', AuthViewSet.as_view({'post': 'refresh'}), name='auth-refresh'),
    path('auth/me/', AuthViewSet.as_view({'get': 'me'}), name='auth-me'),
    path('auth/set-custom-claims/', AuthViewSet.as_view({'post': 'set_custom_claims'}), name='auth-set-claims'),
    path('auth/logout/', AuthViewSet.as_view({'post': 'logout'}), name='auth-logout'),
    path('auth/anonymous-signin/', AuthViewSet.as_view({'post': 'anonymous_signin'}), name='auth-anonymous'),
]

data_urls = [
    path('data/collections/', DataViewSet.as_view({'get': 'collections'}), name='data-collections'),
    path('data/query/', DataViewSet.as_view({'post': 'query'}), name='data-query'),
    path('data/write-batch/', DataViewSet.as_view({'post': 'write_batch'}), name='data-write-batch'),
]

rules_urls = [
    path('rules/', RulesViewSet.as_view({'get': 'get_rules', 'post': 'update_rules'}), name='rules'),
    path('rules/test/', RulesViewSet.as_view({'post': 'test_rules'}), name='rules-test'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('', include(auth_urls)),
    path('', include(data_urls)),
    path('', include(rules_urls)),
]
