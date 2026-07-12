"""
ASGI config for Own Firebase (ownfirebase) project.
WebSocket & realtime via Django Channels.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ownfirebase.settings')
django_asgi_app = get_asgi_application()

from realtime.routing import websocket_urlpatterns  # noqa: E402 — after Django setup
from realtime.auth_middleware import JWTAuthMiddlewareStack  # noqa: E402 — after Django setup

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
