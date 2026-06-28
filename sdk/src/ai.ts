import { OwnFirebaseClient } from './client';
import type { ChatMessage, ChatCompletion, SearchResult } from './types';

export class AISDK extends OwnFirebaseClient {
  /**
   * Send a chat completion request.
   * Routes to Anthropic (Claude) or Google (Gemini) based on `provider`.
   */
  async chat(
    messages: ChatMessage[],
    options?: {
      provider?: 'anthropic' | 'google';
      model?: string;
      maxTokens?: number;
      temperature?: number;
      system?: string;
    }
  ): Promise<ChatCompletion> {
    return this.request('POST', this.projectUrl('ai/chat/'), {
      messages,
      provider: options?.provider ?? 'anthropic',
      model: options?.model ?? 'claude-haiku-4-5-20251001',
      max_tokens: options?.maxTokens ?? 1024,
      temperature: options?.temperature ?? 0.7,
      system: options?.system,
    });
  }

  /**
   * Semantic search over a RAG vector collection.
   */
  async search(
    collectionId: string,
    query: string,
    topK = 5
  ): Promise<SearchResult[]> {
    const resp = await this.request<{ results: SearchResult[] }>(
      'POST',
      this.projectUrl(`rag/collections/${collectionId}/search/`),
      { query, top_k: topK }
    );
    return resp.results;
  }

  /**
   * Retrieval-augmented generation: search the vector collection then synthesize an answer.
   */
  async ragQuery(
    collectionId: string,
    query: string,
    options?: {
      provider?: 'anthropic' | 'google';
      model?: string;
      topK?: number;
    }
  ): Promise<{ answer: string; sources: Array<{ id: string; score: number }> }> {
    return this.request(
      'POST',
      this.projectUrl(`rag/collections/${collectionId}/query/`),
      {
        query,
        provider: options?.provider ?? 'anthropic',
        model: options?.model ?? 'claude-haiku-4-5-20251001',
        top_k: options?.topK ?? 5,
      }
    );
  }
}
