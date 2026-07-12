import { OwnFirebaseClient } from './client';
import type { AnalyticsEvent, UserProperty, PaginatedResponse } from './types';

export interface AnalyticsQueryParams {
  metric: string;
  dimension?: string;
  start_date?: string;
  end_date?: string;
  filters?: Record<string, string>;
}

export interface AnalyticsQueryResult {
  metric: string;
  dimension?: string;
  rows: Array<{ dimension_value?: string; metric_value: number; date?: string }>;
}

export interface BatchEventParams {
  name: string;
  params?: Record<string, unknown>;
  userId?: string;
  sessionId?: string;
}

export class AnalyticsSDK extends OwnFirebaseClient {
  private eventBatch: BatchEventParams[] = [];
  private batchTimeout: NodeJS.Timeout | null = null;
  private readonly batchMaxSize = 100;
  private readonly batchMaxDelayMs = 5000;

  // ─── Events ──────────────────────────────────────────────────────────────────

  async logEvent(
    name: string,
    params?: Record<string, unknown>,
    options?: { userId?: string; sessionId?: string }
  ): Promise<AnalyticsEvent> {
    return this.request('POST', this.projectUrl('analytics/events/'), {
      name,
      params: params ?? {},
      user_id: options?.userId,
      session_id: options?.sessionId,
    });
  }

  /**
   * Add an event to the batch queue. Events are sent in bulk after a delay or when batch is full.
   */
  addEventToBatch(
    name: string,
    params?: Record<string, unknown>,
    options?: { userId?: string; sessionId?: string }
  ): void {
    this.eventBatch.push({
      name,
      params,
      userId: options?.userId,
      sessionId: options?.sessionId,
    });

    // Send immediately if batch is full
    if (this.eventBatch.length >= this.batchMaxSize) {
      this.flushBatch();
    } else if (!this.batchTimeout) {
      // Schedule flush after delay
      this.batchTimeout = setTimeout(() => {
        this.flushBatch();
      }, this.batchMaxDelayMs);
    }
  }

  /**
   * Send all batched events to the server.
   */
  async flushBatch(): Promise<void> {
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }

    if (this.eventBatch.length === 0) {
      return;
    }

    const batch = this.eventBatch.splice(0, this.eventBatch.length);
    try {
      await this.request('POST', this.projectUrl('analytics/events/batch/'), {
        events: batch,
      });
    } catch (error) {
      // Re-add failed events to batch for retry
      this.eventBatch.unshift(...batch);
      throw error;
    }
  }

  async listEvents(
    filters?: Record<string, string>
  ): Promise<PaginatedResponse<AnalyticsEvent>> {
    return this.request(
      'GET',
      this.projectUrl('analytics/events/'),
      undefined,
      { query: filters }
    );
  }

  // ─── User Properties ─────────────────────────────────────────────────────────

  async setUserProperty(name: string, value: string): Promise<UserProperty> {
    return this.request('POST', this.projectUrl('analytics/user-properties/'), {
      name,
      value,
    });
  }

  async listUserProperties(): Promise<PaginatedResponse<UserProperty>> {
    return this.request('GET', this.projectUrl('analytics/user-properties/'));
  }

  // ─── Conversion Events ───────────────────────────────────────────────────────

  async listConversionEvents(): Promise<PaginatedResponse<{ id: string; name: string }>> {
    return this.request('GET', this.projectUrl('analytics/conversion-events/'));
  }

  async markConversionEvent(name: string): Promise<{ id: string; name: string }> {
    return this.request(
      'POST',
      this.projectUrl('analytics/conversion-events/'),
      { name }
    );
  }

  // ─── Query ───────────────────────────────────────────────────────────────────

  async query(params: AnalyticsQueryParams): Promise<AnalyticsQueryResult> {
    return this.request('POST', this.projectUrl('analytics/query/'), params);
  }

  /**
   * Clean up batch timer on SDK teardown.
   */
  destroy(): void {
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }
  }
}
