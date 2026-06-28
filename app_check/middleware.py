"""
App Check middleware.

Checks X-App-Check-Token header on protected endpoints.
Projects must have App Check enforcement enabled in settings.
"""

import logging

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Paths that bypass App Check validation entirely.
EXEMPT_PATHS = [
    '/health/',
    '/api/v1/auth/login/',
    '/api/v1/auth/register/',
    '/api/v1/auth/magic-link/send/',
]


class AppCheckMiddleware:
    """
    Optional middleware that validates App Check tokens.

    Behaviour controlled by settings.APP_CHECK_ENFORCEMENT (default False):

      True  — missing or invalid tokens return a 401 JSON response on
              non-exempt paths that carry a project_id URL kwarg.
      False — token presence/validity is still checked and written to
              request.app_check_verified so views can inspect it, but
              requests are never blocked.

    Exempt paths skip all App Check logic regardless of enforcement:
        /health/
        /api/v1/auth/login/
        /api/v1/auth/register/
        /api/v1/auth/magic-link/send/

    On DB or unexpected errors during validation the middleware logs a
    WARNING and fails open (allows the request) to prevent service
    outages from transient DB blips.

    Token validity relies on AppCheckToken.is_valid(), which checks both
    token expiry (expires_at) and the is_revoked flag.

    Attach after AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Cache at startup; override_settings in tests re-instantiates middleware.
        self.enforcement = getattr(settings, 'APP_CHECK_ENFORCEMENT', False)

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # --- 1. Exempt paths bypass all App Check logic ---
        if request.path in EXEMPT_PATHS:
            return None

        # --- 2. Only apply to project-scoped endpoints ---
        project_id = view_kwargs.get('project_id')
        if not project_id:
            return None

        # --- 3. Require token header when enforcement is on ---
        token_header = request.headers.get('X-App-Check-Token')
        if not token_header:
            request.app_check_verified = False
            if self.enforcement:
                logger.warning(
                    'AppCheckMiddleware: missing token on project=%s path=%s',
                    project_id,
                    request.path,
                )
                return JsonResponse(
                    {
                        'error': 'App Check token is required.',
                        'code': 'app_check_required',
                    },
                    status=401,
                )
            return None

        # --- 4. Resolve project (fail open on DB errors) ---
        from core.models import Project
        try:
            project = Project.objects.get(id=project_id, is_active=True)
        except Project.DoesNotExist:
            # No matching project — nothing to enforce against.
            request.app_check_verified = False
            return None
        except Exception as exc:
            logger.warning(
                'AppCheckMiddleware: DB error fetching project=%s — failing open. %s',
                project_id,
                exc,
            )
            request.app_check_verified = False
            return None

        # --- 5. Validate token (checks expires_at and is_revoked via is_valid()) ---
        from .services import hash_token, validate_app_check_token
        try:
            token_hash = hash_token(token_header)
            valid, reason = validate_app_check_token(project, token_hash)
        except Exception as exc:
            logger.warning(
                'AppCheckMiddleware: token validation error for project=%s — failing open. %s',
                project_id,
                exc,
            )
            request.app_check_verified = False
            return None

        request.app_check_verified = valid

        # --- 6. Block only when enforcement is active and token is bad ---
        if not valid and self.enforcement:
            logger.warning(
                'AppCheckMiddleware: invalid token rejected for project=%s path=%s reason=%s',
                project_id,
                request.path,
                reason,
            )
            return JsonResponse(
                {
                    'error': 'App Check token is invalid or expired.',
                    'code': 'app_check_invalid',
                    'detail': reason,
                },
                status=401,
            )

        return None
