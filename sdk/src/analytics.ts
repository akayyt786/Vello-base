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

export class AnalyticsSDK extends OwnFirebaseClient {
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
}
