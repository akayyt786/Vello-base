import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/crashlytics.dart';

void main() {
  group('CrashlyticsSDK Unit Tests (Mocked)', () {
    late CrashlyticsSDK crashlytics;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      crashlytics = CrashlyticsSDK(config: config);
    });

    test('CrashlyticsSDK initializes with config', () {
      expect(crashlytics.baseUrl, equals('http://localhost:8000'));
      expect(crashlytics.projectId, equals('test-project'));
    });

    test('CrashGroup.fromJson parses correctly', () {
      final json = {
        'id': 'group-123',
        'project': 'proj-1',
        'signature': 'abc123def456',
        'title': 'NullPointerException in MainActivity.java:42',
        'exception_type': 'NullPointerException',
        'first_seen_at': '2026-01-01T00:00:00Z',
        'last_seen_at': '2026-01-05T12:00:00Z',
        'occurrence_count': 42,
        'affected_users_count': 7,
        'is_resolved': false,
        'resolved_at': null,
        'notes': '',
        'created_at': '2026-01-01T00:00:00Z',
        'updated_at': '2026-01-05T12:00:00Z',
      };
      final group = CrashGroup.fromJson(json);
      expect(group.id, equals('group-123'));
      expect(group.signature, equals('abc123def456'));
      expect(group.exceptionType, equals('NullPointerException'));
      expect(group.occurrenceCount, equals(42));
      expect(group.affectedUsersCount, equals(7));
      expect(group.isResolved, isFalse);
      expect(group.resolvedAt, isNull);
    });

    test('CrashGroup.fromJson handles resolved group', () {
      final json = {
        'id': 'group-456',
        'project': 'proj-1',
        'signature': 'xyz789',
        'title': 'IOException in NetworkClient.java:10',
        'exception_type': 'IOException',
        'first_seen_at': '2026-01-01T00:00:00Z',
        'last_seen_at': '2026-01-02T00:00:00Z',
        'occurrence_count': 3,
        'affected_users_count': 1,
        'is_resolved': true,
        'resolved_at': '2026-01-03T00:00:00Z',
        'notes': 'Fixed in v1.2.3',
        'created_at': '2026-01-01T00:00:00Z',
        'updated_at': '2026-01-03T00:00:00Z',
      };
      final group = CrashGroup.fromJson(json);
      expect(group.isResolved, isTrue);
      expect(group.resolvedAt, equals('2026-01-03T00:00:00Z'));
      expect(group.notes, equals('Fixed in v1.2.3'));
    });

    test('CrashReport.fromJson parses correctly', () {
      final json = {
        'id': 'report-1',
        'project': 'proj-1',
        'group': 'group-123',
        'user_id': 'user-1',
        'session_id': 'session-1',
        'platform': 'ios',
        'app_version': '2.1.0',
        'os_version': '17.2',
        'device_model': 'iPhone15,3',
        'exception_type': 'NullPointerException',
        'exception_message': 'Attempt to invoke method on a null object',
        'stack_trace': 'at MainActivity.onCreate(MainActivity.java:42)',
        'fatal': true,
        'breadcrumbs': [
          {'timestamp': '2026-01-05T11:59:00Z', 'category': 'navigation', 'message': 'opened home screen'},
        ],
        'custom_keys': {'user_tier': 'premium'},
        'occurred_at': '2026-01-05T12:00:00Z',
        'created_at': '2026-01-05T12:00:01Z',
      };
      final report = CrashReport.fromJson(json);
      expect(report.id, equals('report-1'));
      expect(report.group, equals('group-123'));
      expect(report.platform, equals('ios'));
      expect(report.fatal, isTrue);
      expect(report.breadcrumbs, hasLength(1));
      expect(report.customKeys['user_tier'], equals('premium'));
    });

    test('CrashReport.fromJson handles ungrouped report with defaults', () {
      final json = {
        'id': 'report-2',
        'project': 'proj-1',
        'group': null,
        'platform': 'android',
        'exception_type': 'RuntimeException',
        'stack_trace': 'at Foo.bar(Foo.java:1)',
        'fatal': false,
        'breadcrumbs': [],
        'custom_keys': {},
        'occurred_at': '2026-01-05T12:00:00Z',
        'created_at': '2026-01-05T12:00:01Z',
      };
      final report = CrashReport.fromJson(json);
      expect(report.group, isNull);
      expect(report.userId, equals(''));
      expect(report.sessionId, equals(''));
      expect(report.exceptionMessage, equals(''));
      expect(report.fatal, isFalse);
      expect(report.breadcrumbs, isEmpty);
      expect(report.customKeys, isEmpty);
    });

    test('PerformanceTrace.fromJson parses correctly', () {
      final json = {
        'id': 'trace-1',
        'project': 'proj-1',
        'trace_name': 'api_call',
        'duration_ms': 350,
        'user_id': 'user-1',
        'session_id': 'session-1',
        'platform': 'web',
        'app_version': '2.1.0',
        'custom_attributes': {'endpoint': '/api/v1/data'},
        'custom_metrics': {'bytes_downloaded': 1024},
        'occurred_at': '2026-01-05T12:00:00Z',
        'created_at': '2026-01-05T12:00:01Z',
      };
      final trace = PerformanceTrace.fromJson(json);
      expect(trace.traceName, equals('api_call'));
      expect(trace.durationMs, equals(350));
      expect(trace.customAttributes['endpoint'], equals('/api/v1/data'));
      expect(trace.customMetrics['bytes_downloaded'], equals(1024));
    });

    test('NetworkRequestRecord.fromJson parses correctly', () {
      final json = {
        'id': 'net-1',
        'project': 'proj-1',
        'url': 'https://api.example.com/v1/users',
        'http_method': 'GET',
        'response_code': 200,
        'request_size_bytes': 128,
        'response_size_bytes': 4096,
        'duration_ms': 220,
        'user_id': 'user-1',
        'session_id': 'session-1',
        'platform': 'android',
        'app_version': '2.1.0',
        'occurred_at': '2026-01-05T12:00:00Z',
        'created_at': '2026-01-05T12:00:01Z',
      };
      final record = NetworkRequestRecord.fromJson(json);
      expect(record.url, equals('https://api.example.com/v1/users'));
      expect(record.httpMethod, equals('GET'));
      expect(record.responseCode, equals(200));
      expect(record.requestSizeBytes, equals(128));
      expect(record.responseSizeBytes, equals(4096));
    });

    test('NetworkRequestRecord.fromJson handles null response_code', () {
      final json = {
        'id': 'net-2',
        'project': 'proj-1',
        'url': 'https://api.example.com/v1/timeout',
        'http_method': 'POST',
        'response_code': null,
        'request_size_bytes': 64,
        'response_size_bytes': 0,
        'duration_ms': 30000,
        'user_id': '',
        'session_id': '',
        'platform': 'web',
        'app_version': '',
        'occurred_at': '2026-01-05T12:00:00Z',
        'created_at': '2026-01-05T12:00:01Z',
      };
      final record = NetworkRequestRecord.fromJson(json);
      expect(record.responseCode, isNull);
      expect(record.responseSizeBytes, equals(0));
    });

    test('CrashSummary.fromJson parses correctly', () {
      final json = {
        'total_crash_groups': 15,
        'unresolved_groups': 4,
        'total_reports_last_7d': 230,
        'affected_users_last_7d': 58,
        'top_crashes': [
          {
            'signature': 'abc123',
            'title': 'NullPointerException in MainActivity.java:42',
            'count': 120,
            'last_seen': '2026-01-05T12:00:00Z',
          },
        ],
      };
      final summary = CrashSummary.fromJson(json);
      expect(summary.totalCrashGroups, equals(15));
      expect(summary.unresolvedGroups, equals(4));
      expect(summary.totalReportsLast7d, equals(230));
      expect(summary.affectedUsersLast7d, equals(58));
      expect(summary.topCrashes, hasLength(1));
      expect(summary.topCrashes.first.signature, equals('abc123'));
      expect(summary.topCrashes.first.count, equals(120));
    });

    test('CrashSummary.fromJson handles empty top_crashes', () {
      final json = {
        'total_crash_groups': 0,
        'unresolved_groups': 0,
        'total_reports_last_7d': 0,
        'affected_users_last_7d': 0,
        'top_crashes': [],
      };
      final summary = CrashSummary.fromJson(json);
      expect(summary.topCrashes, isEmpty);
    });

    test('Cursor-paginated list response has no count field', () {
      final response = {
        'next': 'http://localhost:8000/api/projects/test/crashlytics/groups/?cursor=abc',
        'previous': null,
        'results': [
          {
            'id': 'group-1',
            'project': 'proj-1',
            'signature': 'sig-1',
            'title': 'Error 1',
            'exception_type': 'Exception',
            'first_seen_at': '2026-01-01T00:00:00Z',
            'last_seen_at': '2026-01-02T00:00:00Z',
            'occurrence_count': 1,
            'affected_users_count': 1,
            'is_resolved': false,
            'resolved_at': null,
            'notes': '',
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-02T00:00:00Z',
          },
        ],
      };
      expect(response.containsKey('count'), isFalse);
      final results = (response['results'] as List)
          .map((item) => CrashGroup.fromJson(item as Map<String, dynamic>))
          .toList();
      final page = CrashlyticsPaginatedResponse<CrashGroup>(
        next: response['next'] as String?,
        previous: response['previous'] as String?,
        results: results,
      );
      expect(page.results, hasLength(1));
      expect(page.next, isNotNull);
      expect(page.previous, isNull);
    });

    test('Crash report submission payload structure', () {
      final payload = {
        'exception_type': 'IllegalStateException',
        'stack_trace': 'at Foo.bar(Foo.kt:10)',
        'occurred_at': '2026-01-05T12:00:00Z',
        'platform': 'android',
        'fatal': true,
      };
      expect(payload['exception_type'], equals('IllegalStateException'));
      expect(payload['fatal'], isTrue);
    });

    test('Batch trace submission payload caps at 500 items', () {
      final traces = List.generate(
        500,
        (i) => {
          'trace_name': 'trace-$i',
          'duration_ms': 100 + i,
          'occurred_at': '2026-01-05T12:00:00Z',
        },
      );
      expect(traces, hasLength(500));
      final overLimit = [...traces, traces.first];
      expect(overLimit.length > 500, isTrue);
    });

    test('Batch network request submission payload caps at 500 items', () {
      final records = List.generate(
        500,
        (i) => {
          'url': 'https://example.com/$i',
          'http_method': 'GET',
          'duration_ms': 100 + i,
          'occurred_at': '2026-01-05T12:00:00Z',
        },
      );
      expect(records, hasLength(500));
      final overLimit = [...records, records.first];
      expect(overLimit.length > 500, isTrue);
    });

    test('submitTracesBatch rejects batches over 500 items', () {
      final overLimit = List.generate(
        501,
        (i) => {
          'trace_name': 'trace-$i',
          'duration_ms': 100,
          'occurred_at': '2026-01-05T12:00:00Z',
        },
      );
      // The size guard runs before any network call, so the returned Future
      // rejects synchronously with ArgumentError — no live server needed.
      expect(crashlytics.submitTracesBatch(overLimit), throwsArgumentError);
    });

    test('submitNetworkRequestsBatch rejects batches over 500 items', () {
      final overLimit = List.generate(
        501,
        (i) => {
          'url': 'https://example.com/$i',
          'http_method': 'GET',
          'duration_ms': 100,
          'occurred_at': '2026-01-05T12:00:00Z',
        },
      );
      expect(crashlytics.submitNetworkRequestsBatch(overLimit), throwsArgumentError);
    });
  });
}
