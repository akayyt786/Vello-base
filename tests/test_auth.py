"""
Tests for authentication endpoints: register, login, refresh, logout, me, custom claims.
Tests JWT token generation, custom claims, and token blacklist.
"""

import pytest
import json
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from core.models import UserProfile, RefreshTokenBlacklist


@pytest.mark.django_db
class TestAuthViewSet:
    """Tests for auth endpoints."""

    def test_register_success(self, api_client):
        """Test successful user registration."""
        url = reverse('auth-register')
        data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user']['email'] == 'newuser@example.com'

    def test_register_password_mismatch(self, api_client):
        """Test registration fails when passwords don't match."""
        url = reverse('auth-register')
        data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'password_confirm': 'DifferentPass123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, test_user):
        """Test registration fails for duplicate email."""
        url = reverse('auth-register')
        data = {
            'email': test_user.email,
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_success(self, api_client, test_user):
        """Test successful login."""
        url = reverse('auth-login')
        data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user']['id'] == test_user.id

    def test_login_invalid_password(self, api_client, test_user):
        """Test login fails with invalid password."""
        url = reverse('auth-login')
        data = {
            'email': test_user.email,
            'password': 'wrongpassword'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login fails for nonexistent user."""
        url = reverse('auth-login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'password'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_anonymous_signin(self, api_client):
        """Test anonymous sign-in creates anonymous user."""
        url = reverse('auth-anonymous')
        response = api_client.post(url)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user'] is not None

    def test_me_authenticated(self, api_client, test_user):
        """Test /api/auth/me/ returns current user profile."""
        # Login to get token
        login_url = reverse('auth-login')
        login_data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data['access']

        # Get current user
        url = reverse('auth-me')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['email'] == test_user.email
        assert 'profile' in response.data
        assert response.data['email_verified'] is True
        assert response.data['sign_in_provider'] == 'password'

    def test_me_unauthenticated(self, api_client):
        """Test /api/auth/me/ returns 401 without token."""
        url = reverse('auth-me')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, test_user):
        """Test token refresh endpoint."""
        # Login to get tokens
        login_url = reverse('auth-login')
        login_data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data)
        refresh_token = login_response.data['refresh']

        # Refresh the token
        url = reverse('auth-refresh')
        data = {'refresh': refresh_token}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_logout_blacklists_token(self, api_client, test_user):
        """Test logout blacklists refresh token."""
        # Login to get tokens
        login_url = reverse('auth-login')
        login_data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        # Logout
        logout_url = reverse('auth-logout')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_data = {'refresh': refresh_token}
        logout_response = api_client.post(logout_url, logout_data)

        assert logout_response.status_code == status.HTTP_204_NO_CONTENT

        # Verify token is blacklisted
        from jwt import decode as jwt_decode
        from django.conf import settings
        decoded = jwt_decode(
            refresh_token,
            settings.SIMPLE_JWT['SIGNING_KEY'],
            algorithms=['HS256']
        )
        jti = decoded['jti']
        assert RefreshTokenBlacklist.objects.filter(jti=jti).exists()

    def test_set_custom_claims_admin(self, api_client, admin_user):
        """Test setting custom claims (admin only)."""
        # Create a regular user
        user = User.objects.create_user(
            username='regularuser@example.com',
            email='regularuser@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=user)

        # Login as admin
        login_url = reverse('auth-login')
        login_data = {
            'email': admin_user.email,
            'password': 'adminpass123'
        }
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data['access']

        # Set custom claims
        url = reverse('auth-set-claims')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        data = {
            'user_id': user.id,
            'claims': {
                'admin': False,
                'role': 'editor',
                'tier': 'premium'
            }
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user_id'] == user.id
        assert response.data['custom_claims']['role'] == 'editor'

        # Verify claims were saved
        user.profile.refresh_from_db()
        assert user.profile.custom_claims['role'] == 'editor'

    def test_set_custom_claims_non_admin(self, api_client, test_user):
        """Test setting custom claims fails for non-admin."""
        # Login as regular user
        login_url = reverse('auth-login')
        login_data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data['access']

        # Try to set custom claims
        url = reverse('auth-set-claims')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        data = {
            'user_id': test_user.id,
            'claims': {'admin': True}
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_custom_claims_in_token(self, api_client, admin_user, test_user):
        """Test custom claims appear in JWT token."""
        # Set custom claims on user
        login_url = reverse('auth-login')
        login_data = {
            'email': admin_user.email,
            'password': 'adminpass123'
        }
        login_response = api_client.post(login_url, login_data)
        admin_token = login_response.data['access']

        # Set claims for test_user
        url = reverse('auth-set-claims')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        data = {
            'user_id': test_user.id,
            'claims': {'role': 'editor'}
        }
        api_client.post(url, data, format='json')

        # Login as test_user and check token
        login_data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data['access']

        # Decode and verify claims
        from jwt import decode as jwt_decode
        from django.conf import settings
        decoded = jwt_decode(
            access_token,
            settings.SIMPLE_JWT['SIGNING_KEY'],
            algorithms=['HS256']
        )
        assert decoded.get('role') == 'editor'
        assert decoded.get('email') == test_user.email
        assert decoded.get('email_verified') is True

    def test_register_password_validation(self, api_client):
        """Test registration enforces password requirements."""
        url = reverse('auth-register')

        # Test weak password (too short, fails validation)
        data = {
            'email': 'newuser@example.com',
            'password': '123',  # Too short
            'password_confirm': '123'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_refresh_token_with_custom_claims(self, api_client, test_user, admin_user):
        """Test that refreshed token includes custom claims."""
        # Set custom claims on test_user via admin
        login_url = reverse('auth-login')
        admin_login_data = {
            'email': admin_user.email,
            'password': 'adminpass123'
        }
        admin_login_response = api_client.post(login_url, admin_login_data)
        admin_token = admin_login_response.data['access']

        # Set custom claims
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        claims_url = reverse('auth-set-claims')
        claims_data = {
            'user_id': test_user.id,
            'claims': {'role': 'editor', 'tier': 'pro'}
        }
        api_client.post(claims_url, claims_data, format='json')

        # Login as test_user and get tokens
        api_client.credentials()
        user_login_data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        user_login_response = api_client.post(login_url, user_login_data)
        refresh_token = user_login_response.data['refresh']

        # Refresh token
        refresh_url = reverse('auth-refresh')
        refresh_data = {'refresh': refresh_token}
        refresh_response = api_client.post(refresh_url, refresh_data)

        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access' in refresh_response.data

        # Decode new access token
        from jwt import decode as jwt_decode
        from django.conf import settings
        new_token = refresh_response.data['access']
        decoded = jwt_decode(
            new_token,
            settings.SIMPLE_JWT['SIGNING_KEY'],
            algorithms=['HS256']
        )
        assert decoded.get('role') == 'editor'
        assert decoded.get('tier') == 'pro'

    def test_logout_prevents_token_reuse(self, api_client, test_user):
        """Test that refresh token cannot be reused after logout."""
        # Login to get tokens
        login_url = reverse('auth-login')
        login_data = {
            'email': test_user.email,
            'password': 'testpass123'
        }
        login_response = api_client.post(login_url, login_data)
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        # Logout
        logout_url = reverse('auth-logout')
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_data = {'refresh': refresh_token}
        logout_response = api_client.post(logout_url, logout_data)
        assert logout_response.status_code == status.HTTP_204_NO_CONTENT

        # Try to refresh with blacklisted token
        api_client.credentials()
        refresh_url = reverse('auth-refresh')
        refresh_data = {'refresh': refresh_token}
        refresh_response = api_client.post(refresh_url, refresh_data)

        # Should fail (token is blacklisted)
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
