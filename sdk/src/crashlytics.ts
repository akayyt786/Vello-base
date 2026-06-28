import { OwnFirebaseClient } from './client';
import type { CrashReport, PerformanceTrace, PaginatedResponse } from './types';

export interface CrashGroup {
  id: string;
  exception_type: string;
  message_summary: string;
  occurrence_count: number;
  affected_users: number;
  first_seen: string;
  last_seen: string;
  status: 'open' | 'resolved' | 'ignored';
}

export interface NetworkRequestRecord {
  id: string;
  url: string;
  method: string;
  status_code: number;
  duration_ms: number;
  request_size: number;
  response_size: number;
  timestamp: string;
}

export class CrashlyticsSDK extends OwnFirebaseClient {
  // ─── Crash Groups ────────────────────────────────────────────────────────────

  async listCrashGroups(
    filters?: Record<string, string>
  ): Promise<PaginatedResponse<CrashGroup>> {
    return this.request(
      'GET',
      this.projectUrl('crashlytics/groups/'),
      undefined,
      { query: filters }
    );
  }

  async getCrashGroup(id: string): Promise<CrashGroup> {
    return this.request('GET', this.projectUrl(`crashlytics/groups/${id}/`));
  }

  // ─── Crash Reports ───────────────────────────────────────────────────────────

  async reportCrash(report: {
    exception_type: string;
    message: string;
    stack_trace: string;
    app_version: string;
    platform: string;
    device_info?: Record<string, unknown>;
  }): Promise<CrashReport> {
    return this.request('POST', this.projectUrl('crashlytics/reports/'), report);
  }

  async listCrashReports(
    filters?: Record<string, string>
  ): Promise<PaginatedResponse<CrashReport>> {
    return this.request(
      'GET',
      this.projectUrl('crashlytics/reports/'),
      undefined,
      { query: filters }
    );
  }

  async getCrashSummary(): Promise<{
    total_crashes: number;
    crash_free_users_percentage: number;
    affected_users: number;
    open_issues: number;
  }> {
    return this.request('GET', this.projectUrl('crashlytics/summary/'));
  }

  // ─── Performance Traces ──────────────────────────────────────────────────────

  async recordTrace(trace: {
    name: string;
    duration_ms: number;
    started_at: string;
    attributes?: Record<string, string>;
    metrics?: Record<string, number>;
  }): Promise<PerformanceTrace> {
    return this.request('POST', this.projectUrl('crashlytics/traces/'), trace);
  }

  async listTraces(
    filters?: Record<string, string>
  ): Promise<PaginatedResponse<PerformanceTrace>> {
    return this.request(
      'GET',
      this.projectUrl('crashlytics/traces/'),
      undefined,
      { query: filters }
    );
  }

  // ─── Network Requests ────────────────────────────────────────────────────────

  async recordNetworkRequest(record: {
    url: string;
    method: string;
    status_code: number;
    duration_ms: number;
    request_size?: number;
    response_size?: number;
  }): Promise<NetworkRequestRecord> {
    return this.request(
      'POST',
      this.projectUrl('crashlytics/network/'),
      record
    );
  }

  async listNetworkRequests(
    filters?: Record<string, string>
  ): Promise<PaginatedResponse<NetworkRequestRecord>> {
    return this.request(
      'GET',
      this.projectUrl('crashlytics/network/'),
      undefined,
      { query: filters }
    );
  }
}
