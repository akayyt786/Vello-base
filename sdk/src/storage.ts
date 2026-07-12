import { OwnFirebaseClient } from './client';
import type { StorageObject, StorageUploadUrl, PaginatedResponse } from './types';

export class StorageSDK extends OwnFirebaseClient {
  /**
   * Request a presigned upload URL from MinIO/S3 for direct browser upload.
   */
  async getUploadUrl(options: {
    path: string;
    contentType?: string;
    size?: number;
    metadata?: Record<string, unknown>;
  }): Promise<StorageUploadUrl> {
    return this.request('POST', this.projectUrl('storage/upload-url/'), {
      path: options.path,
      content_type: options.contentType,
      size: options.size,
      metadata: options.metadata,
    });
  }

  /**
   * Confirm a direct upload after the client has PUT to the presigned URL.
   */
  async confirmUpload(fileId: string): Promise<StorageObject> {
    return this.request('POST', this.projectUrl('storage/confirm/'), {
      file_id: fileId,
    });
  }

  async listFiles(prefix?: string): Promise<PaginatedResponse<StorageObject>> {
    const query: Record<string, string> = {};
    if (prefix) query['prefix'] = prefix;
    return this.request(
      'GET',
      this.projectUrl('storage/files/'),
      undefined,
      { query }
    );
  }

  async getFile(path: string): Promise<StorageObject> {
    return this.request('GET', this.projectUrl(`storage/files/${path}/`));
  }

  async deleteFile(path: string): Promise<void> {
    return this.request('DELETE', this.projectUrl(`storage/files/${path}/`));
  }

  /**
   * High-level helper: request an upload URL, PUT the file, then confirm.
   * Only works in environments with fetch + Blob support (browsers, Deno, Node 18+).
   */
  async upload(
    file: Blob | Buffer | ArrayBuffer,
    options: {
      path: string;
      contentType?: string;
      size?: number;
      metadata?: Record<string, unknown>;
    }
  ): Promise<StorageObject> {
    const { upload_url, file_id } = await this.getUploadUrl(options);

    const putResponse = await fetch(upload_url, {
      method: 'PUT',
      headers: options.contentType ? { 'Content-Type': options.contentType } : undefined,
      body: file as any,
    });

    if (!putResponse.ok) {
      throw new Error(
        `Upload to presigned URL failed: ${putResponse.status} ${putResponse.statusText}`
      );
    }

    return this.confirmUpload(file_id);
  }
}
