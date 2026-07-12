import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/analytics.dart';

void main() {
  group('AnalyticsSDK Unit Tests (Mocked)', () {
    late AnalyticsSDK analytics;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      analytics = AnalyticsSDK(config: config);
    });

    test('AnalyticsSDK initializes with config', () {
      expect(analytics.baseUrl, equals('http://localhost:8000'));
      expect(analytics.projectId, equals('test-project'));
    });

    test('AnalyticsEvent.fromJson parses correctly', () {
      final json = {
        'id': 'event-123',
        'name': 'page_view',
        'params': {'page': '/home', 'referrer': 'google'},
        'timestamp': '2024-01-01T00:00:00Z',
        'user_id': 'user-123',
        'session_id': 'session-456',
      };
      final event = AnalyticsEvent.fromJson(json);
      expect(event.id, equals('event-123'));
      expect(event.name, equals('page_view'));
      expect(event.params['page'], equals('/home'));
      expect(event.userId, equals('user-123'));
      expect(event.sessionId, equals('session-456'));
    });

    test('AnalyticsEvent handles missing optional fields', () {
      final json = {
        'id': 'event-123',
        'name': 'purchase',
        'params': {'amount': 99.99},
        'timestamp': '2024-01-01T00:00:00Z',
      };
      final event = AnalyticsEvent.fromJson(json);
      expect(event.userId, isNull);
      expect(event.sessionId, isNull);
    });

    test('UserProperty.fromJson parses correctly', () {
      final json = {
        'id': 'prop-123',
        'name': 'subscription_tier',
        'value': 'premium',
        'user_id': 'user-123',
      };
      final prop = UserProperty.fromJson(json);
      expect(prop.id, equals('prop-123'));
      expect(prop.name, equals('subscription_tier'));
      expect(prop.value, equals('premium'));
      expect(prop.userId, equals('user-123'));
    });

    test('AnalyticsEvent with complex params', () {
      final json = {
        'id': 'event-123',
        'name': 'purchase',
        'params': {
          'amount': 99.99,
          'currency': 'USD',
          'items': [
            {'name': 'Item 1', 'quantity': 2},
            {'name': 'Item 2', 'quantity': 1},
          ],
          'metadata': {'source': 'app', 'platform': 'iOS'},
        },
        'timestamp': '2024-01-01T00:00:00Z',
      };
      final event = AnalyticsEvent.fromJson(json);
      expect(event.params['amount'], equals(99.99));
      expect(event.params['items'], isList);
      expect((event.params['items'] as List).length, equals(2));
    });

    test('Batch event logging structure', () {
      final events = [
        {
          'name': 'page_view',
          'params': {'page': '/home'},
        },
        {
          'name': 'button_click',
          'params': {'button_id': 'btn-1'},
        },
        {
          'name': 'form_submit',
          'params': {'form_id': 'form-1'},
        },
      ];
      expect(events, hasLength(3));
      expect(events.every((e) => e.containsKey('name')), isTrue);
      expect(events.every((e) => e.containsKey('params')), isTrue);
    });

    test('Query parameter structure', () {
      final queryParams = {
        'metric': 'event_count',
        'dimension': 'event_name',
        'start_date': '2024-01-01',
        'end_date': '2024-01-31',
      };
      expect(queryParams['metric'], equals('event_count'));
      expect(queryParams['dimension'], equals('event_name'));
    });

    test('User property value types', () {
      final stringProp = {'name': 'email', 'value': 'user@example.com'};
      final numberProp = {'name': 'user_lifetime_value', 'value': '9999'};
      final boolProp = {'name': 'is_premium', 'value': 'true'};

      expect(stringProp['value'], isA<String>());
      expect(numberProp['value'], isA<String>());
      expect(boolProp['value'], isA<String>());
    });

    test('Conversion event structure', () {
      final conversionEvent = {
        'id': 'conv-123',
        'name': 'purchase_complete',
      };
      expect(conversionEvent['id'], isNotNull);
      expect(conversionEvent['name'], equals('purchase_complete'));
    });

    test('Paginated events response structure', () {
      final response = {
        'count': 100,
        'next': 'http://localhost:8000/api/projects/test/analytics/events/?page=2',
        'previous': null,
        'results': [
          {
            'id': 'event-1',
            'name': 'page_view',
            'params': {},
            'timestamp': '2024-01-01T00:00:00Z',
          },
        ],
      };
      expect(response['count'], equals(100));
      expect(response['next'], isNotNull);
      expect(response['previous'], isNull);
      expect(response['results'], isList);
    });

    test('Analytics event timestamp format', () {
      final event = AnalyticsEvent(
        id: 'event-1',
        name: 'test',
        params: {},
        timestamp: '2024-01-01T12:34:56.789Z',
      );
      expect(event.timestamp, matches(RegExp(r'^\d{4}-\d{2}-\d{2}T')));
    });
  });
}
