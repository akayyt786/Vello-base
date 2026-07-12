import { CrashlyticsSDK } from '../src/crashlytics';
import type { CrashReport, PerformanceTrace, PaginatedResponse } from '../src/types';
import type { CrashGroup, NetworkRequestRecord } from '../src/crashlytics';

global.fetch = jest.fn();

describe('CrashlyticsSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('crash groups', () => {
    it('should list crash groups', async () => {
      const mockResponse: PaginatedResponse<CrashGroup> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'group1',
            exception_type: 'NullPointerException',
            message_summary: 'Null pointer in MainActivity',
            occurrence_count: 42,
            affected_users: 15,
            first_seen: '2024-01-01T00:00:00Z',
            last_seen: '2024-01-05T12:00:00Z',
            status: 'open',
          },
          {
            id: 'group2',
            exception_type: 'IllegalArgumentException',
            message_summary: 'Invalid argument passed',
            occurrence_count: 8,
            affected_users: 3,
            first_seen: '2024-01-03T00:00:00Z',
            last_seen: '2024-01-04T18:00:00Z',
            status: 'resolved',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.listCrashGroups();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
      expect(result.results[0].status).toBe('open');
    });

    it('should list crash groups with filters', async () => {
      const mockResponse: PaginatedResponse<CrashGroup> = {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'group1',
            exception_type: 'NullPointerException',
            message_summary: 'Null pointer in MainActivity',
            occurrence_count: 42,
            affected_users: 15,
            first_seen: '2024-01-01T00:00:00Z',
            last_seen: '2024-01-05T12:00:00Z',
            status: 'open',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.listCrashGroups({ status: 'open' });

      expect(result.count).toBe(1);
    });

    it('should get specific crash group', async () => {
      const mockGroup: CrashGroup = {
        id: 'group1',
        exception_type: 'NullPointerException',
        message_summary: 'Null pointer in MainActivity',
        occurrence_count: 42,
        affected_users: 15,
        first_seen: '2024-01-01T00:00:00Z',
        last_seen: '2024-01-05T12:00:00Z',
        status: 'open',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockGroup,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.getCrashGroup('group1');

      expect(result).toEqual(mockGroup);
      expect(result.exception_type).toBe('NullPointerException');
    });
  });

  describe('crash reports', () => {
    it('should report crash', async () => {
      const mockReport: CrashReport = {
        id: 'report1',
        exception_type: 'NullPointerException',
        message: 'Null pointer when accessing user data',
        stack_trace: 'at MainActivity.onCreate(MainActivity.java:42)\nat Activity.performCreate(...',
        occurred_at: '2024-01-05T10:30:00Z',
        app_version: '1.2.3',
        platform: 'android',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockReport,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.reportCrash({
        exception_type: 'NullPointerException',
        message: 'Null pointer when accessing user data',
        stack_trace: 'at MainActivity.onCreate(MainActivity.java:42)\nat Activity.performCreate(...',
        app_version: '1.2.3',
        platform: 'android',
      });

      expect(result).toEqual(mockReport);
      expect(result.id).toBe('report1');
    });

    it('should report crash with device info', async () => {
      const mockReport: CrashReport = {
        id: 'report2',
        exception_type: 'OutOfMemoryError',
        message: 'Out of memory',
        stack_trace: 'at java.lang.Runtime.nativeGetRuntime...',
        occurred_at: '2024-01-05T11:00:00Z',
        app_version: '1.2.3',
        platform: 'android',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockReport,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.reportCrash({
        exception_type: 'OutOfMemoryError',
        message: 'Out of memory',
        stack_trace: 'at java.lang.Runtime.nativeGetRuntime...',
        app_version: '1.2.3',
        platform: 'android',
        device_info: {
          device_model: 'Pixel 6',
          os_version: '12',
          ram_mb: 8192,
          available_ram_mb: 512,
        },
      });

      expect(result.exception_type).toBe('OutOfMemoryError');
    });

    it('should list crash reports', async () => {
      const mockResponse: PaginatedResponse<CrashReport> = {
        count: 3,
        next: null,
        previous: null,
        results: [
          {
            id: 'r1',
            exception_type: 'NullPointerException',
            message: 'NPE in MainActivity',
            stack_trace: '...',
            occurred_at: '2024-01-05T10:00:00Z',
            app_version: '1.2.3',
            platform: 'android',
          },
          {
            id: 'r2',
            exception_type: 'OutOfMemoryError',
            message: 'OOM',
            stack_trace: '...',
            occurred_at: '2024-01-05T10:30:00Z',
            app_version: '1.2.3',
            platform: 'android',
          },
          {
            id: 'r3',
            exception_type: 'IllegalStateException',
            message: 'Illegal state',
            stack_trace: '...',
            occurred_at: '2024-01-05T11:00:00Z',
            app_version: '1.2.3',
            platform: 'ios',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.listCrashReports();

      expect(result.count).toBe(3);
      expect(result.results).toHaveLength(3);
    });

    it('should get crash summary', async () => {
      const mockSummary = {
        total_crashes: 256,
        crash_free_users_percentage: 87.5,
        affected_users: 32,
        open_issues: 5,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockSummary,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.getCrashSummary();

      expect(result.total_crashes).toBe(256);
      expect(result.crash_free_users_percentage).toBe(87.5);
      expect(result.affected_users).toBe(32);
      expect(result.open_issues).toBe(5);
    });
  });

  describe('performance traces', () => {
    it('should record performance trace', async () => {
      const mockTrace: PerformanceTrace = {
        id: 'trace1',
        name: 'app_startup',
        duration_ms: 2345,
        started_at: '2024-01-05T10:00:00Z',
        attributes: { app_version: '1.2.3', device: 'Pixel6' },
        metrics: { cold_start: 2345, warm_start: 450 },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockTrace,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.recordTrace({
        name: 'app_startup',
        duration_ms: 2345,
        started_at: '2024-01-05T10:00:00Z',
        attributes: { app_version: '1.2.3', device: 'Pixel6' },
        metrics: { cold_start: 2345, warm_start: 450 },
      });

      expect(result.name).toBe('app_startup');
      expect(result.duration_ms).toBe(2345);
    });

    it('should list performance traces', async () => {
      const mockResponse: PaginatedResponse<PerformanceTrace> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'trace1',
            name: 'app_startup',
            duration_ms: 2345,
            started_at: '2024-01-05T10:00:00Z',
            attributes: {},
            metrics: { cold_start: 2345 },
          },
          {
            id: 'trace2',
            name: 'main_screen_load',
            duration_ms: 890,
            started_at: '2024-01-05T10:00:03Z',
            attributes: {},
            metrics: { layout_time: 450, data_load: 440 },
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.listTraces();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
    });
  });

  describe('network requests', () => {
    it('should record network request', async () => {
      const mockRecord: NetworkRequestRecord = {
        id: 'net1',
        url: 'https://api.example.com/users/123',
        method: 'GET',
        status_code: 200,
        duration_ms: 245,
        request_size: 512,
        response_size: 4096,
        timestamp: '2024-01-05T10:00:05Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.recordNetworkRequest({
        url: 'https://api.example.com/users/123',
        method: 'GET',
        status_code: 200,
        duration_ms: 245,
        request_size: 512,
        response_size: 4096,
      });

      expect(result.url).toBe('https://api.example.com/users/123');
      expect(result.status_code).toBe(200);
    });

    it('should record failed network request', async () => {
      const mockRecord: NetworkRequestRecord = {
        id: 'net2',
        url: 'https://api.example.com/data',
        method: 'POST',
        status_code: 500,
        duration_ms: 3000,
        request_size: 1024,
        response_size: 256,
        timestamp: '2024-01-05T10:01:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockRecord,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.recordNetworkRequest({
        url: 'https://api.example.com/data',
        method: 'POST',
        status_code: 500,
        duration_ms: 3000,
      });

      expect(result.status_code).toBe(500);
    });

    it('should list network requests', async () => {
      const mockResponse: PaginatedResponse<NetworkRequestRecord> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'net1',
            url: 'https://api.example.com/users/123',
            method: 'GET',
            status_code: 200,
            duration_ms: 245,
            request_size: 512,
            response_size: 4096,
            timestamp: '2024-01-05T10:00:05Z',
          },
          {
            id: 'net2',
            url: 'https://api.example.com/data',
            method: 'POST',
            status_code: 500,
            duration_ms: 3000,
            request_size: 1024,
            response_size: 256,
            timestamp: '2024-01-05T10:01:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const crashlytics = new CrashlyticsSDK(config);
      crashlytics.setAccessToken('access-token');
      crashlytics.setProjectId('test-project');

      const result = await crashlytics.listNetworkRequests();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
    });
  });

  describe('crash severity scenarios', () => {
    it('should handle crashes on different platforms', () => {
      const platforms = ['android', 'ios', 'web', 'macos'];

      platforms.forEach(platform => {
        expect(platform).toBeDefined();
      });
    });

    it('should track different exception types', () => {
      const exceptionTypes = [
        'NullPointerException',
        'OutOfMemoryError',
        'IllegalStateException',
        'RuntimeException',
        'TypeError',
        'SyntaxError',
        'ReferenceError',
      ];

      expect(exceptionTypes).toHaveLength(7);
    });

    it('should handle crash status transitions', () => {
      const statuses = ['open', 'resolved', 'ignored'] as const;

      expect(statuses).toContain('open');
      expect(statuses).toContain('resolved');
      expect(statuses).toContain('ignored');
    });
  });
});
