"""
WebSocket URL routing for realtime subscriptions.
Mounted under /ws/ in ASGI app.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/v1/projects/(?P<project_id>[^/]+)/listen/$', consumers.RealtimeConsumer.as_asgi()),
]
