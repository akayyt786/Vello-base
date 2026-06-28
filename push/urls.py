from rest_framework.routers import DefaultRouter
from . import views

app_name = 'push'

router = DefaultRouter()
router.register('tokens', views.DeviceTokenViewSet, basename='device-token')
router.register('topics', views.TopicViewSet, basename='topic')
router.register('notifications', views.PushNotificationViewSet, basename='push-notification')
router.register('campaigns', views.NotificationCampaignViewSet, basename='campaign')

urlpatterns = router.urls
