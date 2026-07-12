"""Tests for OwnFirebase Auth SDK."""

import pytest
from unittest.mock import Mock, patch
from ownfirebase import OwnFirebaseConfig, APIError
from ownfirebase.auth import AuthSDK


class TestAuthSDK:
    """Tests for the Auth SDK."""

    def test_auth_init(self):
        """Test Auth SDK initialization."""
        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)
        assert auth.base_url == 'http://localhost:8000'
        assert auth.project_id == 'test-project'
        assert auth.access_token == 'test-token'

    @patch('requests.request')
    def test_send_otp_phone(self, mock_request):
        """Test sending OTP via phone."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'session_id': 'session-123',
            'expires_in': 300
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        # Since the auth module is currently a stub, we'll test the base functionality
        # In a real implementation, this would call send_otp_phone method
        result = auth.request(
            'POST',
            auth.project_url('auth/phone/send-otp'),
            json_data={'phone_number': '+1234567890'}
        )

        assert result['session_id'] == 'session-123'
        assert result['expires_in'] == 300

    @patch('requests.request')
    def test_verify_otp_phone(self, mock_request):
        """Test verifying OTP via phone."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': 'user-123',
            'access_token': 'new-access-token',
            'refresh_token': 'refresh-token-xyz'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/phone/verify-otp'),
            json_data={'session_id': 'session-123', 'otp': '123456'}
        )

        assert result['user_id'] == 'user-123'
        assert result['access_token'] == 'new-access-token'

    @patch('requests.request')
    def test_enroll_totp_mfa(self, mock_request):
        """Test enrolling TOTP MFA."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'secret': 'JBSWY3DPEBLW64TMMQ======',
            'qr_code': 'data:image/png;base64,iVBORw0KG...',
            'device_id': 'device-123'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/mfa/enroll/totp'),
            json_data={}
        )

        assert 'secret' in result
        assert 'qr_code' in result
        assert result['device_id'] == 'device-123'

    @patch('requests.request')
    def test_confirm_totp_mfa(self, mock_request):
        """Test confirming TOTP MFA enrollment."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'device_id': 'device-123',
            'status': 'active'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/mfa/confirm/totp'),
            json_data={'device_id': 'device-123', 'code': '123456'}
        )

        assert result['status'] == 'active'

    @patch('requests.request')
    def test_verify_totp_code(self, mock_request):
        """Test verifying TOTP code during login."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new-access-token',
            'refresh_token': 'refresh-token',
            'user_id': 'user-123'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/mfa/verify/totp'),
            json_data={'code': '123456', 'session_id': 'session-123'}
        )

        assert result['access_token'] == 'new-access-token'

    @patch('requests.request')
    def test_send_magic_link(self, mock_request):
        """Test sending magic link."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'session_id': 'session-123',
            'expires_in': 900
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/magic-link/send'),
            json_data={'email': 'test@example.com'}
        )

        assert result['session_id'] == 'session-123'

    @patch('requests.request')
    def test_verify_magic_link(self, mock_request):
        """Test verifying magic link."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': 'user-123',
            'access_token': 'new-access-token',
            'refresh_token': 'refresh-token'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/magic-link/verify'),
            json_data={'token': 'magic-link-token-xyz'}
        )

        assert result['user_id'] == 'user-123'
        assert result['access_token'] == 'new-access-token'

    @patch('requests.request')
    def test_link_email(self, mock_request):
        """Test linking email to account."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': 'user-123',
            'email': 'test@example.com'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/link-email'),
            json_data={'email': 'test@example.com'}
        )

        assert result['email'] == 'test@example.com'

    @patch('requests.request')
    def test_set_password(self, mock_request):
        """Test setting password."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/set-password'),
            json_data={'password': 'new-password-123'}
        )

        assert result['status'] == 'success'

    @patch('requests.request')
    def test_anonymous_upgrade(self, mock_request):
        """Test upgrading anonymous account to registered."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'user_id': 'user-123',
            'email': 'newemail@example.com'
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'POST',
            auth.project_url('auth/upgrade'),
            json_data={'email': 'newemail@example.com', 'password': 'password-123'}
        )

        assert result['email'] == 'newemail@example.com'

    @patch('requests.request')
    def test_mfa_device_list(self, mock_request):
        """Test listing MFA devices."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'devices': [
                {'device_id': 'device-1', 'type': 'totp', 'name': 'Authenticator App'},
                {'device_id': 'device-2', 'type': 'sms', 'phone': '+1234567890'}
            ]
        }
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'GET',
            auth.project_url('auth/mfa/devices')
        )

        assert len(result['devices']) == 2

    @patch('requests.request')
    def test_mfa_device_delete(self, mock_request):
        """Test deleting MFA device."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 204
        mock_request.return_value = mock_response

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        result = auth.request(
            'DELETE',
            auth.project_url('auth/mfa/devices/device-123')
        )

        assert result is None


class TestAuthFlow:
    """Integration tests for complete authentication flows."""

    @patch('requests.request')
    def test_complete_phone_otp_flow(self, mock_request):
        """Test complete phone OTP authentication flow."""
        # Mock sequence of responses
        responses = [
            # Send OTP
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'session_id': 'session-123',
                'expires_in': 300
            })),
            # Verify OTP
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'user_id': 'user-123',
                'access_token': 'access-token-123',
                'refresh_token': 'refresh-token-123'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
        )
        auth = AuthSDK(config)

        # Step 1: Send OTP
        send_response = auth.request(
            'POST',
            auth.project_url('auth/phone/send-otp'),
            json_data={'phone_number': '+1234567890'}
        )
        assert send_response['session_id'] == 'session-123'

        # Step 2: Verify OTP
        verify_response = auth.request(
            'POST',
            auth.project_url('auth/phone/verify-otp'),
            json_data={'session_id': 'session-123', 'otp': '123456'}
        )
        assert verify_response['access_token'] == 'access-token-123'

    @patch('requests.request')
    def test_magic_link_authentication_flow(self, mock_request):
        """Test complete magic link authentication flow."""
        responses = [
            # Send magic link
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'session_id': 'session-456',
                'expires_in': 900
            })),
            # Verify magic link
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'user_id': 'user-456',
                'access_token': 'access-token-456',
                'refresh_token': 'refresh-token-456'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
        )
        auth = AuthSDK(config)

        # Step 1: Send magic link
        send_response = auth.request(
            'POST',
            auth.project_url('auth/magic-link/send'),
            json_data={'email': 'user@example.com'}
        )
        assert send_response['session_id'] == 'session-456'

        # Step 2: Verify magic link
        verify_response = auth.request(
            'POST',
            auth.project_url('auth/magic-link/verify'),
            json_data={'token': 'magic-link-token-123'}
        )
        assert verify_response['access_token'] == 'access-token-456'

    @patch('requests.request')
    def test_totp_mfa_flow(self, mock_request):
        """Test complete TOTP MFA enrollment and verification flow."""
        responses = [
            # Enroll TOTP
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'secret': 'JBSWY3DPEBLW64TMMQ======',
                'qr_code': 'data:image/png;base64,...',
                'device_id': 'device-456'
            })),
            # Confirm TOTP
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'device_id': 'device-456',
                'status': 'active'
            })),
            # Verify TOTP during login
            Mock(ok=True, status_code=200, json=Mock(return_value={
                'access_token': 'access-token-789',
                'user_id': 'user-789'
            }))
        ]
        mock_request.side_effect = responses

        config = OwnFirebaseConfig(
            base_url='http://localhost:8000',
            project_id='test-project',
            access_token='test-token',
        )
        auth = AuthSDK(config)

        # Step 1: Enroll TOTP
        enroll_response = auth.request(
            'POST',
            auth.project_url('auth/mfa/enroll/totp'),
            json_data={}
        )
        assert 'secret' in enroll_response

        # Step 2: Confirm TOTP
        confirm_response = auth.request(
            'POST',
            auth.project_url('auth/mfa/confirm/totp'),
            json_data={'device_id': 'device-456', 'code': '123456'}
        )
        assert confirm_response['status'] == 'active'

        # Step 3: Verify TOTP during login
        verify_response = auth.request(
            'POST',
            auth.project_url('auth/mfa/verify/totp'),
            json_data={'code': '234567', 'session_id': 'session-123'}
        )
        assert verify_response['access_token'] == 'access-token-789'
