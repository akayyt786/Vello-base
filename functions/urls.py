from django.urls import path
from . import views

app_name = 'functions'

urlpatterns = [
    path('', views.FunctionListView.as_view(), name='function-list'),
    path('<str:name>/', views.FunctionDetailView.as_view(), name='function-detail'),
    path('<str:name>/invoke/', views.FunctionInvokeView.as_view(), name='function-invoke'),
    path('<str:name>/logs/', views.FunctionLogsView.as_view(), name='function-logs'),
]
