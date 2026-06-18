"""
ASGI config for Own Firebase (ownfirebase) project.
WebSocket & realtime via Django Channels.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ownfirebase.settings')
django_asgi_app = get_asgi_application()

# Channels routing (WebSocket consumers go here; Phase 1 MVP stub)
from django.urls import path

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            [
                # WebSocket routes stub (Phase 2+)
            ]
        )
    ),
})
