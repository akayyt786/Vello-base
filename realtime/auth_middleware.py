"""
ASGI middleware: authenticates WebSocket connections via the same JWT access
tokens the REST API uses (rest_framework_simplejwt + core.backends'
blacklist check), passed as a `?token=` query string param since a browser
WebSocket handshake cannot set a custom Authorization header.

Wraps (rather than replaces) Channels' session-based AuthMiddlewareStack:
if a valid token is present it wins; otherwise the connection falls back to
session auth, so a same-origin browser client with a Django session cookie
still works unauthenticated-by-token.
"""

from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _get_user_from_token(raw_token):
    from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
    from core.backends import CustomJWTAuthentication

    auth = CustomJWTAuthentication()
    try:
        validated_token = auth.get_validated_token(raw_token)
        return auth.get_user(validated_token)
    except (InvalidToken, AuthenticationFailed):
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        token = parse_qs(query_string).get('token', [None])[0]

        if token:
            scope = dict(scope)
            scope['user'] = await _get_user_from_token(token)

        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    # AuthMiddlewareStack (outer) sets a session-derived scope['user'] first;
    # JWTAuthMiddleware (inner) then overrides it only when a token param is
    # present and valid — order matters, reversing it would let the session
    # middleware clobber the JWT-derived user afterward.
    return AuthMiddlewareStack(JWTAuthMiddleware(inner))
