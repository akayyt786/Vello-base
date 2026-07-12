import { AISDK } from '../src/ai';
import type { ChatMessage, ChatCompletion, SearchResult } from '../src/types';

global.fetch = jest.fn();

describe('AISDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('chat completion', () => {
    it('should send chat message with default options', async () => {
      const mockCompletion: ChatCompletion = {
        content: 'Hello! I am Claude. How can I help you today?',
        model: 'claude-haiku-4-5-20251001',
        provider: 'anthropic',
        usage: {
          prompt_tokens: 10,
          completion_tokens: 20,
          total_tokens: 30,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCompletion,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const messages: ChatMessage[] = [
        { role: 'user', content: 'Hello!' },
      ];

      const result = await ai.chat(messages);

      expect(result).toEqual(mockCompletion);
      expect(result.provider).toBe('anthropic');
      expect(result.usage.total_tokens).toBe(30);
    });

    it('should send chat with custom options', async () => {
      const mockCompletion: ChatCompletion = {
        content: 'The weather is sunny.',
        model: 'claude-opus',
        provider: 'anthropic',
        usage: {
          prompt_tokens: 50,
          completion_tokens: 10,
          total_tokens: 60,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCompletion,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const messages: ChatMessage[] = [
        { role: 'system', content: 'You are a weather expert.' },
        { role: 'user', content: 'What is the weather?' },
      ];

      const result = await ai.chat(messages, {
        provider: 'anthropic',
        model: 'claude-opus',
        maxTokens: 500,
        temperature: 0.3,
      });

      expect(result.model).toBe('claude-opus');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/ai/chat/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            messages,
            provider: 'anthropic',
            model: 'claude-opus',
            max_tokens: 500,
            temperature: 0.3,
            system: undefined,
          }),
        })
      );
    });

    it('should send chat with system prompt', async () => {
      const mockCompletion: ChatCompletion = {
        content: 'The answer is 42.',
        model: 'claude-haiku-4-5-20251001',
        provider: 'anthropic',
        usage: {
          prompt_tokens: 30,
          completion_tokens: 5,
          total_tokens: 35,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCompletion,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const messages: ChatMessage[] = [
        { role: 'user', content: 'What is the answer to life, the universe, and everything?' },
      ];

      const result = await ai.chat(messages, {
        system: 'You are a fan of Douglas Adams.',
        temperature: 0.8,
      });

      expect(result.content).toContain('42');
    });

    it('should support Google provider', async () => {
      const mockCompletion: ChatCompletion = {
        content: 'This is a Gemini response.',
        model: 'gemini-pro',
        provider: 'google',
        usage: {
          prompt_tokens: 20,
          completion_tokens: 15,
          total_tokens: 35,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCompletion,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const messages: ChatMessage[] = [
        { role: 'user', content: 'Hello Gemini!' },
      ];

      const result = await ai.chat(messages, {
        provider: 'google',
        model: 'gemini-pro',
      });

      expect(result.provider).toBe('google');
      expect(result.model).toBe('gemini-pro');
    });

    it('should handle multi-turn conversation', async () => {
      const mockCompletion: ChatCompletion = {
        content: 'The capital of France is Paris.',
        model: 'claude-haiku-4-5-20251001',
        provider: 'anthropic',
        usage: {
          prompt_tokens: 50,
          completion_tokens: 10,
          total_tokens: 60,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCompletion,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const messages: ChatMessage[] = [
        { role: 'user', content: 'What is the capital of France?' },
        { role: 'assistant', content: 'The capital of France is Paris.' },
        { role: 'user', content: 'Tell me more about it.' },
      ];

      const result = await ai.chat(messages);

      expect(result.content).toBeDefined();
    });
  });

  describe('semantic search', () => {
    it('should search vector collection', async () => {
      const mockResults: SearchResult[] = [
        {
          id: 'result1',
          content: 'OwnFirebase is a backend-as-a-service platform.',
          score: 0.95,
          external_id: 'doc1',
        },
        {
          id: 'result2',
          content: 'The platform provides database, auth, and AI capabilities.',
          score: 0.87,
          external_id: 'doc2',
        },
        {
          id: 'result3',
          content: 'It supports real-time data synchronization.',
          score: 0.75,
          external_id: 'doc3',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ results: mockResults }),
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const results = await ai.search('collection1', 'What is OwnFirebase?', 3);

      expect(results).toEqual(mockResults);
      expect(results).toHaveLength(3);
      expect(results[0].score).toBe(0.95);
    });

    it('should search with default topK', async () => {
      const mockResults: SearchResult[] = [
        { id: 'r1', content: 'Content 1', score: 0.9, external_id: 'e1' },
        { id: 'r2', content: 'Content 2', score: 0.8, external_id: 'e2' },
        { id: 'r3', content: 'Content 3', score: 0.7, external_id: 'e3' },
        { id: 'r4', content: 'Content 4', score: 0.6, external_id: 'e4' },
        { id: 'r5', content: 'Content 5', score: 0.5, external_id: 'e5' },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ results: mockResults }),
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const results = await ai.search('collection1', 'Search query');

      expect(results).toHaveLength(5);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/rag/collections/collection1/search/',
        expect.objectContaining({
          body: JSON.stringify({
            query: 'Search query',
            top_k: 5,
          }),
        })
      );
    });

    it('should handle search with metadata', async () => {
      const mockResults: SearchResult[] = [
        {
          id: 'result1',
          content: 'Content with metadata',
          score: 0.92,
          external_id: 'doc1',
          metadata: { source: 'blog', date: '2024-01-01', author: 'John' },
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ results: mockResults }),
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const results = await ai.search('collection1', 'Query', 1);

      expect(results[0].metadata).toEqual({ source: 'blog', date: '2024-01-01', author: 'John' });
    });
  });

  describe('RAG query', () => {
    it('should perform RAG query', async () => {
      const mockResponse = {
        answer: 'OwnFirebase is a comprehensive backend platform offering database, authentication, cloud functions, storage, and AI capabilities. It supports real-time data synchronization and provides security rules for access control.',
        sources: [
          { id: 'doc1', score: 0.95 },
          { id: 'doc2', score: 0.87 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const result = await ai.ragQuery('collection1', 'What is OwnFirebase?');

      expect(result).toEqual(mockResponse);
      expect(result.answer).toBeDefined();
      expect(result.sources).toHaveLength(2);
    });

    it('should perform RAG query with custom options', async () => {
      const mockResponse = {
        answer: 'A detailed answer based on retrieved documents.',
        sources: [
          { id: 'source1', score: 0.98 },
          { id: 'source2', score: 0.85 },
          { id: 'source3', score: 0.72 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const result = await ai.ragQuery('collection1', 'Detailed question', {
        provider: 'anthropic',
        model: 'claude-opus',
        topK: 10,
      });

      expect(result.sources).toHaveLength(3);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/rag/collections/collection1/query/',
        expect.objectContaining({
          body: JSON.stringify({
            query: 'Detailed question',
            provider: 'anthropic',
            model: 'claude-opus',
            top_k: 10,
          }),
        })
      );
    });

    it('should support Google provider for RAG', async () => {
      const mockResponse = {
        answer: 'Answer from Gemini model.',
        sources: [{ id: 'doc1', score: 0.9 }],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const result = await ai.ragQuery('collection1', 'Question', {
        provider: 'google',
        model: 'gemini-pro',
      });

      expect(result.answer).toBeDefined();
    });

    it('should handle RAG query with no relevant sources', async () => {
      const mockResponse = {
        answer: 'I could not find sufficient information to answer your question.',
        sources: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const result = await ai.ragQuery('collection1', 'Obscure question');

      expect(result.sources).toHaveLength(0);
    });
  });

  describe('token usage tracking', () => {
    it('should track chat token usage', async () => {
      const mockCompletion: ChatCompletion = {
        content: 'Response',
        model: 'claude-haiku-4-5-20251001',
        provider: 'anthropic',
        usage: {
          prompt_tokens: 100,
          completion_tokens: 50,
          total_tokens: 150,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCompletion,
      });

      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      const result = await ai.chat([{ role: 'user', content: 'Test' }]);

      expect(result.usage).toEqual({
        prompt_tokens: 100,
        completion_tokens: 50,
        total_tokens: 150,
      });
    });

    it('should accumulate token usage over multiple calls', async () => {
      const ai = new AISDK(config);
      ai.setAccessToken('access-token');
      ai.setProjectId('test-project');

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            content: 'Response 1',
            model: 'claude-haiku-4-5-20251001',
            provider: 'anthropic',
            usage: { prompt_tokens: 50, completion_tokens: 25, total_tokens: 75 },
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            content: 'Response 2',
            model: 'claude-haiku-4-5-20251001',
            provider: 'anthropic',
            usage: { prompt_tokens: 60, completion_tokens: 30, total_tokens: 90 },
          }),
        });

      const result1 = await ai.chat([{ role: 'user', content: 'Q1' }]);
      const result2 = await ai.chat([{ role: 'user', content: 'Q2' }]);

      const totalTokens = result1.usage.total_tokens + result2.usage.total_tokens;
      expect(totalTokens).toBe(165);
    });
  });
});
