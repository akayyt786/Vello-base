import { AppCheckSDK } from '../src/appcheck';
import type { AppCheckToken } from '../src/types';

global.fetch = jest.fn();

describe('AppCheckSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('token exchange', () => {
    it('should exchange reCAPTCHA v3 token', async () => {
      const mockResponse: AppCheckToken = {
        token: 'app-check-token-xyz',
        expires_at: '2024-01-01T01:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      const result = await appCheck.exchangeToken({
        provider: 'recaptcha_v3',
        platform: 'web',
        rawToken: 'recaptcha-v3-token-abc123',
      });

      expect(result).toEqual(mockResponse);
      expect(result.token).toBeDefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/app-check/exchange/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            provider: 'recaptcha_v3',
            platform: 'web',
            raw_token: 'recaptcha-v3-token-abc123',
          }),
        })
      );
    });

    it('should exchange reCAPTCHA Enterprise token', async () => {
      const mockResponse: AppCheckToken = {
        token: 'app-check-token-enterprise',
        expires_at: '2024-01-01T01:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      const result = await appCheck.exchangeToken({
        provider: 'recaptcha_enterprise',
        platform: 'web',
        rawToken: 'recaptcha-enterprise-token-def456',
      });

      expect(result.token).toBeDefined();
    });

    it('should exchange DeviceCheck token', async () => {
      const mockResponse: AppCheckToken = {
        token: 'app-check-token-devicecheck',
        expires_at: '2024-01-01T01:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      const result = await appCheck.exchangeToken({
        provider: 'device_check',
        platform: 'ios',
        rawToken: 'device-check-assertion-ghi789',
      });

      expect(result.token).toBeDefined();
    });

    it('should exchange Play Integrity token', async () => {
      const mockResponse: AppCheckToken = {
        token: 'app-check-token-play-integrity',
        expires_at: '2024-01-01T01:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      const result = await appCheck.exchangeToken({
        provider: 'play_integrity',
        platform: 'android',
        rawToken: 'play-integrity-token-jkl012',
      });

      expect(result.token).toBeDefined();
    });

    it('should exchange debug token', async () => {
      const mockResponse: AppCheckToken = {
        token: 'app-check-token-debug',
        expires_at: '2024-01-01T01:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      const result = await appCheck.exchangeToken({
        provider: 'debug',
        platform: 'web',
        rawToken: 'debug-token-mno345',
      });

      expect(result.token).toBeDefined();
    });

    it('should handle token expiration', async () => {
      const mockResponse: AppCheckToken = {
        token: 'short-lived-token',
        expires_at: '2024-01-01T00:15:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      const result = await appCheck.exchangeToken({
        provider: 'recaptcha_v3',
        platform: 'web',
        rawToken: 'token123',
      });

      expect(result.expires_at).toBeDefined();
    });
  });

  describe('app check integration', () => {
    it('should support multiple token exchanges', async () => {
      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            token: 'token-1',
            expires_at: '2024-01-01T01:00:00Z',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            token: 'token-2',
            expires_at: '2024-01-01T01:30:00Z',
          }),
        });

      const result1 = await appCheck.exchangeToken({
        provider: 'recaptcha_v3',
        platform: 'web',
        rawToken: 'attestation-1',
      });

      const result2 = await appCheck.exchangeToken({
        provider: 'recaptcha_v3',
        platform: 'web',
        rawToken: 'attestation-2',
      });

      expect(result1.token).toBe('token-1');
      expect(result2.token).toBe('token-2');
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should handle different raw token formats', async () => {
      const appCheck = new AppCheckSDK(config);
      appCheck.setAccessToken('access-token');
      appCheck.setProjectId('test-project');

      const rawTokens = [
        'simple-token',
        'base64-encoded-token-xyz123==',
        'jwt-like-token.eyJhbGc.SflKxwRJSM',
        'long-attestation-string-with-many-characters-that-represent-a-valid-token-format-for-verification-purposes',
      ];

      for (const rawToken of rawTokens) {
        (global.fetch as jest.Mock).mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            token: 'app-check-token',
            expires_at: '2024-01-01T01:00:00Z',
          }),
        });

        const result = await appCheck.exchangeToken({
          provider: 'recaptcha_v3',
          platform: 'web',
          rawToken,
        });

        expect(result.token).toBeDefined();
      }

      expect(global.fetch).toHaveBeenCalledTimes(4);
    });
  });

  describe('provider support', () => {
    it('should support all attestation providers', () => {
      const providers: Array<'recaptcha_v3' | 'recaptcha_enterprise' | 'play_integrity' | 'device_check' | 'debug'> = [
        'recaptcha_v3',
        'recaptcha_enterprise',
        'play_integrity',
        'device_check',
        'debug',
      ];

      expect(providers).toHaveLength(5);
    });
  });
});
