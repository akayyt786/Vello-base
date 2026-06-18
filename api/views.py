"""
DRF views: Auth, Projects, Data, Rules (Phase 1 scaffolds).
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.models import Project, ProjectMembership, UserProfile, RefreshTokenBlacklist
from data.models import Document
from core.permissions import IsProjectMember, IsProjectOwner, IsProjectEditorOrOwner
from rules.permissions import DocumentRules
from api.serializers import (
    ProjectSerializer,
    ProjectMembershipSerializer,
    UserSerializer,
    UserProfileSerializer,
    TokenRefreshResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    CustomClaimsSerializer,
    MeSerializer,
    DocumentSerializer,
)

logger = logging.getLogger(__name__)


class AuthViewSet(viewsets.ViewSet):
    """
    Authentication endpoints: register, login, refresh, logout, profile, custom claims.
    Phase 1 MVP: email/password authentication with JWT and custom claims.
    Mirrors Firebase Authentication API.
    """
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """
        POST /api/auth/register/
        Register a new user with email and password.

        Body:
            {
                "email": "user@example.com",
                "password": "secure_password_123",
                "password_confirm": "secure_password_123",
                "first_name": "John",
                "last_name": "Doe"
            }

        Returns:
            {
                "access": "<JWT access token>",
                "refresh": "<JWT refresh token>",
                "user": {
                    "id": 1,
                    "username": "user@example.com",
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            }

        Status: 201 Created on success, 400 Bad Request on validation error
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {'detail': 'Email already registered'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create user and profile atomically
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data.get('first_name', ''),
                last_name=serializer.validated_data.get('last_name', ''),
            )

            # Create user profile with custom claims support
            UserProfile.objects.create(
                user=user,
                sign_in_provider='password',
                email_verified=False,
                custom_claims={}
            )

        # Generate JWT tokens (with custom claims)
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        logger.info(f"User registered: {email}")

        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """
        POST /api/auth/login/
        Authenticate user with email and password, return JWT tokens.

        Body:
            {
                "email": "user@example.com",
                "password": "secure_password_123",
                "project_id": "uuid-optional"
            }

        Returns:
            {
                "access": "<JWT access token>",
                "refresh": "<JWT refresh token>",
                "user": { ... }
            }

        Status: 200 OK on success, 401 Unauthorized on invalid credentials
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        project_id = serializer.validated_data.get('project_id')

        # Authenticate user
        try:
            user = User.objects.get(email=email)
            if not user.check_password(password):
                logger.warning(f"Failed login attempt for {email}: invalid password")
                return Response(
                    {'detail': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            logger.warning(f"Failed login attempt: user {email} not found")
            return Response(
                {'detail': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Add project_id to token claims if provided
        if project_id:
            access_token['project_id'] = str(project_id)
            refresh['project_id'] = str(project_id)

        logger.info(f"User logged in: {email}")

        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def refresh(self, request):
        """
        POST /api/auth/refresh/
        Refresh an expired access token using a valid refresh token.

        Body:
            {
                "refresh": "<JWT refresh token>"
            }

        Returns:
            {
                "access": "<new JWT access token>",
                "refresh": "<new JWT refresh token (if ROTATE_REFRESH_TOKENS=True)>"
            }

        Status: 200 OK on success, 401 Unauthorized if refresh token is invalid/expired
        """
        serializer = RegisterSerializer(data=request.data)
        if 'refresh' not in request.data:
            return Response(
                {'detail': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use the custom TokenRefreshView's logic
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        refresh_serializer = TokenRefreshSerializer(data=request.data)
        refresh_serializer.is_valid(raise_exception=True)

        return Response(refresh_serializer.validated_data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        GET /api/auth/me/
        Get the current authenticated user's profile, including custom claims.
        Requires Bearer token in Authorization header.

        Returns:
            {
                "user": {
                    "id": 1,
                    "username": "user@example.com",
                    "email": "user@example.com",
                    "first_name": "John",
                    "last_name": "Doe"
                },
                "profile": {
                    "user": { ... },
                    "sign_in_provider": "password",
                    "email_verified": false,
                    "phone_number": "",
                    "avatar_url": "",
                    "bio": "",
                    "custom_claims": {}
                },
                "email_verified": false,
                "sign_in_provider": "password",
                "custom_claims": {}
            }

        Status: 200 OK, 401 Unauthorized if not authenticated
        """
        user = request.user
        serializer = MeSerializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_custom_claims(self, request):
        """
        POST /api/auth/set-custom-claims/
        Set custom claims for a user (admin/owner only).
        Custom claims are included in JWT tokens and max out at 1000 bytes.

        Body:
            {
                "user_id": 123,
                "claims": {
                    "admin": true,
                    "role": "editor",
                    "tier": "premium"
                }
            }

        Returns:
            {
                "user_id": 123,
                "custom_claims": { ... }
            }

        Status: 200 OK, 403 Forbidden if not admin, 404 Not Found if user doesn't exist
        """
        # Only admins/superusers can set custom claims
        if not request.user.is_staff:
            return Response(
                {'detail': 'Only administrators can set custom claims'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CustomClaimsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        claims = serializer.validated_data['claims']

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update custom claims in profile
        with transaction.atomic():
            profile = user.profile
            profile.custom_claims = claims
            profile.save()

        logger.info(f"Custom claims set for user {user_id}: {claims}")

        return Response({
            'user_id': user_id,
            'custom_claims': claims
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        POST /api/auth/logout/
        Logout the current user by blacklisting their refresh token.
        This prevents further token refreshes.

        Body:
            {
                "refresh": "<JWT refresh token>"
            }

        Returns: 204 No Content

        Status: 204 No Content on success, 400 Bad Request if refresh token not provided
        """
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token is required for logout'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Decode the refresh token to get the jti (JWT ID) and expiration
            refresh = RefreshToken(refresh_token)

            # Verify the token belongs to the authenticated user (prevent token hijacking)
            token_user_id = refresh.get('user_id')
            if str(token_user_id) != str(request.user.id):
                return Response(
                    {'detail': 'Refresh token does not belong to authenticated user'},
                    status=status.HTTP_403_FORBIDDEN
                )

            jti = refresh.get('jti')
            exp = refresh.get('exp')

            # Convert exp (Unix timestamp) to datetime for expires_at
            from datetime import datetime
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)

            # Blacklist the token
            RefreshTokenBlacklist.objects.create(
                jti=jti,
                user=request.user,
                expires_at=expires_at
            )

            logger.info(f"User logged out: {request.user.email}")
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return Response(
                {'detail': 'Invalid refresh token'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def anonymous_signin(self, request):
        """
        POST /api/auth/anonymous-signin/
        Create an anonymous user session. Useful for accumulating data before sign-up.
        Can be upgraded to a full account later via account linking.

        Returns:
            {
                "access": "<JWT access token>",
                "refresh": "<JWT refresh token>",
                "user": { ... }
            }

        Status: 201 Created
        """
        import uuid

        with transaction.atomic():
            # Create anonymous user with unique username and email
            anon_id = uuid.uuid4().hex[:12]
            user = User.objects.create_user(
                username=f"anon_{anon_id}",
                email=f"anon_{anon_id}@anonymous.local",
            )

            # Create profile with anonymous sign-in provider
            UserProfile.objects.create(
                user=user,
                sign_in_provider='anonymous',
                custom_claims={}
            )

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        logger.info(f"Anonymous user created: {user.username}")

        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    Projects: CRUD operations.
    Phase 1 MVP: basic project management.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter projects by current user's membership."""
        user = self.request.user
        return Project.objects.filter(
            members__user=user
        ).distinct()

    def perform_create(self, serializer):
        """Create project and add user as owner."""
        project = serializer.save()
        ProjectMembership.objects.create(
            project=project,
            user=self.request.user,
            role='owner'
        )

    @action(detail=True, methods=['post'])
    def invite_member(self, request, pk=None):
        """
        POST /api/v1/projects/{id}/invite_member/
        Body: { "email": "...", "role": "editor|viewer" }
        Invite a user to the project.
        """
        project = self.get_object()

        # Check permissions
        if not ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role='owner'
        ).exists():
            return Response(
                {'detail': 'Only project owner can invite members'},
                status=status.HTTP_403_FORBIDDEN
            )

        email = request.data.get('email')
        role = request.data.get('role', 'viewer')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create or update membership
        membership, created = ProjectMembership.objects.update_or_create(
            project=project,
            user=user,
            defaults={'role': role}
        )

        return Response(
            ProjectMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        GET /api/v1/projects/{id}/members/
        List all members of a project.
        """
        project = self.get_object()
        memberships = ProjectMembership.objects.filter(project=project)
        serializer = ProjectMembershipSerializer(memberships, many=True)
        return Response(serializer.data)


class ProjectMembershipViewSet(viewsets.ModelViewSet):
    """
    Project memberships: manage user roles within projects.
    Phase 1 MVP: basic CRUD.
    """
    queryset = ProjectMembership.objects.all()
    serializer_class = ProjectMembershipSerializer
    permission_classes = [IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        """Filter memberships by current user's projects."""
        user = self.request.user
        return ProjectMembership.objects.filter(
            project__members__user=user
        ).distinct()

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """
        POST /api/v1/memberships/{id}/remove_member/
        Remove a user from a project.
        """
        membership = self.get_object()

        # Check if requester is owner
        if not ProjectMembership.objects.filter(
            project=membership.project,
            user=request.user,
            role='owner'
        ).exists():
            return Response(
                {'detail': 'Only project owner can remove members'},
                status=status.HTTP_403_FORBIDDEN
            )

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DataViewSet(viewsets.ViewSet):
    """
    Data API: CRUD for documents/collections.
    Phase 1 MVP: scaffold only (no implementation).
    Full implementation in Phase 2 with:
    - Document model (with JSONB data + collections)
    - Query engine
    - Transaction support
    - Change listeners
    """
    permission_classes = [IsAuthenticated, IsProjectMember]

    @action(detail=False, methods=['get'])
    def collections(self, request):
        """
        GET /api/v1/data/collections/
        List all collections in the project.
        Returns: ["users", "posts", ...]
        """
        # Phase 2+
        return Response({'collections': []})

    @action(detail=False, methods=['post'])
    def query(self, request):
        """
        POST /api/v1/data/query/
        Execute a query (like Firestore).
        Body: { "collection": "users", "where": [...], "order_by": [...], "limit": 10 }
        Returns: { "documents": [...], "count": 5 }
        """
        # Phase 2+
        return Response({'documents': [], 'count': 0})

    @action(detail=False, methods=['post'])
    def write_batch(self, request):
        """
        POST /api/v1/data/write-batch/
        Batch write documents (like Firestore batch).
        Body: { "writes": [{"op": "set", "path": "...", "data": {...}}, ...] }
        Returns: 200 OK or error
        """
        # Phase 2+
        return Response({'status': 'ok'})


class RulesViewSet(viewsets.ViewSet):
    """
    Security Rules: read/update rules for collections.
    Phase 1 MVP: scaffold only.
    Full implementation in Phase 2 with:
    - Rules DSL compiler (Firebase rules → RLS policies + business logic)
    - Validation
    - Testing
    """
    permission_classes = [IsAuthenticated, IsProjectOwner]

    @action(detail=False, methods=['get'])
    def get_rules(self, request):
        """
        GET /api/v1/rules/
        Get current security rules for the project.
        Returns: { "rules": "..." }
        """
        # Phase 2+
        return Response({'rules': ''})

    @action(detail=False, methods=['post'])
    def update_rules(self, request):
        """
        POST /api/v1/rules/
        Update security rules for the project.
        Body: { "rules": "..." }
        Returns: 200 OK or validation error
        """
        # Phase 2+
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def test_rules(self, request):
        """
        POST /api/v1/rules/test/
        Test a rule against sample data.
        Body: { "rules": "...", "test_path": "...", "context": {...} }
        Returns: { "allowed": true/false, "reason": "..." }
        """
        # Phase 2+
        return Response({'allowed': True, 'reason': ''})


class DocumentViewSet(viewsets.ModelViewSet):
    """
    Documents: CRUD with Security Rules enforcement.
    Phase 1 MVP: basic document CRUD + rule evaluation on every request.

    GET /api/v1/projects/{project_id}/documents/ - list documents
    POST /api/v1/projects/{project_id}/documents/ - create document
    GET /api/v1/projects/{project_id}/documents/{id}/ - get document
    PATCH /api/v1/projects/{project_id}/documents/{id}/ - update document
    DELETE /api/v1/projects/{project_id}/documents/{id}/ - delete document
    """
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated, IsProjectMember, DocumentRules]
    filterset_fields = ['collection', 'owner']

    def get_queryset(self):
        """Filter documents by project membership."""
        user = self.request.user
        project_id = self.kwargs.get('project_id')

        # Verify user is member of project
        if project_id:
            if not ProjectMembership.objects.filter(
                project_id=project_id,
                user=user
            ).exists():
                return Document.objects.none()

            return Document.objects.filter(project_id=project_id)

        return Document.objects.none()

    def perform_create(self, serializer):
        """Create document in the project."""
        project_id = self.kwargs.get('project_id')
        serializer.save(project_id=project_id)

    def perform_update(self, serializer):
        """Update document."""
        serializer.save()
