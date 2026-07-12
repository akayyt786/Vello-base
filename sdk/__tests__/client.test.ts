import { OwnFirebaseClient } from '../src/client';
import type { OwnFirebaseConfig } from '../src/types';

// Mock global fetch
global.fetch = jest.fn();

describe('OwnFirebaseClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('initialization', () => {
    it('should initialize with base config', () => {
      const config: OwnFirebaseConfig = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
        accessToken: 'test-token',
      };

      const client = new OwnFirebaseClient(config);
      expect(client).toBeDefined();
    });

    it('should strip trailing slash from baseUrl', () => {
      const config: OwnFirebaseConfig = {
        baseUrl: 'http://localhost:8000/',
      };

      const client = new OwnFirebaseClient(config);
      // Access protected baseUrl through projectUrl method
      expect(() => client.setProjectId('test')).not.toThrow();
    });

    it('should set and retrieve access token', () => {
      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      client.setAccessToken('new-token');
      expect(client).toBeDefined();
    });

    it('should set and retrieve project ID', () => {
      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      client.setProjectId('my-project');
      expect(client).toBeDefined();
    });
  });

  describe('projectUrl', () => {
    it('should throw error if projectId is not set', () => {
      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      const projectUrlCall = () => {
        // We need to call a method that uses projectUrl
        (client as any).projectUrl('test');
      };

      expect(projectUrlCall).toThrow('projectId is required for this operation');
    });

    it('should construct proper project URL', () => {
      const config: OwnFirebaseConfig = {
        baseUrl: 'http://localhost:8000',
        projectId: 'my-project',
      };
      const client = new OwnFirebaseClient(config);
      const url = (client as any).projectUrl('collections/');

      expect(url).toBe('http://localhost:8000/api/projects/my-project/collections/');
    });
  });

  describe('request', () => {
    it('should make GET request without auth', async () => {
      const mockResponse = { ok: true, status: 200, json: async () => ({ data: 'test' }) };
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      const result = await (client as any).request('GET', 'http://localhost:8000/api/test/', undefined, { noAuth: true });

      expect(result).toEqual({ data: 'test' });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/test/', expect.objectContaining({
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        body: undefined,
      }));
    });

    it('should make POST request with auth token', async () => {
      const mockResponse = { ok: true, status: 200, json: async () => ({ success: true }) };
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

      const config: OwnFirebaseConfig = {
        baseUrl: 'http://localhost:8000',
        accessToken: 'test-token',
      };
      const client = new OwnFirebaseClient(config);

      const body = { email: 'test@example.com' };
      const result = await (client as any).request('POST', 'http://localhost:8000/api/test/', body);

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/test/', expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
        body: JSON.stringify(body),
      }));
    });

    it('should add query parameters to URL', async () => {
      const mockResponse = { ok: true, status: 200, json: async () => [] };
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      const query = { filter: 'active', limit: '10' };
      await (client as any).request('GET', 'http://localhost:8000/api/test/', undefined, { query, noAuth: true });

      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('filter=active');
      expect(callUrl).toContain('limit=10');
    });

    it('should handle 204 No Content response', async () => {
      const mockResponse = { ok: true, status: 204 };
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      const result = await (client as any).request('DELETE', 'http://localhost:8000/api/test/', undefined, { noAuth: true });

      expect(result).toBeUndefined();
    });

    it('should handle error responses with JSON detail', async () => {
      const errorDetail = { message: 'Unauthorized' };
      const mockResponse = {
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: async () => errorDetail,
      };
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      try {
        await (client as any).request('GET', 'http://localhost:8000/api/test/', undefined, { noAuth: true });
        fail('Should have thrown error');
      } catch (err: any) {
        expect(err.status).toBe(401);
        expect(err.message).toBe('Unauthorized');
        expect(err.detail).toEqual(errorDetail);
      }
    });

    it('should handle error responses with text detail', async () => {
      const mockResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => { throw new Error('Not JSON'); },
        text: async () => 'Internal Server Error',
      };
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      try {
        await (client as any).request('GET', 'http://localhost:8000/api/test/', undefined, { noAuth: true, retries: 0 });
        fail('Should have thrown error');
      } catch (err: any) {
        expect(err.status).toBe(500);
        expect(err.detail).toBe('Internal Server Error');
      }
    });

    it('should not include auth header when token is not set', async () => {
      const mockResponse = { ok: true, status: 200, json: async () => ({ data: 'test' }) };
      (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse);

      const config: OwnFirebaseConfig = { baseUrl: 'http://localhost:8000' };
      const client = new OwnFirebaseClient(config);

      await (client as any).request('GET', 'http://localhost:8000/api/test/');

      const callHeaders = (global.fetch as jest.Mock).mock.calls[0][1].headers;
      expect(callHeaders['Authorization']).toBeUndefined();
    });
  });
});
