"""
App Check middleware.

Checks X-App-Check-Token header on protected endpoints.
Projects must have App Check enforcement enabled.
"""

import logging

logger = logging.getLogger(__name__)


class AppCheckMiddleware:
    """
    Optional middleware that validates App Check tokens.
    Only enforces on paths where project has enforcement enabled.
    Attach after AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Only check if project_id is in URL kwargs
        project_id = view_kwargs.get('project_id')
        if not project_id:
            return None

        # Get App-Check token from header
        token_header = request.headers.get('X-App-Check-Token')
        if not token_header:
            # Not enforced by default — attach status to request for views to check
            request.app_check_verified = False
            return None

        from .services import hash_token, validate_app_check_token
        from core.models import Project
        try:
            project = Project.objects.get(id=project_id, is_active=True)
        except Project.DoesNotExist:
            request.app_check_verified = False
            return None

        token_hash = hash_token(token_header)
        valid, _ = validate_app_check_token(project, token_hash)
        request.app_check_verified = valid
        return None
