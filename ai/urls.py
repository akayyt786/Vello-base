from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AIProviderConfigViewSet, AIUsageView, ChatCompletionView, EmbeddingView

app_name = "ai"

router = DefaultRouter()
router.register(r'providers', AIProviderConfigViewSet, basename='ai-providers')

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', ChatCompletionView.as_view(), name='ai-chat'),
    path('embeddings/', EmbeddingView.as_view(), name='ai-embeddings'),
    path('usage/', AIUsageView.as_view(), name='ai-usage'),
]
