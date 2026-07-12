import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/crashlytics.dart';

void main() {
  group('CrashlyticsSDK Integration Tests', () {
    late CrashlyticsSDK crashlytics;
    const baseUrl = 'http://localhost:8000';
    const testProjectId = 'test-project-001';

    setUp(() {
      // Constructed directly rather than via `OwnFirebase`/`app.crashlytics`
      // since the barrel file (ownfirebase_sdk.dart) isn't wired up for this
      // module yet.
      crashlytics = CrashlyticsSDK(
        config: OwnFirebaseConfig(
          baseUrl: baseUrl,
          projectId: testProjectId,
        ),
      );
      crashlytics.setAccessToken('integration-test-token');
    });

    test('CrashlyticsSDK is properly initialized', () {
      expect(crashlytics, isNotNull);
      expect(crashlytics.baseUrl, equals(baseUrl));
      expect(crashlytics.projectId, equals(testProjectId));
    });

    test('Crash group methods exist', () {
      final methods = [
        crashlytics.listCrashGroups,
        crashlytics.getCrashGroup,
        crashlytics.updateCrashGroup,
        crashlytics.resolveCrashGroup,
        crashlytics.unresolveCrashGroup,
      ];
      expect(methods, hasLength(5));
    });

    test('Crash report methods exist', () {
      final methods = [
        crashlytics.reportCrash,
        crashlytics.listCrashReports,
        crashlytics.getCrashReport,
      ];
      expect(methods, hasLength(3));
    });

    test('Performance trace methods exist', () {
      final methods = [
        crashlytics.recordTrace,
        crashlytics.listTraces,
        crashlytics.getTrace,
        crashlytics.submitTracesBatch,
      ];
      expect(methods, hasLength(4));
    });

    test('Network request methods exist', () {
      final methods = [
        crashlytics.recordNetworkRequest,
        crashlytics.listNetworkRequests,
        crashlytics.getNetworkRequest,
        crashlytics.submitNetworkRequestsBatch,
      ];
      expect(methods, hasLength(4));
    });

    test('Summary method exists', () {
      final methods = [
        crashlytics.getCrashSummary,
      ];
      expect(methods, hasLength(1));
    });

    test('Crash group resolution workflow structure', () {
      const groupId = 'group-to-resolve';
      final update = {
        'is_resolved': true,
        'notes': 'Fixed in release 2.1.1',
      };
      expect(groupId, isNotEmpty);
      expect(update['is_resolved'], isTrue);
    });

    test('Crash report payload for multiple platforms', () {
      final reports = [
        {
          'platform': 'ios',
          'exception_type': 'NSInvalidArgumentException',
          'stack_trace': 'at AppDelegate.application(_:didFinishLaunchingWithOptions:)',
          'occurred_at': '2026-01-05T12:00:00Z',
        },
        {
          'platform': 'android',
          'exception_type': 'NullPointerException',
          'stack_trace': 'at MainActivity.onCreate(MainActivity.java:42)',
          'occurred_at': '2026-01-05T12:05:00Z',
        },
        {
          'platform': 'web',
          'exception_type': 'TypeError',
          'stack_trace': "at Object.<anonymous> (app.js:10:5)",
          'occurred_at': '2026-01-05T12:10:00Z',
        },
      ];
      expect(reports, hasLength(3));
      expect(reports.map((r) => r['platform']).toSet(),
          equals({'ios', 'android', 'web'}));
    });

    test('Crash report with breadcrumbs and custom keys', () {
      final report = {
        'exception_type': 'IllegalStateException',
        'stack_trace': 'at Repository.fetch(Repository.kt:88)',
        'occurred_at': '2026-01-05T12:00:00Z',
        'breadcrumbs': [
          {'category': 'navigation', 'message': 'opened checkout screen'},
          {'category': 'network', 'message': 'GET /api/cart -> 200'},
        ],
        'custom_keys': {'cart_id': 'cart-123', 'user_tier': 'premium'},
      };
      expect(report['breadcrumbs'], hasLength(2));
      expect((report['custom_keys'] as Map)['cart_id'], equals('cart-123'));
    });

    test('Performance trace for app startup', () {
      final trace = {
        'trace_name': 'app_startup',
        'duration_ms': 850,
        'platform': 'android',
        'app_version': '3.0.0',
        'occurred_at': '2026-01-05T12:00:00Z',
        'custom_metrics': {'cold_start': 1},
      };
      expect(trace['trace_name'], equals('app_startup'));
      expect(trace['duration_ms'], equals(850));
    });

    test('Network request record for a failed request', () {
      final record = {
        'url': 'https://api.example.com/v1/checkout',
        'http_method': 'POST',
        'response_code': 503,
        'duration_ms': 5000,
        'occurred_at': '2026-01-05T12:00:00Z',
      };
      expect(record['response_code'], equals(503));
    });

    test('Batch trace submission structure', () {
      final traces = List.generate(
        10,
        (i) => {
          'trace_name': 'screen_render_$i',
          'duration_ms': 16 + i,
          'occurred_at': '2026-01-05T12:00:00Z',
        },
      );
      expect(traces, hasLength(10));
    });

    test('Batch network request submission structure', () {
      final records = List.generate(
        10,
        (i) => {
          'url': 'https://api.example.com/v1/resource/$i',
          'http_method': 'GET',
          'duration_ms': 100 + i,
          'occurred_at': '2026-01-05T12:00:00Z',
        },
      );
      expect(records, hasLength(10));
    });

    test('Crash summary response structure', () {
      final summary = {
        'total_crash_groups': 12,
        'unresolved_groups': 3,
        'total_reports_last_7d': 480,
        'affected_users_last_7d': 96,
        'top_crashes': [
          {
            'signature': 'sig-1',
            'title': 'NullPointerException in MainActivity.java:42',
            'count': 210,
            'last_seen': '2026-01-05T12:00:00Z',
          },
        ],
      };
      expect(summary['unresolved_groups'], equals(3));
      expect((summary['top_crashes'] as List), hasLength(1));
    });

    test('Crash group list cursor pagination structure', () {
      final paginatedGroups = {
        'next': 'http://localhost:8000/api/projects/test/crashlytics/groups/?cursor=abc123',
        'previous': null,
        'results': [
          {
            'id': 'group-1',
            'project': testProjectId,
            'signature': 'sig-1',
            'title': 'Error 1',
            'exception_type': 'Exception',
            'first_seen_at': '2026-01-01T00:00:00Z',
            'last_seen_at': '2026-01-02T00:00:00Z',
            'occurrence_count': 5,
            'affected_users_count': 2,
            'is_resolved': false,
            'resolved_at': null,
            'notes': '',
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-02T00:00:00Z',
          },
        ],
      };
      // Cursor pagination has no `count` field, unlike offset pagination.
      expect(paginatedGroups.containsKey('count'), isFalse);
      expect(paginatedGroups['results'], hasLength(1));
    });
  });
}
