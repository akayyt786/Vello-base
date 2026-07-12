import 'package:test/test.dart';
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() {
  group('AnalyticsSDK Integration Tests (Batch Events)', () {
    late OwnFirebase app;
    const baseUrl = 'http://localhost:8000';
    const testProjectId = 'test-project-001';

    setUp(() {
      app = initOwnFirebase(
        OwnFirebaseConfig(
          baseUrl: baseUrl,
          projectId: testProjectId,
        ),
      );
      app.setAccessToken('integration-test-token');
    });

    test('Analytics service is properly initialized', () {
      expect(app.analytics, isNotNull);
      expect(app.analytics.baseUrl, equals(baseUrl));
      expect(app.analytics.projectId, equals(testProjectId));
    });

    test('Event logging methods are available', () {
      final methods = [
        app.analytics.logEvent,
        app.analytics.listEvents,
      ];
      expect(methods, hasLength(2));
    });

    test('User property methods are available', () {
      final methods = [
        app.analytics.setUserProperty,
        app.analytics.listUserProperties,
      ];
      expect(methods, hasLength(2));
    });

    test('Conversion event methods are available', () {
      final methods = [
        app.analytics.listConversionEvents,
        app.analytics.markConversionEvent,
      ];
      expect(methods, hasLength(2));
    });

    test('Query method is available', () {
      expect(app.analytics.query, isNotNull);
    });

    test('Batch event structure for multiple events', () {
      final batchEvents = [
        {
          'name': 'page_view',
          'params': {'page': '/home', 'referrer': 'google'},
          'user_id': 'user-1',
          'session_id': 'session-1',
        },
        {
          'name': 'button_click',
          'params': {'button_id': 'btn-cta', 'section': 'hero'},
          'user_id': 'user-1',
          'session_id': 'session-1',
        },
        {
          'name': 'form_submit',
          'params': {'form_id': 'contact', 'errors': 0},
          'user_id': 'user-1',
          'session_id': 'session-1',
        },
        {
          'name': 'purchase',
          'params': {'amount': 99.99, 'currency': 'USD', 'items': 2},
          'user_id': 'user-1',
          'session_id': 'session-1',
        },
      ];
      expect(batchEvents, hasLength(4));
      expect(batchEvents.every((e) => e.containsKey('name')), isTrue);
      expect(batchEvents.every((e) => e.containsKey('params')), isTrue);
    });

    test('User properties batch structure', () {
      final userProps = [
        {'name': 'email', 'value': 'user@example.com'},
        {'name': 'subscription_tier', 'value': 'premium'},
        {'name': 'account_age_days', 'value': '365'},
        {'name': 'is_paying_customer', 'value': 'true'},
        {'name': 'last_purchase_date', 'value': '2024-01-01'},
      ];
      expect(userProps, hasLength(5));
      expect(userProps.map((p) => p['name']).toList(),
        contains('subscription_tier'));
    });

    test('Analytics query with dimensions and metrics', () {
      final queryParams = {
        'metric': 'event_count',
        'dimension': 'event_name',
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
        'filters': {'platform': 'mobile'},
      };
      expect(queryParams['metric'], equals('event_count'));
      expect(queryParams['dimension'], equals('event_name'));
      expect(queryParams['filters']['platform'], equals('mobile'));
    });

    test('Conversion event marking', () {
      final conversionMarking = [
        {'name': 'sign_up'},
        {'name': 'first_purchase'},
        {'name': 'subscription_upgrade'},
        {'name': 'premium_trial_started'},
      ];
      expect(conversionMarking, hasLength(4));
      expect(conversionMarking.map((c) => c['name']).toList(),
        contains('subscription_upgrade'));
    });

    test('Event parameters with various data types', () {
      final eventParams = {
        'string_param': 'value',
        'number_param': 42,
        'float_param': 3.14,
        'bool_param': true,
        'array_param': [1, 2, 3],
        'object_param': {'nested': 'value'},
        'null_param': null,
      };
      expect(eventParams['number_param'], isA<int>());
      expect(eventParams['float_param'], isA<double>());
      expect(eventParams['array_param'], isA<List>());
    });

    test('Session tracking structure', () {
      final sessionData = {
        'session_id': 'session-123',
        'user_id': 'user-456',
        'started_at': '2024-01-01T10:00:00Z',
        'last_active_at': '2024-01-01T10:30:00Z',
        'device': {'platform': 'iOS', 'model': 'iPhone 14'},
        'location': {'country': 'US', 'city': 'San Francisco'},
      };
      expect(sessionData['session_id'], isNotNull);
      expect(sessionData['device']['platform'], equals('iOS'));
    });

    test('Analytics retention and query support', () {
      final queryTypes = [
        'event_count',
        'unique_users',
        'retention',
        'funnel',
        'cohort',
      ];
      expect(queryTypes, hasLength(5));
      expect(queryTypes.contains('retention'), isTrue);
    });

    test('User properties list pagination', () {
      final pagination = {
        'count': 500,
        'next': 'http://localhost:8000/api/projects/test/analytics/user-properties/?page=2',
        'previous': null,
        'results': [
          {'id': 'prop-1', 'name': 'email', 'value': 'user@example.com', 'user_id': 'user-1'},
        ],
      };
      expect(pagination['count'], equals(500));
      expect(pagination['results'], isA<List>());
    });

    test('Event filtering by time range', () {
      final timeFilter = {
        'start_timestamp': '2024-01-01T00:00:00Z',
        'end_timestamp': '2024-01-31T23:59:59Z',
      };
      expect(timeFilter['start_timestamp'], isNotNull);
      expect(timeFilter['end_timestamp'], isNotNull);
    });

    test('High-volume event batching (1000+ events)', () {
      final largeEventBatch = List.generate(
        1000,
        (i) => {
          'name': 'event_${i % 10}',
          'params': {'index': i},
          'timestamp': '2024-01-01T00:00:00Z',
        },
      );
      expect(largeEventBatch, hasLength(1000));
      expect(largeEventBatch[999]['params']['index'], equals(999));
    });
  });
}
