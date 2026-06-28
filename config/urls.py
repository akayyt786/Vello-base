from rest_framework.routers import DefaultRouter
from django.urls import path
from . import views

app_name = 'remoteconfig'

router = DefaultRouter()
router.register('parameters', views.RemoteConfigViewSet, basename='remote-config')
router.register('experiments', views.ExperimentViewSet, basename='experiment')

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

    # Nested: variants under a specific experiment
    path(
        'experiments/<uuid:experiment_id>/variants/',
        views.ExperimentVariantViewSet.as_view({
            'get': 'list',
            'post': 'create',
        }),
        name='experiment-variant-list',
    ),
    path(
        'experiments/<uuid:experiment_id>/variants/<uuid:pk>/',
        views.ExperimentVariantViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='experiment-variant-detail',
    ),
] + router.urls
