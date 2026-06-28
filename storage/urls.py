from django.urls import path
from . import views

app_name = 'storage'

urlpatterns = [
    path('upload-url/', views.UploadUrlView.as_view(), name='upload-url'),
    path('confirm/', views.ConfirmUploadView.as_view(), name='confirm'),
    path('files/', views.FileListView.as_view(), name='file-list'),
    path('files/<path:path>/', views.FileDetailView.as_view(), name='file-detail'),
]
