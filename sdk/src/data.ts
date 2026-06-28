import { OwnFirebaseClient } from './client';
import type {
  DataDocument,
  DataCollection,
  PaginatedResponse,
  WriteBatchOperation,
  WriteBatchResult,
} from './types';

export class DataSDK extends OwnFirebaseClient {
  // ─── Collections ─────────────────────────────────────────────────────────────

  async listCollections(): Promise<DataCollection[]> {
    return this.request('GET', this.projectUrl('collections/'));
  }

  async createCollection(name: string): Promise<DataCollection> {
    return this.request('POST', this.projectUrl('collections/'), { name });
  }

  // ─── Documents ────────────────────────────────────────────────────────────────

  /**
   * List documents in a collection. The `collection` param supports
   * subcollection paths using forward slashes (e.g. "users/uid/posts").
   */
  async listDocuments(
    collection: string,
    filters?: Record<string, string>
  ): Promise<PaginatedResponse<DataDocument>> {
    return this.request(
      'GET',
      this.projectUrl(`collections/${collection}/docs/`),
      undefined,
      { query: filters }
    );
  }

  async getDocument(collection: string, docId: string): Promise<DataDocument> {
    return this.request(
      'GET',
      this.projectUrl(`collections/${collection}/docs/${docId}/`)
    );
  }

  async createDocument(
    collection: string,
    data: Record<string, unknown>
  ): Promise<DataDocument> {
    return this.request(
      'POST',
      this.projectUrl(`collections/${collection}/docs/`),
      { data }
    );
  }

  async updateDocument(
    collection: string,
    docId: string,
    data: Record<string, unknown>
  ): Promise<DataDocument> {
    return this.request(
      'PATCH',
      this.projectUrl(`collections/${collection}/docs/${docId}/`),
      { data }
    );
  }

  async replaceDocument(
    collection: string,
    docId: string,
    data: Record<string, unknown>
  ): Promise<DataDocument> {
    return this.request(
      'PUT',
      this.projectUrl(`collections/${collection}/docs/${docId}/`),
      { data }
    );
  }

  async deleteDocument(collection: string, docId: string): Promise<void> {
    return this.request(
      'DELETE',
      this.projectUrl(`collections/${collection}/docs/${docId}/`)
    );
  }

  // ─── Batch / Transactions ─────────────────────────────────────────────────────

  async writeBatch(operations: WriteBatchOperation[]): Promise<WriteBatchResult> {
    return this.request('POST', this.projectUrl('transaction/'), {
      operations,
    });
  }

  // ─── Security Rules ───────────────────────────────────────────────────────────

  async getRules(): Promise<{ rules: string }> {
    return this.request('GET', `${this.baseUrl}/api/v1/rules/`);
  }

  async updateRules(rules: string): Promise<{ rules: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/rules/`, { rules });
  }

  async testRules(
    rule: string,
    context: Record<string, unknown>
  ): Promise<{ allowed: boolean; reason?: string }> {
    return this.request('POST', `${this.baseUrl}/api/v1/rules/test/`, {
      rule,
      context,
    });
  }
}
