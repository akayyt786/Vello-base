import type { OwnFirebaseConfig, APIError } from './types';
import { OwnFirebaseError } from './errors';

export interface RequestOptions {
  noAuth?: boolean;
  query?: Record<string, string>;
  retries?: number;
  timeout?: number;
}

export class OwnFirebaseClient {
  protected baseUrl: string;
  protected projectId: string | undefined;
  protected accessToken: string | undefined;
  protected retryConfig = {
    maxRetries: 3,
    initialDelayMs: 100,
    maxDelayMs: 5000,
  };

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

  private shouldRetry(status: number, attempt: number): boolean {
    // Retry on 5xx errors, 429 (rate limit), and 408 (timeout)
    // But not on 4xx errors (except 408 and 429)
    if (status >= 500) return true;
    if (status === 429 || status === 408) return true;
    return false;
  }

  private getRetryDelay(attempt: number): number {
    const delay = Math.min(
      this.retryConfig.initialDelayMs * Math.pow(2, attempt),
      this.retryConfig.maxDelayMs
    );
    // Add jitter: ±10% of delay
    return delay + (Math.random() - 0.5) * delay * 0.2;
  }

  async request<T>(
    method: string,
    url: string,
    body?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    const maxRetries = options?.retries ?? this.retryConfig.maxRetries;
    let lastError: unknown;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await this.makeRequest<T>(method, url, body, options);
      } catch (error) {
        lastError = error;

        // Check if we should retry
        let shouldRetry = false;
        if (error instanceof OwnFirebaseError) {
          shouldRetry = this.shouldRetry(error.status, attempt);
        } else if (error && typeof error === 'object' && 'status' in error) {
          shouldRetry = this.shouldRetry((error as APIError).status, attempt);
        }

        if (!shouldRetry || attempt === maxRetries) {
          throw error;
        }

        // Wait before retrying
        const delay = this.getRetryDelay(attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError;
  }

  private async makeRequest<T>(
    method: string,
    url: string,
    body?: unknown,
    options?: RequestOptions
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

    const controller = new AbortController();
    const timeoutMs = options?.timeout ?? 30000;
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(fullUrl, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
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
        throw OwnFirebaseError.fromAPIError(err);
      }

      if (response.status === 204) return undefined as unknown as T;
      return response.json() as Promise<T>;
    } catch (error) {
      // Handle abort (timeout)
      if (error instanceof Error && error.name === 'AbortError') {
        const err: APIError = {
          status: 408,
          message: 'Request timeout',
          detail: `Request to ${url} timed out after ${timeoutMs}ms`,
        };
        throw OwnFirebaseError.fromAPIError(err);
      }
      // Re-throw if already OwnFirebaseError
      if (error instanceof OwnFirebaseError) {
        throw error;
      }
      // Wrap other errors
      if (error instanceof Error) {
        throw new OwnFirebaseError(error.message, 'NETWORK_ERROR', 0, error);
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }
}
