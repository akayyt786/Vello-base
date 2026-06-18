"""
Custom JWT authentication backend.
Extends rest_framework_simplejwt to verify tokens and load custom claims.
"""

import logging
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from jwt import decode as jwt_decode
from django.contrib.auth.models import User
from core.models import RefreshTokenBlacklist

logger = logging.getLogger(__name__)


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that:
    1. Verifies JWT signature and claims
    2. Checks token blacklist (for revoked tokens)
    3. Loads user and attaches custom claims to request
    4. Raises 401 if token is invalid/expired/blacklisted
    """

    def authenticate(self, request):
        """
        Authenticate request using JWT token.
        Returns (user, validated_token) or None if no token.
        """
        # Let parent extract and validate token
        try:
            result = super().authenticate(request)
            if result is None:
                return None

            user, validated_token = result

            # Check if token has been blacklisted (logout)
            jti = validated_token.get('jti')
            if jti and RefreshTokenBlacklist.objects.filter(jti=jti).exists():
                logger.warning(f"Blacklisted token used by {user.email}")
                raise InvalidToken("Token has been revoked")

            # Attach decoded token claims to request for later use
            request.token_claims = validated_token

            return (user, validated_token)

        except (InvalidToken, AuthenticationFailed) as e:
            logger.debug(f"JWT authentication failed: {e}")
            raise

    def get_validated_token(self, raw_token):
        """
        Validate token signature and structure.
        Override parent to add blacklist check.
        """
        validated_token = super().get_validated_token(raw_token)

        # Check blacklist
        jti = validated_token.get('jti')
        if jti and RefreshTokenBlacklist.objects.filter(jti=jti).exists():
            raise InvalidToken("Token has been revoked")

        return validated_token
