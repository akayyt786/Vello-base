import { OwnFirebaseClient } from './client';
import type { AuthTokens, User, MFADevice, LinkedSocialAccount, CustomToken } from './types';

export class AuthSDK extends OwnFirebaseClient {
  // ─── Core Auth ───────────────────────────────────────────────────────────────

  async register(
    email: string,
    password: string,
    username?: string
  ): Promise<AuthTokens> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/register/`,
      { email, password, username },
      { noAuth: true }
    );
  }

  async login(email: string, password: string): Promise<AuthTokens> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/login/`,
      { email, password },
      { noAuth: true }
    );
  }

  async refreshToken(refresh: string): Promise<{ access: string }> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/refresh/`,
      { refresh },
      { noAuth: true }
    );
  }

  async logout(refresh: string): Promise<void> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/logout/`, {
      refresh,
    });
  }

  async getMe(): Promise<User> {
    return this.request('GET', `${this.baseUrl}/api/v1/auth/me/`);
  }

  async anonymousSignIn(): Promise<AuthTokens> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/anonymous-signin/`,
      {},
      { noAuth: true }
    );
  }

  async setCustomClaims(claims: Record<string, unknown>): Promise<{ detail: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/set-custom-claims/`, {
      claims,
    });
  }

  // ─── Social Auth ─────────────────────────────────────────────────────────────

  async googleSignIn(idToken: string): Promise<AuthTokens> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/social/google/`,
      { id_token: idToken },
      { noAuth: true }
    );
  }

  async githubSignIn(accessToken: string): Promise<AuthTokens> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/social/github/`,
      { access_token: accessToken },
      { noAuth: true }
    );
  }

  async listLinkedAccounts(): Promise<LinkedSocialAccount[]> {
    return this.request('GET', `${this.baseUrl}/api/v1/auth/social/linked/`);
  }

  async unlinkSocialAccount(accountId: string): Promise<void> {
    return this.request(
      'DELETE',
      `${this.baseUrl}/api/v1/auth/social/linked/${accountId}/`
    );
  }

  // ─── Phone / OTP ─────────────────────────────────────────────────────────────

  async sendPhoneOTP(phoneNumber: string): Promise<{ detail: string }> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/phone/send-otp/`,
      { phone_number: phoneNumber },
      { noAuth: true }
    );
  }

  async verifyPhoneOTP(
    phoneNumber: string,
    code: string
  ): Promise<AuthTokens> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/phone/verify-otp/`,
      { phone_number: phoneNumber, code },
      { noAuth: true }
    );
  }

  // ─── MFA ─────────────────────────────────────────────────────────────────────

  async enrollTOTP(): Promise<{ totp_uri: string; secret: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/mfa/enroll/totp/`, {});
  }

  async confirmTOTP(code: string): Promise<{ detail: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/mfa/confirm/totp/`, {
      code,
    });
  }

  async verifyTOTP(code: string): Promise<AuthTokens> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/mfa/verify/totp/`, {
      code,
    });
  }

  async enrollSMS(phoneNumber: string): Promise<{ detail: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/mfa/enroll/sms/`, {
      phone_number: phoneNumber,
    });
  }

  async confirmSMS(deviceId: string, code: string): Promise<{ detail: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/mfa/confirm/sms/`, {
      device_id: deviceId,
      code,
    });
  }

  async verifySMS(deviceId: string, code: string): Promise<AuthTokens> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/mfa/verify/sms/`, {
      device_id: deviceId,
      code,
    });
  }

  async sendSMSCode(deviceId: string): Promise<{ detail: string }> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/mfa/send-sms-code/${deviceId}/`,
      {}
    );
  }

  async listMFADevices(): Promise<MFADevice[]> {
    return this.request('GET', `${this.baseUrl}/api/v1/auth/mfa/devices/`);
  }

  async deleteMFADevice(deviceId: string): Promise<void> {
    return this.request(
      'DELETE',
      `${this.baseUrl}/api/v1/auth/mfa/devices/${deviceId}/`
    );
  }

  // ─── Passwordless / Magic Link ────────────────────────────────────────────────

  async sendMagicLink(email: string): Promise<{ detail: string }> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/magic-link/send/`,
      { email },
      { noAuth: true }
    );
  }

  async verifyMagicLink(token: string): Promise<AuthTokens> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/magic-link/verify/`,
      { token },
      { noAuth: true }
    );
  }

  // ─── Account Management ───────────────────────────────────────────────────────

  async upgradeAnonymous(
    email: string,
    password: string,
    password2: string
  ): Promise<AuthTokens> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/upgrade/`, {
      email,
      password,
      password2,
    });
  }

  async setPassword(
    newPassword: string,
    newPassword2: string,
    currentPassword?: string
  ): Promise<{ detail: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/set-password/`, {
      new_password: newPassword,
      new_password2: newPassword2,
      current_password: currentPassword,
    });
  }

  async linkEmail(email: string, password: string): Promise<{ detail: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/auth/link-email/`, {
      email,
      password,
    });
  }

  async verifyEmailChange(token: string): Promise<{ detail: string }> {
    return this.request(
      'POST',
      `${this.baseUrl}/api/v1/auth/verify-email-change/`,
      { token },
      { noAuth: true }
    );
  }

  // ─── Custom Token (project-scoped) ───────────────────────────────────────────

  async issueCustomToken(
    userId: string,
    claims?: Record<string, unknown>
  ): Promise<CustomToken> {
    return this.request(
      'POST',
      this.projectUrl('auth/custom-token/'),
      { user_id: userId, claims }
    );
  }
}
