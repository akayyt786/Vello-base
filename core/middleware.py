"""
Multi-tenant middleware: extracts project_id and user_id from JWT, sets context for RLS.
"""

import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Thread-local context vars for multi-tenant isolation
current_project_id = ContextVar('project_id', default=None)
current_user_id = ContextVar('user_id', default=None)


class MultiTenantMiddleware(MiddlewareMixin):
    """
    Extracts JWT payload and sets app.current_project / app.current_user context vars.
    These are used by:
    1. Custom permission classes to validate project membership
    2. RLS policies (via Postgres SET app.current_project = '...')
    3. Query filters (to auto-filter by project)
    """

    def process_request(self, request):
        """Extract JWT and set context vars."""
        # Skip for unauthenticated paths (login, registration, etc.)
        if self._is_public_path(request):
            return None

        # Extract JWT from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        try:
            # Decode JWT without verifying signature (we trust DRF to verify)
            # In production, always verify the signature
            from rest_framework_simplejwt.tokens import Token
            from rest_framework_simplejwt.settings import api_settings

            # Decode and validate
            jwt_auth = JWTAuthentication()
            # This will raise an exception if token is invalid
            # Note: JWTAuthentication.authenticate() expects (request, token)
            # We'll manually validate here for simplicity

            from jwt import decode
            from django.conf import settings
            import jwt as pyjwt

            payload = pyjwt.decode(
                token,
                settings.SIMPLE_JWT.get('SIGNING_KEY', settings.SECRET_KEY),
                algorithms=[settings.SIMPLE_JWT.get('ALGORITHM', 'HS256')]
            )

            user_id = payload.get('user_id')
            project_id = payload.get('project_id')  # Custom claim added by auth view

            if user_id:
                current_user_id.set(user_id)
            if project_id:
                current_project_id.set(project_id)

            # Attach to request for easy access in views/serializers
            request.tenant_project_id = project_id
            request.tenant_user_id = user_id

        except Exception as e:
            logger.debug(f"JWT decode error: {e}")
            # Let DRF's JWTAuthentication handle the error properly
            return None

        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        After DRF authentication, validate project membership (if required).
        """
        if request.user and request.user.is_authenticated:
            project_id = getattr(request, 'tenant_project_id', None)
            if project_id:
                # Validate user is a member of this project
                # This can be done via a permission class instead (see core/permissions.py)
                pass
        return None

    @staticmethod
    def _is_public_path(request):
        """Paths that don't require JWT."""
        public_paths = [
            '/api/auth/',
            '/api/v1/auth/login',
            '/api/v1/auth/register',
            '/api/v1/auth/token',
            '/api/v1/auth/token/refresh',
            '/api/v1/auth/anonymous-signin',
            '/api/schema/',
            '/api/docs/',
            '/api/redoc/',
            '/admin/',
        ]
        for path in public_paths:
            if request.path.startswith(path):
                return True
        return False
