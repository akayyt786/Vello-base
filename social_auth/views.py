import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount
from .serializers import GoogleSignInSerializer, GitHubSignInSerializer, SocialAccountSerializer
from .services import verify_google_id_token, verify_github_access_token

User = get_user_model()
logger = logging.getLogger(__name__)


def _jwt_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user_id": str(user.id),
        "email": user.email,
        "is_new": getattr(user, "_is_new", False),
    }


def _get_or_create_user_for_social(provider_data, provider):
    """
    Find existing SocialAccount -> return linked user.
    Or find user by email -> link SocialAccount.
    Or create new user -> create SocialAccount.
    Returns (user, is_new).
    """
    # 1. Existing social account
    try:
        sa = SocialAccount.objects.select_related("user").get(
            provider=provider, provider_uid=provider_data["provider_uid"]
        )
        # Update fields
        sa.name = provider_data.get("name", sa.name)
        sa.avatar_url = provider_data.get("avatar_url", sa.avatar_url)
        sa.raw_data = provider_data.get("raw_data", sa.raw_data)
        sa.save(update_fields=["name", "avatar_url", "raw_data"])
        return sa.user, False
    except SocialAccount.DoesNotExist:
        pass

    email = provider_data.get("email", "")
    with transaction.atomic():
        # 2. Existing user by email -> link (only if provider verified the email).
        # Unverified emails must NOT link to existing accounts — prevents account takeover.
        if email and provider_data.get("email_verified"):
            user = User.objects.filter(email=email).first()
            if user:
                SocialAccount.objects.create(
                    user=user,
                    provider=provider,
                    provider_uid=provider_data["provider_uid"],
                    email=email,
                    name=provider_data.get("name", ""),
                    avatar_url=provider_data.get("avatar_url", ""),
                    raw_data=provider_data.get("raw_data", {}),
                )
                return user, False

        # 3. Create new user
        username = provider + "_" + provider_data["provider_uid"]
        if len(username) > 150:
            username = username[:150]
        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,  # unusable password
        )
        if provider_data.get("name"):
            parts = provider_data["name"].split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
            user.save(update_fields=["first_name", "last_name"])
        SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_uid=provider_data["provider_uid"],
            email=email,
            name=provider_data.get("name", ""),
            avatar_url=provider_data.get("avatar_url", ""),
            raw_data=provider_data.get("raw_data", {}),
        )
        return user, True


class GoogleSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = GoogleSignInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        provider_data, error = verify_google_id_token(ser.validated_data["id_token"])
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        user, is_new = _get_or_create_user_for_social(provider_data, "google")
        user._is_new = is_new
        resp = _jwt_response(user)
        return Response(resp, status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK)


class GitHubSignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = GitHubSignInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        provider_data, error = verify_github_access_token(ser.validated_data["access_token"])
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        user, is_new = _get_or_create_user_for_social(provider_data, "github")
        user._is_new = is_new
        resp = _jwt_response(user)
        return Response(resp, status=status.HTTP_201_CREATED if is_new else status.HTTP_200_OK)


class LinkedAccountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = SocialAccount.objects.filter(user=request.user)
        return Response(SocialAccountSerializer(accounts, many=True).data)

    def delete(self, request, pk):
        account = SocialAccount.objects.filter(pk=pk, user=request.user).first()
        if not account:
            return Response(
                {"error": "Social account not found."}, status=status.HTTP_404_NOT_FOUND
            )
        # Prevent unlinking last auth method if user has no password
        if not request.user.has_usable_password():
            remaining = SocialAccount.objects.filter(user=request.user).count()
            if remaining <= 1:
                return Response(
                    {"error": "Cannot unlink last authentication method. Set a password first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        account.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
