import { OwnFirebaseClient } from './client';
import type { PushDeviceToken, PushTopic, PaginatedResponse } from './types';

export interface PushNotificationPayload {
  title: string;
  body: string;
  data?: Record<string, string>;
  icon?: string;
  badge?: string;
}

export interface PushNotificationRecord {
  id: string;
  title: string;
  body: string;
  status: string;
  sent_at: string;
  recipient_count: number;
}

export class PushSDK extends OwnFirebaseClient {
  // ─── Device Tokens ───────────────────────────────────────────────────────────

  async registerToken(
    token: string,
    platform: 'ios' | 'android' | 'web'
  ): Promise<PushDeviceToken> {
    return this.request('POST', this.projectUrl('push/tokens/'), {
      token,
      platform,
    });
  }

  async listTokens(): Promise<PaginatedResponse<PushDeviceToken>> {
    return this.request('GET', this.projectUrl('push/tokens/'));
  }

  async deleteToken(id: string): Promise<void> {
    return this.request('DELETE', this.projectUrl(`push/tokens/${id}/`));
  }

  // ─── Topics ───────────────────────────────────────────────────────────────────

  async listTopics(): Promise<PaginatedResponse<PushTopic>> {
    return this.request('GET', this.projectUrl('push/topics/'));
  }

  async createTopic(name: string): Promise<PushTopic> {
    return this.request('POST', this.projectUrl('push/topics/'), { name });
  }

  async subscribeTopic(topicId: string): Promise<{ detail: string }> {
    return this.request(
      'POST',
      this.projectUrl(`push/topics/${topicId}/`),
      { action: 'subscribe' }
    );
  }

  // ─── Send Notifications ──────────────────────────────────────────────────────

  async sendToDevice(
    tokenId: string,
    notification: PushNotificationPayload
  ): Promise<PushNotificationRecord> {
    return this.request('POST', this.projectUrl('push/notifications/'), {
      target_type: 'device',
      target_id: tokenId,
      ...notification,
    });
  }

  async sendToTopic(
    topicId: string,
    notification: PushNotificationPayload
  ): Promise<PushNotificationRecord> {
    return this.request('POST', this.projectUrl('push/notifications/'), {
      target_type: 'topic',
      target_id: topicId,
      ...notification,
    });
  }

  async listNotifications(): Promise<PaginatedResponse<PushNotificationRecord>> {
    return this.request('GET', this.projectUrl('push/notifications/'));
  }

  // ─── Campaigns ───────────────────────────────────────────────────────────────

  async listCampaigns(): Promise<PaginatedResponse<PushNotificationRecord>> {
    return this.request('GET', this.projectUrl('push/campaigns/'));
  }

  async createCampaign(
    notification: PushNotificationPayload & {
      scheduled_at?: string;
      audience?: Record<string, unknown>;
    }
  ): Promise<PushNotificationRecord> {
    return this.request('POST', this.projectUrl('push/campaigns/'), notification);
  }
}
