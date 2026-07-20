"""OwnFirebase Auth SDK."""

from typing import Any, Dict, List, Optional

from .client import OwnFirebaseClient


class AuthSDK(OwnFirebaseClient):
    """Authentication service."""

    # ─── Core Auth ───────────────────────────────────────────────────────────────

    def register(
        self,
        email: str,
        password: str,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new user account. Returns AuthTokens."""
        body: Dict[str, Any] = {'email': email, 'password': password}
        if username is not None:
            body['username'] = username
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/register/',
            json_data=body,
            no_auth=True,
        )

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Log in with email/password. Returns AuthTokens."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/login/',
            json_data={'email': email, 'password': password},
            no_auth=True,
        )

    def refresh_token(self, refresh: str) -> Dict[str, Any]:
        """Exchange a refresh token for a new access token."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/refresh/',
            json_data={'refresh': refresh},
            no_auth=True,
        )

    def logout(self, refresh: str) -> None:
        """Invalidate a refresh token."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/logout/',
            json_data={'refresh': refresh},
        )

    def get_me(self) -> Dict[str, Any]:
        """Get the currently authenticated user."""
        return self.request('GET', f'{self.base_url}/api/v1/auth/me/')

    def anonymous_sign_in(self) -> Dict[str, Any]:
        """Create an anonymous session. Returns AuthTokens."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/anonymous-signin/',
            json_data={},
            no_auth=True,
        )

    def set_custom_claims(self, claims: Dict[str, Any]) -> Dict[str, Any]:
        """Set custom claims on the authenticated user's token."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/set-custom-claims/',
            json_data={'claims': claims},
        )

    # ─── Social Auth ─────────────────────────────────────────────────────────────

    def google_sign_in(self, id_token: str) -> Dict[str, Any]:
        """Sign in with a Google ID token. Returns AuthTokens."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/social/google/',
            json_data={'id_token': id_token},
            no_auth=True,
        )

    def github_sign_in(self, access_token: str) -> Dict[str, Any]:
        """Sign in with a GitHub access token. Returns AuthTokens."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/social/github/',
            json_data={'access_token': access_token},
            no_auth=True,
        )

    def list_linked_accounts(self) -> List[Dict[str, Any]]:
        """List social accounts linked to the authenticated user."""
        return self.request('GET', f'{self.base_url}/api/v1/auth/social/linked/')

    def unlink_social_account(self, account_id: str) -> None:
        """Unlink a social account."""
        return self.request(
            'DELETE',
            f'{self.base_url}/api/v1/auth/social/linked/{account_id}/',
        )

    # ─── Phone / OTP ─────────────────────────────────────────────────────────────

    def send_phone_otp(self, phone_number: str) -> Dict[str, Any]:
        """Send a one-time passcode to a phone number."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/phone/send-otp/',
            json_data={'phone_number': phone_number},
            no_auth=True,
        )

    def verify_phone_otp(self, phone_number: str, otp_code: str) -> Dict[str, Any]:
        """Verify a phone OTP and receive AuthTokens."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/phone/verify-otp/',
            json_data={'phone_number': phone_number, 'otp_code': otp_code},
            no_auth=True,
        )

    # ─── MFA ─────────────────────────────────────────────────────────────────────

    def enroll_totp(self) -> Dict[str, Any]:
        """Begin TOTP MFA enrollment. Returns device_id/secret/provisioning_uri."""
        return self.request(
            'POST', f'{self.base_url}/api/v1/auth/mfa/enroll/totp/', json_data={}
        )

    def confirm_totp(self, device_id: str, totp_code: str) -> Dict[str, Any]:
        """Confirm and activate a TOTP device enrolled via enroll_totp."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/mfa/confirm/totp/',
            json_data={'device_id': device_id, 'totp_code': totp_code},
        )

    def verify_totp(self, device_id: str, totp_code: str) -> Dict[str, Any]:
        """Verify a TOTP code for an already-confirmed device (e.g. at login)."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/mfa/verify/totp/',
            json_data={'device_id': device_id, 'totp_code': totp_code},
        )

    def enroll_sms(self, phone_number: str) -> Dict[str, Any]:
        """Begin SMS MFA enrollment."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/mfa/enroll/sms/',
            json_data={'phone_number': phone_number},
        )

    def confirm_sms(self, device_id: str, code: str) -> Dict[str, Any]:
        """Confirm and activate an SMS MFA device."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/mfa/confirm/sms/',
            json_data={'device_id': device_id, 'code': code},
        )

    def verify_sms(self, device_id: str, code: str) -> Dict[str, Any]:
        """Verify an SMS MFA code (e.g. at login). Returns AuthTokens."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/mfa/verify/sms/',
            json_data={'device_id': device_id, 'code': code},
        )

    def send_sms_code(self, device_id: str) -> Dict[str, Any]:
        """Send a new SMS MFA code for an enrolled device."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/mfa/send-sms-code/{device_id}/',
            json_data={},
        )

    def list_mfa_devices(self) -> List[Dict[str, Any]]:
        """List enrolled MFA devices for the authenticated user."""
        return self.request('GET', f'{self.base_url}/api/v1/auth/mfa/devices/')

    def delete_mfa_device(self, device_id: str) -> None:
        """Delete an enrolled MFA device."""
        return self.request(
            'DELETE', f'{self.base_url}/api/v1/auth/mfa/devices/{device_id}/'
        )

    # ─── Passwordless / Magic Link ────────────────────────────────────────────────

    def send_magic_link(self, email: str) -> Dict[str, Any]:
        """Send a passwordless magic link to an email address."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/magic-link/send/',
            json_data={'email': email},
            no_auth=True,
        )

    def verify_magic_link(self, token: str) -> Dict[str, Any]:
        """Verify a magic link token. Returns AuthTokens."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/magic-link/verify/',
            json_data={'token': token},
            no_auth=True,
        )

    # ─── Account Management ───────────────────────────────────────────────────────

    def upgrade_anonymous(
        self, email: str, password: str, password2: str
    ) -> Dict[str, Any]:
        """Upgrade an anonymous session to a full registered account."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/upgrade/',
            json_data={'email': email, 'password': password, 'password2': password2},
        )

    def set_password(
        self,
        new_password: str,
        new_password2: str,
        current_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set (or change) the authenticated user's password."""
        body: Dict[str, Any] = {
            'new_password': new_password,
            'new_password2': new_password2,
        }
        if current_password is not None:
            body['current_password'] = current_password
        return self.request(
            'POST', f'{self.base_url}/api/v1/auth/set-password/', json_data=body
        )

    def link_email(self, email: str, password: str) -> Dict[str, Any]:
        """Link an email/password credential to the authenticated user."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/link-email/',
            json_data={'email': email, 'password': password},
        )

    def verify_email_change(self, token: str) -> Dict[str, Any]:
        """Verify an email-change confirmation token."""
        return self.request(
            'POST',
            f'{self.base_url}/api/v1/auth/verify-email-change/',
            json_data={'token': token},
            no_auth=True,
        )

    # ─── Custom Token (project-scoped) ───────────────────────────────────────────

    def issue_custom_token(
        self, user_id: str, claims: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Issue a custom server-signed token for user_id, scoped to the project."""
        body: Dict[str, Any] = {'user_id': user_id}
        if claims is not None:
            body['claims'] = claims
        return self.request('POST', self.project_url('auth/custom-token/'), json_data=body)
