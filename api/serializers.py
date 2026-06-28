"""
DRF serializers for auth, project, and membership endpoints.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from core.models import Project, ProjectMembership, UserProfile
from data.models import Document, Collection


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['user', 'sign_in_provider', 'email_verified', 'phone_number', 'avatar_url', 'bio', 'custom_claims']


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model.

    NOTE: api_key is intentionally excluded from this serializer to avoid leaking
    the key in list and retrieve responses. Use the dedicated /api-key/ endpoint
    (owner-only) to retrieve it.
    """
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'slug', 'owner', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create project with current user as owner."""
        request = self.context.get('request')
        validated_data['owner'] = request.user
        return super().create(validated_data)


class ProjectMembershipSerializer(serializers.ModelSerializer):
    """Serializer for ProjectMembership model."""
    user = UserSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ['id', 'project', 'user', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Response serializer for token refresh and login endpoints."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
    project_id = serializers.CharField(required=False)


class LoginSerializer(serializers.Serializer):
    """Serializer for login endpoint."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    project_id = serializers.UUIDField(required=False)


class RegisterSerializer(serializers.Serializer):
    """Serializer for registration endpoint."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate password match and strength."""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match'})

        # Validate password against Django's validators
        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})

        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that includes custom claims in the JWT payload.
    Mirrors Firebase's custom claims functionality.
    """
    @classmethod
    def get_token(cls, user):
        """Override to add custom claims to token."""
        token = super().get_token(user)

        # Get user profile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        # Add standard claims
        token['email'] = user.email
        token['email_verified'] = profile.email_verified
        token['sign_in_provider'] = profile.sign_in_provider

        # Add custom claims from profile
        if profile.custom_claims:
            for key, value in profile.custom_claims.items():
                token[key] = value

        # Firebase-like structure
        token['firebase'] = {
            'sign_in_provider': profile.sign_in_provider,
            'identities': {},
        }

        return token


class RefreshTokenSerializer(TokenRefreshSerializer):
    """
    Custom refresh token serializer with token blacklist support.
    """
    def validate(self, attrs):
        """Validate and check token blacklist."""
        return super().validate(attrs)


class CustomClaimsSerializer(serializers.Serializer):
    """Serializer for setting custom claims on a user."""
    user_id = serializers.IntegerField()
    claims = serializers.JSONField(required=True)

    def validate_claims(self, value):
        """Validate custom claims size (Firebase max is 1000 bytes)."""
        import json
        claims_json = json.dumps(value)
        if len(claims_json.encode('utf-8')) > 1000:
            raise serializers.ValidationError(
                "Custom claims exceed maximum size of 1000 bytes"
            )
        return value


class MeSerializer(serializers.Serializer):
    """Response serializer for /api/auth/me/ endpoint."""
    user = serializers.SerializerMethodField()
    profile = UserProfileSerializer(read_only=True)
    email_verified = serializers.SerializerMethodField()
    sign_in_provider = serializers.SerializerMethodField()
    custom_claims = serializers.SerializerMethodField()

    def get_user(self, obj):
        return UserSerializer(obj).data

    def get_email_verified(self, obj):
        return obj.profile.email_verified if hasattr(obj, 'profile') else False

    def get_sign_in_provider(self, obj):
        return obj.profile.sign_in_provider if hasattr(obj, 'profile') else 'password'

    def get_custom_claims(self, obj):
        return obj.profile.custom_claims if hasattr(obj, 'profile') else {}


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model.

    'project' is always read_only — it is set from the URL parameter by the view,
    never from request body.
    """

    class Meta:
        model = Collection
        fields = ['id', 'project', 'name', 'path', 'schema', 'document_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'project', 'document_count', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model.

    Security constraints:
    - 'project' is read_only — set from URL parameter, never from request body.
    - 'created_by' and 'updated_by' are read_only — set server-side on create/update.
    - 'data' field is validated to be at most 1 MB (1,048,576 bytes) when serialized.
    """
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'project', 'collection_path', 'doc_id', 'data',
            'created_by', 'updated_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'project', 'created_by', 'updated_by', 'created_at', 'updated_at']

    def validate_data(self, value):
        """Enforce a 1 MB size limit on document content."""
        import json
        serialized = json.dumps(value)
        if len(serialized.encode('utf-8')) > 1_048_576:
            raise serializers.ValidationError(
                "Document data exceeds the maximum allowed size of 1 MB (1,048,576 bytes)."
            )
        return value

    def create(self, validated_data):
        """Create document with current user as creator."""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update document and record the updater."""
        request = self.context.get('request')
        validated_data['updated_by'] = request.user
        return super().update(instance, validated_data)
