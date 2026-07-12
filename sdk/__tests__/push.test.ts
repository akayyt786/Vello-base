import { PushSDK } from '../src/push';
import type { PushDeviceToken, PushTopic, PaginatedResponse } from '../src/types';
import type { PushNotificationPayload, PushNotificationRecord, PushTopicSubscription } from '../src/push';

global.fetch = jest.fn();

describe('PushSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('device tokens', () => {
    it('should register device token', async () => {
      const mockToken: PushDeviceToken = {
        id: 'token1',
        token: 'fcm-token-abc123',
        platform: 'fcm',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockToken,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.registerToken('fcm-token-abc123', 'fcm');

      expect(result).toEqual(mockToken);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/push/tokens/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            token: 'fcm-token-abc123',
            platform: 'fcm',
          }),
        })
      );
    });

    it('should register iOS (APNs) token', async () => {
      const mockToken: PushDeviceToken = {
        id: 'token2',
        token: 'apns-token-xyz789',
        platform: 'apns',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockToken,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.registerToken('apns-token-xyz789', 'apns');

      expect(result).toEqual(mockToken);
    });

    it('should register web token', async () => {
      const mockToken: PushDeviceToken = {
        id: 'token3',
        token: 'web-token-web123',
        platform: 'web',
        is_active: true,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockToken,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.registerToken('web-token-web123', 'web');

      expect(result.platform).toBe('web');
    });

    it('should list device tokens', async () => {
      const mockResponse: PaginatedResponse<PushDeviceToken> = {
        count: 3,
        next: null,
        previous: null,
        results: [
          { id: 'token1', token: 'fcm-token-abc123', platform: 'fcm', is_active: true },
          { id: 'token2', token: 'apns-token-xyz789', platform: 'apns', is_active: true },
          { id: 'token3', token: 'web-token-web123', platform: 'web', is_active: false },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.listTokens();

      expect(result.count).toBe(3);
      expect(result.results).toHaveLength(3);
      expect(result.results[0].platform).toBe('fcm');
    });

    it('should delete device token', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.deleteToken('token1');

      expect(result).toBeUndefined();
    });
  });

  describe('topics', () => {
    it('should list topics', async () => {
      const mockResponse: PaginatedResponse<PushTopic> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          { id: 'topic1', name: 'news', subscriber_count: 100 },
          { id: 'topic2', name: 'promotions', subscriber_count: 250 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.listTopics();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
      expect(result.results[0].name).toBe('news');
    });

    it('should create topic', async () => {
      const mockTopic: PushTopic = {
        id: 'topic3',
        name: 'updates',
        subscriber_count: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockTopic,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.createTopic('updates');

      expect(result).toEqual(mockTopic);
      expect(result.name).toBe('updates');
    });

    it('should subscribe to topic', async () => {
      const mockResponse: PushTopicSubscription = {
        id: 'sub1',
        topic: 'topic1',
        device_token: 'token1',
        created_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockResponse,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.subscribeTopic('topic1', 'token1');

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/push/topics/topic1/subscribe/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ device_token_id: 'token1' }),
        })
      );
    });
  });

  describe('send notifications', () => {
    it('should send notification to device', async () => {
      const mockRecord: PushNotificationRecord = {
        id: 'notif1',
        title: 'Hello',
        body: 'Welcome to OwnFirebase',
        status: 'sent',
        sent_at: '2024-01-01T00:00:00Z',
        recipient_count: 1,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const payload: PushNotificationPayload = {
        title: 'Hello',
        body: 'Welcome to OwnFirebase',
      };

      const result = await push.sendToDevice('token1', payload);

      expect(result).toEqual(mockRecord);
      expect(result.recipient_count).toBe(1);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/push/notifications/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            device_token: 'token1',
            title: 'Hello',
            body: 'Welcome to OwnFirebase',
          }),
        })
      );
    });

    it('should send notification with custom data', async () => {
      const mockRecord: PushNotificationRecord = {
        id: 'notif2',
        title: 'Promo',
        body: 'Special offer available',
        status: 'sent',
        sent_at: '2024-01-01T00:01:00Z',
        recipient_count: 1,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const payload: PushNotificationPayload = {
        title: 'Promo',
        body: 'Special offer available',
        data: {
          promo_code: 'SAVE20',
          link: 'https://example.com/promo',
        },
      };

      const result = await push.sendToDevice('token1', payload);

      expect(result.title).toBe('Promo');
    });

    it('should send notification to topic', async () => {
      const mockRecord: PushNotificationRecord = {
        id: 'notif3',
        title: 'News Update',
        body: 'Breaking news story',
        status: 'sent',
        sent_at: '2024-01-01T00:02:00Z',
        recipient_count: 150,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const payload: PushNotificationPayload = {
        title: 'News Update',
        body: 'Breaking news story',
      };

      const result = await push.sendToTopic('topic1', payload);

      expect(result.recipient_count).toBe(150);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/push/notifications/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            topic: 'topic1',
            title: 'News Update',
            body: 'Breaking news story',
          }),
        })
      );
    });

    it('should send notification with icon and badge', async () => {
      const mockRecord: PushNotificationRecord = {
        id: 'notif4',
        title: 'Message',
        body: 'New message received',
        status: 'sent',
        sent_at: '2024-01-01T00:03:00Z',
        recipient_count: 1,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const payload: PushNotificationPayload = {
        title: 'Message',
        body: 'New message received',
        icon: 'https://example.com/icon.png',
        badge: 'https://example.com/badge.png',
      };

      const result = await push.sendToDevice('token1', payload);

      expect(result).toBeDefined();
    });

    it('should list notifications', async () => {
      const mockResponse: PaginatedResponse<PushNotificationRecord> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'notif1',
            title: 'Notif 1',
            body: 'Body 1',
            status: 'sent',
            sent_at: '2024-01-01T00:00:00Z',
            recipient_count: 1,
          },
          {
            id: 'notif2',
            title: 'Notif 2',
            body: 'Body 2',
            status: 'sent',
            sent_at: '2024-01-01T00:01:00Z',
            recipient_count: 150,
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.listNotifications();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
    });
  });

  describe('campaigns', () => {
    it('should list campaigns', async () => {
      const mockResponse: PaginatedResponse<PushNotificationRecord> = {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'campaign1',
            title: 'Summer Campaign',
            body: 'Great deals this summer',
            status: 'scheduled',
            sent_at: '2024-06-01T00:00:00Z',
            recipient_count: 0,
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const result = await push.listCampaigns();

      expect(result.count).toBe(1);
      expect(result.results[0].title).toBe('Summer Campaign');
    });

    it('should create campaign with scheduling', async () => {
      const mockRecord: PushNotificationRecord = {
        id: 'campaign2',
        title: 'Scheduled Campaign',
        body: 'This campaign is scheduled',
        status: 'scheduled',
        sent_at: '2024-06-15T10:00:00Z',
        recipient_count: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const campaign = {
        title: 'Scheduled Campaign',
        body: 'This campaign is scheduled',
        scheduled_at: '2024-06-15T10:00:00Z',
        audience: { region: 'US' },
      };

      const result = await push.createCampaign(campaign);

      expect(result.status).toBe('scheduled');
    });

    it('should create campaign with audience targeting', async () => {
      const mockRecord: PushNotificationRecord = {
        id: 'campaign3',
        title: 'Targeted Campaign',
        body: 'Campaign for specific audience',
        status: 'scheduled',
        sent_at: '2024-06-20T00:00:00Z',
        recipient_count: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const push = new PushSDK(config);
      push.setAccessToken('access-token');
      push.setProjectId('test-project');

      const campaign = {
        title: 'Targeted Campaign',
        body: 'Campaign for specific audience',
        audience: {
          regions: ['US', 'CA'],
          user_properties: {
            subscription_tier: 'premium',
          },
          min_app_version: '1.0.0',
        },
      };

      const result = await push.createCampaign(campaign);

      expect(result.title).toBe('Targeted Campaign');
    });
  });
});
