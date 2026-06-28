from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'abtesting'

router = DefaultRouter()
router.register('experiments', views.ExperimentViewSet, basename='experiment')

urlpatterns = router.urls
