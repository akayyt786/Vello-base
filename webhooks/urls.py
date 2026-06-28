from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WebhookEndpointViewSet

app_name = 'webhooks'

router = DefaultRouter()
router.register(r'endpoints', WebhookEndpointViewSet, basename='webhook-endpoints')

urlpatterns = [path('', include(router.urls))]
