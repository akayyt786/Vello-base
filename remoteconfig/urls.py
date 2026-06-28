from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RemoteConfigViewSet, RemoteConfigFetchView

app_name = 'remoteconfig'

router = DefaultRouter()
router.register(r'params', RemoteConfigViewSet, basename='remote-config-params')

urlpatterns = [
    path('', include(router.urls)),
    path('fetch/', RemoteConfigFetchView.as_view(), name='fetch'),
]
