"""URL configuration for app_check app."""

from django.urls import path
from . import views

app_name = 'app_check'

urlpatterns = [
    path('config/', views.AppCheckConfigListView.as_view(), name='config-list'),
    path('config/<uuid:pk>/', views.AppCheckConfigDetailView.as_view(), name='config-detail'),
    path('exchange/', views.ExchangeTokenView.as_view(), name='exchange'),
    path('verify/', views.VerifyTokenView.as_view(), name='verify'),
    path('tokens/', views.TokenListView.as_view(), name='token-list'),
    path('tokens/<uuid:pk>/revoke/', views.RevokeTokenView.as_view(), name='token-revoke'),
    path('debug-tokens/', views.DebugTokenListView.as_view(), name='debug-token-list'),
    path('debug-tokens/<uuid:pk>/', views.DebugTokenDeleteView.as_view(), name='debug-token-delete'),
]
