from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VectorCollectionViewSet

app_name = "rag"

router = DefaultRouter()
router.register(r'collections', VectorCollectionViewSet, basename='rag-collections')

urlpatterns = [path('', include(router.urls))]
