import { DataSDK } from '../src/data';
import type { DataDocument, DataCollection, PaginatedResponse, WriteBatchOperation, WriteBatchResult } from '../src/types';

global.fetch = jest.fn();

describe('DataSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('collections', () => {
    it('should list all collections', async () => {
      const mockCollections: DataCollection[] = [
        { id: 'col1', name: 'users', document_count: 10 },
        { id: 'col2', name: 'posts', document_count: 25 },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCollections,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.listCollections();

      expect(result).toEqual(mockCollections);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/collections/',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should create new collection', async () => {
      const mockCollection: DataCollection = {
        id: 'col3',
        name: 'products',
        document_count: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockCollection,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.createCollection('products');

      expect(result).toEqual(mockCollection);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/collections/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'products' }),
        })
      );
    });
  });

  describe('documents - read', () => {
    it('should list documents in collection', async () => {
      const mockResponse: PaginatedResponse<DataDocument> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'doc1',
            collection: 'users',
            data: { name: 'John', email: 'john@example.com' },
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'doc2',
            collection: 'users',
            data: { name: 'Jane', email: 'jane@example.com' },
            created_at: '2024-01-02T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.listDocuments('users');

      expect(result).toEqual(mockResponse);
      expect(result.results).toHaveLength(2);
      expect(result.count).toBe(2);
    });

    it('should list documents with filters', async () => {
      const mockResponse: PaginatedResponse<DataDocument> = {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'doc1',
            collection: 'users',
            data: { name: 'John', status: 'active' },
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const filters = { status: 'active' };
      const result = await data.listDocuments('users', filters);

      expect(result.results).toHaveLength(1);
      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('status=active');
    });

    it('should get single document', async () => {
      const mockDocument: DataDocument = {
        id: 'doc1',
        collection: 'users',
        data: { name: 'John', email: 'john@example.com' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockDocument,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.getDocument('users', 'doc1');

      expect(result).toEqual(mockDocument);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/collections/users/docs/doc1/',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should get document with subcollection path', async () => {
      const mockDocument: DataDocument = {
        id: 'post1',
        collection: 'users/uid/posts',
        data: { title: 'My Post' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockDocument,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.getDocument('users/uid/posts', 'post1');

      expect(result).toEqual(mockDocument);
    });
  });

  describe('documents - create', () => {
    it('should create document', async () => {
      const mockDocument: DataDocument = {
        id: 'doc-new',
        collection: 'users',
        data: { name: 'Bob', email: 'bob@example.com' },
        created_at: '2024-01-03T00:00:00Z',
        updated_at: '2024-01-03T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockDocument,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const docData = { name: 'Bob', email: 'bob@example.com' };
      const result = await data.createDocument('users', docData);

      expect(result).toEqual(mockDocument);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/collections/users/docs/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ data: docData }),
        })
      );
    });

    it('should create document with complex nested data', async () => {
      const complexData = {
        name: 'Complex',
        metadata: {
          tags: ['tag1', 'tag2'],
          nested: {
            value: 123,
          },
        },
        active: true,
      };

      const mockDocument: DataDocument = {
        id: 'doc-complex',
        collection: 'items',
        data: complexData,
        created_at: '2024-01-03T00:00:00Z',
        updated_at: '2024-01-03T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockDocument,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.createDocument('items', complexData);

      expect(result.data).toEqual(complexData);
    });
  });

  describe('documents - update', () => {
    it('should update document (PATCH)', async () => {
      const mockDocument: DataDocument = {
        id: 'doc1',
        collection: 'users',
        data: { name: 'John Updated', email: 'john@example.com' },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-04T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockDocument,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const updateData = { name: 'John Updated' };
      const result = await data.updateDocument('users', 'doc1', updateData);

      expect(result).toEqual(mockDocument);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/collections/users/docs/doc1/',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ data: updateData }),
        })
      );
    });

    it('should replace document (PUT)', async () => {
      const mockDocument: DataDocument = {
        id: 'doc1',
        collection: 'users',
        data: { name: 'John Replaced', age: 30 },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-04T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockDocument,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const replaceData = { name: 'John Replaced', age: 30 };
      const result = await data.replaceDocument('users', 'doc1', replaceData);

      expect(result).toEqual(mockDocument);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/collections/users/docs/doc1/',
        expect.objectContaining({
          method: 'PUT',
        })
      );
    });
  });

  describe('documents - delete', () => {
    it('should delete document', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.deleteDocument('users', 'doc1');

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/collections/users/docs/doc1/',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('batch operations', () => {
    it('should perform write batch', async () => {
      const mockResult: WriteBatchResult = {
        written: 3,
        errors: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResult,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');

      const operations: WriteBatchOperation[] = [
        {
          op: 'set',
          collection: 'users',
          doc_id: 'doc1',
          data: { name: 'John' },
        },
        {
          op: 'update',
          collection: 'users',
          doc_id: 'doc2',
          data: { name: 'Jane Updated' },
        },
        {
          op: 'delete',
          collection: 'users',
          doc_id: 'doc3',
        },
      ];

      const result = await data.writeBatch(operations);

      expect(result).toEqual(mockResult);
      expect(result.written).toBe(3);
      expect(result.errors).toHaveLength(0);
    });

    it('should handle batch with errors', async () => {
      const mockResult: WriteBatchResult = {
        written: 1,
        errors: [
          { operation: 1, error: 'Document not found' },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResult,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');

      const operations: WriteBatchOperation[] = [
        { op: 'set', collection: 'users', doc_id: 'doc1', data: { name: 'John' } },
        { op: 'update', collection: 'users', doc_id: 'nonexistent', data: { name: 'Jane' } },
      ];

      const result = await data.writeBatch(operations);

      expect(result.written).toBe(1);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should handle complex batch with multiple collections', async () => {
      const mockResult: WriteBatchResult = {
        written: 5,
        errors: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResult,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');

      const operations: WriteBatchOperation[] = [
        { op: 'set', collection: 'users', doc_id: 'u1', data: { name: 'User 1' } },
        { op: 'set', collection: 'posts', doc_id: 'p1', data: { title: 'Post 1' } },
        { op: 'set', collection: 'users/u1/comments', doc_id: 'c1', data: { text: 'Comment' } },
        { op: 'update', collection: 'users', doc_id: 'u1', data: { updated: true } },
        { op: 'delete', collection: 'posts', doc_id: 'p2' },
      ];

      const result = await data.writeBatch(operations);

      expect(result.written).toBe(5);
    });
  });

  describe('security rules', () => {
    it('should get security rules', async () => {
      const mockRules = { rules: 'rules_version = "2";\nmatch /databases/{database}/documents { match /{document=**} { allow read, write: if true; } }' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockRules,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.getRules();

      expect(result.rules).toBeDefined();
    });

    it('should update security rules', async () => {
      const newRules = 'rules_version = "2";\nmatch /databases/{database}/documents { match /users/{uid} { allow read: if true; } }';
      const mockResponse = { rules: newRules };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const result = await data.updateRules(newRules);

      expect(result.rules).toBe(newRules);
    });

    it('should test security rules', async () => {
      const mockResponse = { allowed: true, reason: 'Rule condition matched' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const data = new DataSDK(config);
      data.setAccessToken('access-token');
      const testContext = { user: { uid: 'user123' }, path: 'users/user123' };
      const result = await data.testRules('allow read: if true;', testContext);

      expect(result.allowed).toBe(true);
    });
  });
});
