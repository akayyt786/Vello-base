import { AuthSDK } from '../src/auth';
import type { AuthTokens, User, MFADevice, LinkedSocialAccount } from '../src/types';

global.fetch = jest.fn();

describe('AuthSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('basic auth', () => {
    it('should register a new user', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
        email: 'test@example.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.register('test@example.com', 'password123', 'testuser');

      expect(result).toEqual(mockTokens);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/register/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123',
            username: 'testuser',
          }),
        })
      );
    });

    it('should login user', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
        email: 'test@example.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.login('test@example.com', 'password123');

      expect(result).toEqual(mockTokens);
    });

    it('should refresh access token', async () => {
      const mockResponse = { access: 'new-access-token' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      const result = await auth.refreshToken('refresh-token');

      expect(result).toEqual(mockResponse);
    });

    it('should logout user', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.logout('refresh-token');

      expect(result).toBeUndefined();
    });

    it('should get current user', async () => {
      const mockUser: User = {
        id: 'user123',
        email: 'test@example.com',
        username: 'testuser',
        first_name: 'Test',
        last_name: 'User',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockUser,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.getMe();

      expect(result).toEqual(mockUser);
    });

    it('should perform anonymous sign in', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'anon-user123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.anonymousSignIn();

      expect(result).toEqual(mockTokens);
    });

    it('should set custom claims', async () => {
      const mockResponse = { detail: 'Claims set successfully' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const claims = { role: 'admin', department: 'engineering' };
      const result = await auth.setCustomClaims(claims);

      expect(result).toEqual(mockResponse);
    });
  });

  describe('social auth', () => {
    it('should sign in with Google', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
        email: 'user@gmail.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.googleSignIn('google-id-token');

      expect(result).toEqual(mockTokens);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/social/google/',
        expect.objectContaining({
          body: JSON.stringify({ id_token: 'google-id-token' }),
        })
      );
    });

    it('should sign in with GitHub', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
        email: 'user@github.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.githubSignIn('github-access-token');

      expect(result).toEqual(mockTokens);
    });

    it('should list linked social accounts', async () => {
      const mockAccounts: LinkedSocialAccount[] = [
        {
          id: 'link1',
          provider: 'google',
          provider_uid: 'google-123',
          email: 'user@gmail.com',
          linked_at: '2024-01-01T00:00:00Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockAccounts,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.listLinkedAccounts();

      expect(result).toEqual(mockAccounts);
    });

    it('should unlink social account', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.unlinkSocialAccount('link1');

      expect(result).toBeUndefined();
    });
  });

  describe('phone/OTP auth', () => {
    it('should send phone OTP', async () => {
      const mockResponse = { detail: 'OTP sent' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      const result = await auth.sendPhoneOTP('+1234567890');

      expect(result).toEqual(mockResponse);
    });

    it('should verify phone OTP', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.verifyPhoneOTP('+1234567890', '123456');

      expect(result).toEqual(mockTokens);
    });
  });

  describe('MFA - TOTP', () => {
    it('should enroll TOTP', async () => {
      const mockResponse = {
        totp_uri: 'otpauth://totp/OwnFirebase:user@example.com?secret=SECRET',
        secret: 'SECRET123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.enrollTOTP();

      expect(result).toEqual(mockResponse);
      expect(result.secret).toBeDefined();
    });

    it('should confirm TOTP enrollment', async () => {
      const mockResponse = { detail: 'TOTP confirmed' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.confirmTOTP('123456');

      expect(result).toEqual(mockResponse);
    });

    it('should verify TOTP code', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.verifyTOTP('123456');

      expect(result).toEqual(mockTokens);
    });
  });

  describe('MFA - SMS', () => {
    it('should enroll SMS MFA', async () => {
      const mockResponse = { detail: 'SMS enrollment initiated' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.enrollSMS('+1234567890');

      expect(result).toEqual(mockResponse);
    });

    it('should confirm SMS MFA', async () => {
      const mockResponse = { detail: 'SMS confirmed' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.confirmSMS('device123', '123456');

      expect(result).toEqual(mockResponse);
    });

    it('should verify SMS code', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.verifySMS('device123', '123456');

      expect(result).toEqual(mockTokens);
    });

    it('should send SMS code', async () => {
      const mockResponse = { detail: 'SMS code sent' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.sendSMSCode('device123');

      expect(result).toEqual(mockResponse);
    });

    it('should list MFA devices', async () => {
      const mockDevices: MFADevice[] = [
        {
          id: 'device1',
          type: 'totp',
          name: 'Authenticator App',
          confirmed: true,
          created_at: '2024-01-01T00:00:00Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockDevices,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.listMFADevices();

      expect(result).toEqual(mockDevices);
    });

    it('should delete MFA device', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.deleteMFADevice('device1');

      expect(result).toBeUndefined();
    });
  });

  describe('passwordless/magic link', () => {
    it('should send magic link', async () => {
      const mockResponse = { detail: 'Magic link sent' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      const result = await auth.sendMagicLink('test@example.com');

      expect(result).toEqual(mockResponse);
    });

    it('should verify magic link', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
        email: 'test@example.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.verifyMagicLink('magic-token-123');

      expect(result).toEqual(mockTokens);
    });
  });

  describe('account management', () => {
    it('should upgrade anonymous user', async () => {
      const mockTokens: AuthTokens = {
        access: 'access-token',
        refresh: 'refresh-token',
        user_id: 'user123',
        email: 'test@example.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockTokens,
      });

      const auth = new AuthSDK(config);
      const result = await auth.upgradeAnonymous('test@example.com', 'password123', 'password123');

      expect(result).toEqual(mockTokens);
    });

    it('should set password', async () => {
      const mockResponse = { detail: 'Password updated' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.setPassword('newpassword123', 'newpassword123', 'oldpassword');

      expect(result).toEqual(mockResponse);
    });

    it('should link email to account', async () => {
      const mockResponse = { detail: 'Email linked' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      const result = await auth.linkEmail('newemail@example.com', 'password123');

      expect(result).toEqual(mockResponse);
    });

    it('should verify email change', async () => {
      const mockResponse = { detail: 'Email changed' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      const result = await auth.verifyEmailChange('email-change-token');

      expect(result).toEqual(mockResponse);
    });
  });

  describe('custom token', () => {
    it('should issue custom token', async () => {
      const mockResponse = { custom_token: 'custom-jwt-token' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const auth = new AuthSDK(config);
      auth.setAccessToken('access-token');
      auth.setProjectId('test-project');

      const result = await auth.issueCustomToken('user123', { role: 'admin' });

      expect(result).toEqual(mockResponse);
    });
  });
});
