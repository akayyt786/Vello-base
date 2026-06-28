import type { OwnFirebaseConfig, APIError } from './types';

export class OwnFirebaseClient {
  protected baseUrl: string;
  protected projectId: string | undefined;
  protected accessToken: string | undefined;

  constructor(config: OwnFirebaseConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.projectId = config.projectId;
    this.accessToken = config.accessToken;
  }

  setAccessToken(token: string): void {
    this.accessToken = token;
  }

  setProjectId(id: string): void {
    this.projectId = id;
  }

  protected projectUrl(path: string): string {
    if (!this.projectId) {
      throw new Error('projectId is required for this operation');
    }
    return `${this.baseUrl}/api/projects/${this.projectId}/${path}`;
  }

  async request<T>(
    method: string,
    url: string,
    body?: unknown,
    options?: { noAuth?: boolean; query?: Record<string, string> }
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (!options?.noAuth && this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    let fullUrl = url;
    if (options?.query) {
      const params = new URLSearchParams(options.query);
      fullUrl += `?${params.toString()}`;
    }

    const response = await fetch(fullUrl, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      let detail: unknown;
      try {
        detail = await response.json();
      } catch {
        detail = await response.text();
      }
      const err: APIError = {
        status: response.status,
        message: response.statusText,
        detail,
      };
      throw err;
    }

    if (response.status === 204) return undefined as unknown as T;
    return response.json() as Promise<T>;
  }
}
