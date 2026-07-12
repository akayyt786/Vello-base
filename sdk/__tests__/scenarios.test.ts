import { initOwnFirebase } from '../src/index';
import type { AuthTokens, DataDocument } from '../src/types';

global.fetch = jest.fn();

describe('OwnFirebase Comprehensive Scenarios', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const baseUrl = 'http://localhost:8000';

  describe('auth flow scenario', () => {
    it('should perform complete user auth flow', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });

      // Register
      const mockRegisterResponse: AuthTokens = {
        access: 'access-token-123',
        refresh: 'refresh-token-abc',
        user_id: 'user123',
        email: 'newuser@example.com',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRegisterResponse,
      });

      const registerResult = await app.auth.register(
        'newuser@example.com',
        'password123',
        'newuser'
      );

      expect(registerResult.user_id).toBe('user123');

      // Set token for subsequent calls
      app.setAccessToken(registerResult.access);

      // Get current user
      const mockUserResponse = {
        id: 'user123',
        email: 'newuser@example.com',
        username: 'newuser',
        first_name: 'New',
        last_name: 'User',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockUserResponse,
      });

      const userResult = await app.auth.getMe();

      expect(userResult.email).toBe('newuser@example.com');
    });

    it('should handle token refresh flow', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });

      // Initial token
      app.setAccessToken('old-access-token');

      // Refresh token
      const mockRefreshResponse = { access: 'new-access-token' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockRefreshResponse,
      });

      const refreshResult = await app.auth.refreshToken('refresh-token-abc');

      expect(refreshResult.access).toBe('new-access-token');

      // Update app with new token
      app.setAccessToken(refreshResult.access);
      expect(() => app.setAccessToken(refreshResult.access)).not.toThrow();
    });
  });

  describe('data operations scenario', () => {
    it('should perform complete data CRUD flow', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      // Create collection
      const mockCollectionResponse = {
        id: 'col1',
        name: 'users',
        document_count: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockCollectionResponse,
      });

      const collectionResult = await app.data.createCollection('users');
      expect(collectionResult.name).toBe('users');

      // Create document
      const mockDocumentResponse: DataDocument = {
        id: 'doc123',
        collection: 'users',
        data: { name: 'John', email: 'john@example.com' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockDocumentResponse,
      });

      const docResult = await app.data.createDocument('users', {
        name: 'John',
        email: 'john@example.com',
      });

      expect(docResult.id).toBe('doc123');

      // Update document
      const mockUpdateResponse: DataDocument = {
        ...mockDocumentResponse,
        data: { name: 'John Updated', email: 'john@example.com' },
        updated_at: '2024-01-02T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockUpdateResponse,
      });

      const updateResult = await app.data.updateDocument('users', 'doc123', {
        name: 'John Updated',
      });

      expect(updateResult.data.name).toBe('John Updated');

      // Delete document
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const deleteResult = await app.data.deleteDocument('users', 'doc123');
      expect(deleteResult).toBeUndefined();
    });

    it('should perform batch write operations', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      const mockBatchResponse = {
        written: 3,
        errors: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockBatchResponse,
      });

      const result = await app.data.writeBatch([
        {
          op: 'set',
          collection: 'users',
          doc_id: 'u1',
          data: { name: 'User 1' },
        },
        {
          op: 'set',
          collection: 'users',
          doc_id: 'u2',
          data: { name: 'User 2' },
        },
        {
          op: 'set',
          collection: 'users',
          doc_id: 'u3',
          data: { name: 'User 3' },
        },
      ]);

      expect(result.written).toBe(3);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('analytics tracking scenario', () => {
    it('should track user journey with analytics', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      const userId = 'user123';
      const sessionId = 'session-abc-123';

      // Log page view
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'event1',
          name: 'page_view',
          params: { page: '/home' },
          timestamp: '2024-01-01T00:00:00Z',
          user_id: userId,
          session_id: sessionId,
        }),
      });

      const pageViewResult = await app.analytics.logEvent(
        'page_view',
        { page: '/home' },
        { userId, sessionId }
      );

      expect(pageViewResult.name).toBe('page_view');

      // Log button click
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'event2',
          name: 'button_click',
          params: { button_id: 'signup_btn' },
          timestamp: '2024-01-01T00:00:05Z',
          user_id: userId,
          session_id: sessionId,
        }),
      });

      const clickResult = await app.analytics.logEvent(
        'button_click',
        { button_id: 'signup_btn' },
        { userId, sessionId }
      );

      expect(clickResult.name).toBe('button_click');

      // Set user property
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'prop1',
          name: 'subscription_tier',
          value: 'premium',
          user_id: userId,
        }),
      });

      const propertyResult = await app.analytics.setUserProperty(
        'subscription_tier',
        'premium'
      );

      expect(propertyResult.name).toBe('subscription_tier');
    });

    it('should query analytics data', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          metric: 'active_users',
          rows: [{ metric_value: 1250 }],
        }),
      });

      const result = await app.analytics.query({
        metric: 'active_users',
        start_date: '2024-01-01',
        end_date: '2024-01-31',
      });

      expect(result.metric).toBe('active_users');
      expect(result.rows[0].metric_value).toBe(1250);
    });
  });

  describe('multi-service scenario', () => {
    it('should use multiple services in sequence', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });

      // Auth
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          access: 'token123',
          refresh: 'refresh123',
          user_id: 'user1',
          email: 'user@example.com',
        }),
      });

      const authResult = await app.auth.login('user@example.com', 'password');
      app.setAccessToken(authResult.access);

      // Data
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'doc1',
          collection: 'posts',
          data: { title: 'My Post' },
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        }),
      });

      const docResult = await app.data.createDocument('posts', { title: 'My Post' });

      // Analytics
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'event1',
          name: 'post_created',
          params: { post_id: 'doc1' },
          timestamp: '2024-01-01T00:00:01Z',
          user_id: 'user1',
        }),
      });

      const eventResult = await app.analytics.logEvent(
        'post_created',
        { post_id: 'doc1' },
        { userId: 'user1' }
      );

      expect(authResult.user_id).toBe('user1');
      expect(docResult.id).toBe('doc1');
      expect(eventResult.name).toBe('post_created');
    });
  });

  describe('real-time and notification scenario', () => {
    it('should register token and send push notification', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      // Register push token
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'token1',
          token: 'fcm-token-xyz',
          platform: 'fcm',
          is_active: true,
        }),
      });

      const tokenResult = await app.push.registerToken('fcm-token-xyz', 'fcm');
      expect(tokenResult.platform).toBe('fcm');

      // Send notification
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'notif1',
          title: 'Hello',
          body: 'You have a new message',
          status: 'sent',
          sent_at: '2024-01-01T00:00:00Z',
          recipient_count: 1,
        }),
      });

      const notifResult = await app.push.sendToDevice('token1', {
        title: 'Hello',
        body: 'You have a new message',
      });

      expect(notifResult.status).toBe('sent');
    });
  });

  describe('function invocation scenario', () => {
    it('should invoke cloud function', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      // List functions
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [
          {
            id: 'fn1',
            name: 'processPayment',
            runtime: 'nodejs18',
            entry_point: 'handler',
            source_code: 'code',
            is_active: true,
          },
        ],
      });

      const functionsResult = await app.functions.listFunctions();
      expect(functionsResult).toHaveLength(1);

      // Invoke function
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          invocation_id: 'inv1',
          status: 'success',
          result: { transactionId: 'tx123', amount: 99.99 },
          duration_ms: 234,
        }),
      });

      const invokeResult = await app.functions.invoke('processPayment', {
        amount: 99.99,
        currency: 'USD',
      });

      expect(invokeResult.status).toBe('success');
      expect((invokeResult.result as any).transactionId).toBe('tx123');
    });

    it('should get function logs', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [
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
            timestamp: '2024-01-01T00:00:01Z',
          },
        ],
      });

      const logsResult = await app.functions.getLogs('processPayment');
      expect(logsResult).toHaveLength(2);
    });
  });

  describe('configuration management scenario', () => {
    it('should manage remote config parameters', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      // Create parameter
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'param1',
          key: 'feature_new_ui',
          default_value: 'false',
          description: 'Enable new UI',
          value_type: 'boolean',
        }),
      });

      const paramResult = await app.remoteConfig.createParameter({
        key: 'feature_new_ui',
        default_value: 'false',
        description: 'Enable new UI',
        value_type: 'boolean',
      });

      expect(paramResult.key).toBe('feature_new_ui');

      // Create condition for parameter
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'cond1',
          name: 'ios_only',
          expression: 'platform == "ios"',
          value: 'true',
        }),
      });

      const condResult = await app.remoteConfig.createCondition('param1', {
        name: 'ios_only',
        expression: 'platform == "ios"',
        value: 'true',
      });

      expect(condResult.expression).toContain('ios');
    });
  });

  describe('A/B testing scenario', () => {
    it('should run A/B test experiment', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      // Create experiment
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'exp1',
          name: 'checkout_v2',
          status: 'running',
          variants: [
            { id: 'v1', name: 'control', allocation: 50, config: {} },
            { id: 'v2', name: 'new_flow', allocation: 50, config: {} },
          ],
        }),
      });

      const expResult = await app.ab.createExperiment({
        name: 'checkout_v2',
        status: 'running',
      });

      expect(expResult.status).toBe('running');

      // Get variant assignment
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          variant_name: 'new_flow',
          config: { flow: 'simplified' },
          experiment_name: 'checkout_v2',
        }),
      });

      const assignmentResult = await app.ab.getAssignment('exp1', 'user123');

      expect(assignmentResult.variant_name).toBe('new_flow');

      // Record conversion
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const conversionResult = await app.ab.recordConversion(
        'exp1',
        'user123',
        'purchase',
        99.99
      );

      expect(conversionResult).toBeUndefined();
    });
  });

  describe('AI and RAG scenario', () => {
    it('should perform chat and RAG queries', async () => {
      const app = initOwnFirebase({ baseUrl, projectId: 'test-project' });
      app.setAccessToken('test-token');

      // Chat
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          content: 'Hello! I can help you with OwnFirebase.',
          model: 'claude-haiku-4-5-20251001',
          provider: 'anthropic',
          usage: { prompt_tokens: 20, completion_tokens: 15, total_tokens: 35 },
        }),
      });

      const chatResult = await app.ai.chat([
        { role: 'user', content: 'What is OwnFirebase?' },
      ]);

      expect(chatResult.content).toContain('OwnFirebase');

      // Search
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          results: [
            {
              id: 'doc1',
              content: 'OwnFirebase is a backend platform',
              score: 0.95,
              external_id: 'e1',
            },
          ],
        }),
      });

      const searchResult = await app.ai.search('collection1', 'What is OwnFirebase?');

      expect(searchResult).toHaveLength(1);
      expect(searchResult[0].score).toBe(0.95);

      // RAG query
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          answer: 'OwnFirebase is a comprehensive backend platform...',
          sources: [{ id: 'doc1', score: 0.95 }],
        }),
      });

      const ragResult = await app.ai.ragQuery('collection1', 'Tell me about OwnFirebase');

      expect(ragResult.answer).toBeDefined();
      expect(ragResult.sources).toHaveLength(1);
    });
  });
});
