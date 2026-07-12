import { FunctionsSDK } from '../src/functions';
import type { FunctionDefinition, FunctionInvocation, FunctionLog } from '../src/types';

global.fetch = jest.fn();

describe('FunctionsSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('function management', () => {
    it('should list functions', async () => {
      const mockFunctions: FunctionDefinition[] = [
        {
          id: 'fn1',
          name: 'sendEmail',
          runtime: 'python3.9',
          entry_point: 'main',
          source_code: 'def main(request): return {"status": "ok"}',
          is_active: true,
        },
        {
          id: 'fn2',
          name: 'processImage',
          runtime: 'nodejs18',
          entry_point: 'handler',
          source_code: 'exports.handler = async (event) => ({ status: "ok" });',
          is_active: true,
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockFunctions,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.listFunctions();

      expect(result).toEqual(mockFunctions);
      expect(result).toHaveLength(2);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/functions/',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should get specific function', async () => {
      const mockFunction: FunctionDefinition = {
        id: 'fn1',
        name: 'sendEmail',
        runtime: 'python3.9',
        entry_point: 'main',
        source_code: 'def main(request): return {"status": "ok"}',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockFunction,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.getFunction('sendEmail');

      expect(result).toEqual(mockFunction);
      expect(result.name).toBe('sendEmail');
    });

    it('should create function', async () => {
      const mockFunction: FunctionDefinition = {
        id: 'fn3',
        name: 'webhookHandler',
        runtime: 'nodejs18',
        entry_point: 'handler',
        source_code: 'exports.handler = async (event) => ({ status: "received" });',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockFunction,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.createFunction({
        name: 'webhookHandler',
        runtime: 'nodejs18',
        entry_point: 'handler',
        source_code: 'exports.handler = async (event) => ({ status: "received" });',
        is_active: true,
      });

      expect(result).toEqual(mockFunction);
      expect(result.is_active).toBe(true);
    });

    it('should update function', async () => {
      const mockFunction: FunctionDefinition = {
        id: 'fn1',
        name: 'sendEmail',
        runtime: 'python3.9',
        entry_point: 'main',
        source_code: 'def main(request): return {"status": "updated"}',
        is_active: false,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockFunction,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.updateFunction('sendEmail', {
        source_code: 'def main(request): return {"status": "updated"}',
        is_active: false,
      });

      expect(result.is_active).toBe(false);
      expect(result.source_code).toContain('updated');
    });

    it('should delete function', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.deleteFunction('sendEmail');

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/functions/sendEmail/',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('function invocation', () => {
    it('should invoke function without payload', async () => {
      const mockInvocation: FunctionInvocation = {
        invocation_id: 'inv1',
        status: 'success',
        result: { message: 'Function executed' },
        duration_ms: 234,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockInvocation,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.invoke('sendEmail');

      expect(result).toEqual(mockInvocation);
      expect(result.status).toBe('success');
      expect(result.duration_ms).toBe(234);
    });

    it('should invoke function with payload', async () => {
      const mockInvocation: FunctionInvocation = {
        invocation_id: 'inv2',
        status: 'success',
        result: { emailsSent: 5 },
        duration_ms: 1234,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockInvocation,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const payload = {
        recipients: ['user1@example.com', 'user2@example.com'],
        subject: 'Welcome',
        body: 'Welcome to OwnFirebase',
      };

      const result = await functions.invoke('sendEmail', payload);

      expect(result).toEqual(mockInvocation);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/functions/sendEmail/invoke/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ payload }),
        })
      );
    });

    it('should handle function invocation error', async () => {
      const mockInvocation: FunctionInvocation = {
        invocation_id: 'inv3',
        status: 'error',
        error: 'TypeError: Cannot read property of undefined',
        duration_ms: 450,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockInvocation,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.invoke('buggyFunction');

      expect(result.status).toBe('error');
      expect(result.error).toContain('TypeError');
    });

    it('should handle timeout in function invocation', async () => {
      const mockInvocation: FunctionInvocation = {
        invocation_id: 'inv4',
        status: 'timeout',
        error: 'Function execution exceeded timeout',
        duration_ms: 30000,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 504,
        json: async () => mockInvocation,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      try {
        await functions.invoke('slowFunction');
      } catch (err: any) {
        expect(err.status).toBe(504);
      }
    });
  });

  describe('function logs', () => {
    it('should get function logs', async () => {
      const mockLogs: FunctionLog[] = [
        {
          id: 'log1',
          level: 'INFO',
          message: 'Function started',
          timestamp: '2024-01-01T00:00:00Z',
        },
        {
          id: 'log2',
          level: 'INFO',
          message: 'Processing data...',
          timestamp: '2024-01-01T00:00:01Z',
        },
        {
          id: 'log3',
          level: 'INFO',
          message: 'Function completed',
          timestamp: '2024-01-01T00:00:02Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockLogs,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.getLogs('sendEmail');

      expect(result).toEqual(mockLogs);
      expect(result).toHaveLength(3);
    });

    it('should get function logs with limit', async () => {
      const mockLogs: FunctionLog[] = [
        {
          id: 'log1',
          level: 'INFO',
          message: 'Function started',
          timestamp: '2024-01-01T00:00:00Z',
        },
        {
          id: 'log2',
          level: 'INFO',
          message: 'Function completed',
          timestamp: '2024-01-01T00:00:02Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockLogs,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.getLogs('sendEmail', { limit: 2 });

      expect(result).toHaveLength(2);
      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('limit=2');
    });

    it('should get function logs since timestamp', async () => {
      const mockLogs: FunctionLog[] = [
        {
          id: 'log2',
          level: 'WARNING',
          message: 'High memory usage',
          timestamp: '2024-01-01T00:05:00Z',
        },
        {
          id: 'log3',
          level: 'ERROR',
          message: 'Connection timeout',
          timestamp: '2024-01-01T00:06:00Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockLogs,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.getLogs('sendEmail', {
        since: '2024-01-01T00:04:00Z',
      });

      expect(result).toHaveLength(2);
      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('since=2024-01-01T00%3A04%3A00Z');
    });

    it('should handle logs with different levels', async () => {
      const mockLogs: FunctionLog[] = [
        {
          id: 'log1',
          level: 'DEBUG',
          message: 'Debug information',
          timestamp: '2024-01-01T00:00:00Z',
        },
        {
          id: 'log2',
          level: 'INFO',
          message: 'Info message',
          timestamp: '2024-01-01T00:00:01Z',
        },
        {
          id: 'log3',
          level: 'WARNING',
          message: 'Warning message',
          timestamp: '2024-01-01T00:00:02Z',
        },
        {
          id: 'log4',
          level: 'ERROR',
          message: 'Error message',
          timestamp: '2024-01-01T00:00:03Z',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockLogs,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.getLogs('sendEmail');

      expect(result).toHaveLength(4);
      expect(result.map(l => l.level)).toContain('DEBUG');
      expect(result.map(l => l.level)).toContain('ERROR');
    });
  });

  describe('multi-runtime support', () => {
    it('should support Python functions', async () => {
      const pythonFunction: FunctionDefinition = {
        id: 'fn_py',
        name: 'processData',
        runtime: 'python3.9',
        entry_point: 'handler',
        source_code: 'def handler(event): return {"result": "processed"}',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => pythonFunction,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.createFunction(pythonFunction);

      expect(result.runtime).toBe('python3.9');
    });

    it('should support Node.js functions', async () => {
      const nodeFunction: FunctionDefinition = {
        id: 'fn_js',
        name: 'apiHandler',
        runtime: 'nodejs18',
        entry_point: 'handler',
        source_code: 'exports.handler = async (event) => ({ status: 200 });',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => nodeFunction,
      });

      const functions = new FunctionsSDK(config);
      functions.setAccessToken('access-token');
      functions.setProjectId('test-project');

      const result = await functions.createFunction(nodeFunction);

      expect(result.runtime).toBe('nodejs18');
    });
  });
});
