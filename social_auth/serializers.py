from rest_framework import serializers
from .models import SocialAccount


class GoogleSignInSerializer(serializers.Serializer):
    id_token = serializers.CharField(help_text="Google ID token from client SDK")


class GitHubSignInSerializer(serializers.Serializer):
    access_token = serializers.CharField(help_text="GitHub OAuth access token")


class AppleSignInSerializer(serializers.Serializer):
    id_token = serializers.CharField(help_text="Apple ID token")


class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ["id", "provider", "provider_uid", "email", "name", "avatar_url", "created_at"]
        read_only_fields = ["id", "provider", "provider_uid", "created_at"]
