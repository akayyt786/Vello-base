import { AnalyticsSDK } from '../src/analytics';
import type { AnalyticsEvent, UserProperty, PaginatedResponse } from '../src/types';

global.fetch = jest.fn();

describe('AnalyticsSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('events', () => {
    it('should log analytics event', async () => {
      const mockEvent: AnalyticsEvent = {
        id: 'event1',
        name: 'user_signup',
        params: { source: 'mobile', campaign: 'summer2024' },
        timestamp: '2024-01-01T00:00:00Z',
        user_id: 'user123',
        session_id: 'session123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockEvent,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.logEvent('user_signup', { source: 'mobile', campaign: 'summer2024' }, {
        userId: 'user123',
        sessionId: 'session123',
      });

      expect(result).toEqual(mockEvent);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/analytics/events/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            name: 'user_signup',
            params: { source: 'mobile', campaign: 'summer2024' },
            user_id: 'user123',
            session_id: 'session123',
          }),
        })
      );
    });

    it('should log event without optional params', async () => {
      const mockEvent: AnalyticsEvent = {
        id: 'event2',
        name: 'page_view',
        params: {},
        timestamp: '2024-01-01T00:01:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockEvent,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.logEvent('page_view');

      expect(result).toEqual(mockEvent);
    });

    it('should log event with complex parameters', async () => {
      const mockEvent: AnalyticsEvent = {
        id: 'event3',
        name: 'purchase',
        params: {
          value: 99.99,
          currency: 'USD',
          items: ['item1', 'item2'],
          metadata: { promo_code: 'SUMMER2024' },
        },
        timestamp: '2024-01-01T00:02:00Z',
        user_id: 'user123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockEvent,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const params = {
        value: 99.99,
        currency: 'USD',
        items: ['item1', 'item2'],
        metadata: { promo_code: 'SUMMER2024' },
      };

      const result = await analytics.logEvent('purchase', params, { userId: 'user123' });

      expect(result.params).toEqual(params);
    });

    it('should list analytics events', async () => {
      const mockResponse: PaginatedResponse<AnalyticsEvent> = {
        count: 3,
        next: null,
        previous: null,
        results: [
          {
            id: 'event1',
            name: 'user_signup',
            params: { source: 'web' },
            timestamp: '2024-01-01T00:00:00Z',
            user_id: 'user123',
          },
          {
            id: 'event2',
            name: 'page_view',
            params: {},
            timestamp: '2024-01-01T00:01:00Z',
            user_id: 'user123',
          },
          {
            id: 'event3',
            name: 'button_click',
            params: { button_id: 'btn_subscribe' },
            timestamp: '2024-01-01T00:02:00Z',
            user_id: 'user123',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.listEvents();

      expect(result.count).toBe(3);
      expect(result.results).toHaveLength(3);
    });

    it('should list events with filters', async () => {
      const mockResponse: PaginatedResponse<AnalyticsEvent> = {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'event1',
            name: 'user_signup',
            params: { source: 'web' },
            timestamp: '2024-01-01T00:00:00Z',
            user_id: 'user123',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.listEvents({ name: 'user_signup' });

      expect(result.results).toHaveLength(1);
    });
  });

  describe('user properties', () => {
    it('should set user property', async () => {
      const mockProperty: UserProperty = {
        id: 'prop1',
        name: 'subscription_tier',
        value: 'premium',
        user_id: 'user123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockProperty,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.setUserProperty('subscription_tier', 'premium');

      expect(result).toEqual(mockProperty);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/analytics/user-properties/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            name: 'subscription_tier',
            value: 'premium',
          }),
        })
      );
    });

    it('should list user properties', async () => {
      const mockResponse: PaginatedResponse<UserProperty> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'prop1',
            name: 'subscription_tier',
            value: 'premium',
            user_id: 'user123',
          },
          {
            id: 'prop2',
            name: 'region',
            value: 'US',
            user_id: 'user123',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.listUserProperties();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
    });
  });

  describe('conversion events', () => {
    it('should list conversion events', async () => {
      const mockResponse: PaginatedResponse<{ id: string; name: string }> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          { id: 'conv1', name: 'purchase' },
          { id: 'conv2', name: 'signup' },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.listConversionEvents();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
    });

    it('should mark conversion event', async () => {
      const mockResponse = { id: 'conv3', name: 'newsletter_signup' };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockResponse,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.markConversionEvent('newsletter_signup');

      expect(result).toEqual(mockResponse);
    });
  });

  describe('analytics query', () => {
    it('should query analytics with metric', async () => {
      const mockResult = {
        metric: 'sessions',
        rows: [
          { date: '2024-01-01', metric_value: 100 },
          { date: '2024-01-02', metric_value: 150 },
          { date: '2024-01-03', metric_value: 120 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResult,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.query({
        metric: 'sessions',
        start_date: '2024-01-01',
        end_date: '2024-01-03',
      });

      expect(result.metric).toBe('sessions');
      expect(result.rows).toHaveLength(3);
      expect(result.rows[0].metric_value).toBe(100);
    });

    it('should query analytics with dimension', async () => {
      const mockResult = {
        metric: 'events',
        dimension: 'event_name',
        rows: [
          { dimension_value: 'page_view', metric_value: 250 },
          { dimension_value: 'button_click', metric_value: 180 },
          { dimension_value: 'form_submit', metric_value: 45 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResult,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.query({
        metric: 'events',
        dimension: 'event_name',
      });

      expect(result.dimension).toBe('event_name');
      expect(result.rows).toHaveLength(3);
      expect(result.rows[0].dimension_value).toBe('page_view');
    });

    it('should query analytics with filters', async () => {
      const mockResult = {
        metric: 'active_users',
        rows: [{ metric_value: 500 }],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResult,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.query({
        metric: 'active_users',
        filters: { country: 'US' },
      });

      expect(result.rows[0].metric_value).toBe(500);
    });

    it('should handle complex analytics query', async () => {
      const mockResult = {
        metric: 'revenue',
        dimension: 'currency',
        rows: [
          { dimension_value: 'USD', metric_value: 10000, date: '2024-01-01' },
          { dimension_value: 'EUR', metric_value: 8500, date: '2024-01-01' },
          { dimension_value: 'USD', metric_value: 12000, date: '2024-01-02' },
          { dimension_value: 'EUR', metric_value: 9200, date: '2024-01-02' },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResult,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.query({
        metric: 'revenue',
        dimension: 'currency',
        start_date: '2024-01-01',
        end_date: '2024-01-02',
        filters: { platform: 'ios' },
      });

      expect(result.metric).toBe('revenue');
      expect(result.dimension).toBe('currency');
      expect(result.rows).toHaveLength(4);
    });
  });

  describe('analytics batching scenarios', () => {
    it('should handle rapid event logging', async () => {
      const mockEvent: AnalyticsEvent = {
        id: 'event1',
        name: 'test_event',
        params: {},
        timestamp: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => mockEvent,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      // Simulate rapid event logging
      const promises = [];
      for (let i = 0; i < 10; i++) {
        promises.push(analytics.logEvent(`event_${i}`, { index: i }));
      }

      const results = await Promise.all(promises);

      expect(results).toHaveLength(10);
      expect(global.fetch).toHaveBeenCalledTimes(10);
    });

    it('should handle event logging with user and session context', async () => {
      const mockEvent: AnalyticsEvent = {
        id: 'event1',
        name: 'user_event',
        params: { action: 'click' },
        timestamp: '2024-01-01T00:00:00Z',
        user_id: 'user123',
        session_id: 'session-abc-123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockEvent,
      });

      const analytics = new AnalyticsSDK(config);
      analytics.setAccessToken('access-token');
      analytics.setProjectId('test-project');

      const result = await analytics.logEvent(
        'user_event',
        { action: 'click' },
        { userId: 'user123', sessionId: 'session-abc-123' }
      );

      expect(result.user_id).toBe('user123');
      expect(result.session_id).toBe('session-abc-123');
    });
  });
});
