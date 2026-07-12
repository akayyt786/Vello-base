import { StorageSDK } from '../src/storage';
import type { StorageObject, StorageUploadUrl, PaginatedResponse } from '../src/types';

global.fetch = jest.fn();

describe('StorageSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('upload operations', () => {
    it('should get upload URL', async () => {
      const mockResponse: StorageUploadUrl = {
        file_id: 'file-123',
        upload_url: 'https://minio.example.com/upload-presigned-url?token=abc123',
        method: 'PUT',
        expires_in: 3600,
        path: 'document.pdf',
        bucket: 'test-project-bucket',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.getUploadUrl({
        path: 'document.pdf',
        contentType: 'application/pdf',
      });

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/storage/upload-url/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            path: 'document.pdf',
            content_type: 'application/pdf',
            size: undefined,
            metadata: undefined,
          }),
        })
      );
    });

    it('should get upload URL with nested path', async () => {
      const mockResponse: StorageUploadUrl = {
        file_id: 'file-456',
        upload_url: 'https://minio.example.com/upload-presigned-url?token=xyz789',
        method: 'PUT',
        expires_in: 3600,
        path: 'user-123/documents/report.pdf',
        bucket: 'test-project-bucket',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.getUploadUrl({
        path: 'user-123/documents/report.pdf',
        contentType: 'application/pdf',
      });

      expect(result.path).toContain('user-123/documents');
    });

    it('should confirm upload', async () => {
      const mockFile: StorageObject = {
        id: 'obj1',
        name: 'document.pdf',
        size: 102400,
        content_type: 'application/pdf',
        url: 'https://storage.example.com/uploads/file-123/document.pdf',
        created_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockFile,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.confirmUpload('file-123');

      expect(result).toEqual(mockFile);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/storage/confirm/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ file_id: 'file-123' }),
        })
      );
    });

    it('should upload file with helper method', async () => {
      const mockUploadUrl: StorageUploadUrl = {
        file_id: 'file-123',
        upload_url: 'https://minio.example.com/upload?token=abc123',
        method: 'PUT',
        expires_in: 3600,
        path: 'uploads/photo.jpg',
        bucket: 'test-project-bucket',
      };

      const mockFile: StorageObject = {
        id: 'obj2',
        name: 'photo.jpg',
        size: 51200,
        content_type: 'image/jpeg',
        url: 'https://storage.example.com/uploads/file-123/photo.jpg',
        created_at: '2024-01-01T00:01:00Z',
      };

      // First call: getUploadUrl
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockUploadUrl,
      });

      // Second call: PUT to presigned URL
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
      });

      // Third call: confirmUpload
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockFile,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const fileBlob = new Blob(['photo data'], { type: 'image/jpeg' });
      const result = await storage.upload(fileBlob, {
        path: 'uploads/photo.jpg',
        contentType: 'image/jpeg',
      });

      expect(result).toEqual(mockFile);
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should handle upload failure', async () => {
      const mockUploadUrl: StorageUploadUrl = {
        file_id: 'file-123',
        upload_url: 'https://minio.example.com/upload?token=abc123',
        method: 'PUT',
        expires_in: 3600,
        path: 'uploads/photo.jpg',
        bucket: 'test-project-bucket',
      };

      // First call: getUploadUrl
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockUploadUrl,
      });

      // Second call: PUT fails
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const fileBlob = new Blob(['photo data'], { type: 'image/jpeg' });

      try {
        await storage.upload(fileBlob, {
          path: 'uploads/photo.jpg',
          contentType: 'image/jpeg',
        });
        fail('Should have thrown error');
      } catch (err: any) {
        expect(err.message).toContain('Upload to presigned URL failed');
        expect(err.message).toContain('403');
      }
    });
  });

  describe('file operations', () => {
    it('should list files', async () => {
      const mockResponse: PaginatedResponse<StorageObject> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'obj1',
            name: 'document.pdf',
            size: 102400,
            content_type: 'application/pdf',
            url: 'https://storage.example.com/uploads/document.pdf',
            created_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'obj2',
            name: 'photo.jpg',
            size: 51200,
            content_type: 'image/jpeg',
            url: 'https://storage.example.com/uploads/photo.jpg',
            created_at: '2024-01-01T00:01:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.listFiles();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
    });

    it('should list files with prefix filter', async () => {
      const mockResponse: PaginatedResponse<StorageObject> = {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'obj3',
            name: 'user-123/profile.jpg',
            size: 25600,
            content_type: 'image/jpeg',
            url: 'https://storage.example.com/user-123/profile.jpg',
            created_at: '2024-01-01T00:02:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.listFiles('user-123/');

      expect(result.count).toBe(1);
      const callUrl = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(callUrl).toContain('prefix=user-123%2F');
    });

    it('should get file metadata', async () => {
      const mockFile: StorageObject = {
        id: 'obj1',
        name: 'document.pdf',
        size: 102400,
        content_type: 'application/pdf',
        url: 'https://storage.example.com/uploads/document.pdf',
        created_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockFile,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.getFile('uploads/document.pdf');

      expect(result).toEqual(mockFile);
      expect(result.size).toBe(102400);
    });

    it('should delete file', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.deleteFile('uploads/document.pdf');

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/storage/files/uploads/document.pdf/',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should handle multiple file types', async () => {
      const mockResponse: PaginatedResponse<StorageObject> = {
        count: 3,
        next: null,
        previous: null,
        results: [
          {
            id: 'obj1',
            name: 'document.pdf',
            size: 102400,
            content_type: 'application/pdf',
            url: 'https://storage.example.com/document.pdf',
            created_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'obj2',
            name: 'image.png',
            size: 204800,
            content_type: 'image/png',
            url: 'https://storage.example.com/image.png',
            created_at: '2024-01-01T00:01:00Z',
          },
          {
            id: 'obj3',
            name: 'data.json',
            size: 1024,
            content_type: 'application/json',
            url: 'https://storage.example.com/data.json',
            created_at: '2024-01-01T00:02:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const storage = new StorageSDK(config);
      storage.setAccessToken('access-token');
      storage.setProjectId('test-project');

      const result = await storage.listFiles();

      expect(result.count).toBe(3);
      expect(result.results.map(f => f.content_type)).toContain('application/pdf');
      expect(result.results.map(f => f.content_type)).toContain('image/png');
      expect(result.results.map(f => f.content_type)).toContain('application/json');
    });
  });
});
