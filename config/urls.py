from rest_framework.routers import DefaultRouter
from django.urls import path
from . import views

app_name = 'remoteconfig'

router = DefaultRouter()
router.register('parameters', views.RemoteConfigViewSet, basename='remote-config')

urlpatterns = [
    # Nested: conditions under a specific config parameter
    path(
        'parameters/<uuid:config_id>/conditions/',
        views.ConfigConditionViewSet.as_view({
            'get': 'list',
            'post': 'create',
        }),
        name='config-condition-list',
    ),
    path(
        'parameters/<uuid:config_id>/conditions/<uuid:pk>/',
        views.ConfigConditionViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='config-condition-detail',
    ),
] + router.urls
