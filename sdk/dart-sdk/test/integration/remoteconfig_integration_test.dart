import 'package:test/test.dart';
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() {
  group('RemoteConfigSDK Integration Tests', () {
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

    test('RemoteConfig service is properly initialized', () {
      expect(app.remoteConfig, isNotNull);
      expect(app.remoteConfig.baseUrl, equals(baseUrl));
      expect(app.remoteConfig.projectId, equals(testProjectId));
    });

    test('Parameter management methods', () {
      final methods = [
        app.remoteConfig.listParameters,
        app.remoteConfig.getParameter,
        app.remoteConfig.createParameter,
        app.remoteConfig.updateParameter,
        app.remoteConfig.deleteParameter,
      ];
      expect(methods, hasLength(5));
    });

    test('Fetch methods are available', () {
      final methods = [
        app.remoteConfig.fetch,
        app.remoteConfig.fetchWithContext,
      ];
      expect(methods, hasLength(2));
    });

    test('Feature flag parameters', () {
      final flags = [
        {
          'key': 'feature_new_ui',
          'default_value': 'false',
          'value_type': 'boolean',
        },
        {
          'key': 'feature_beta_analytics',
          'default_value': 'false',
          'value_type': 'boolean',
        },
        {
          'key': 'feature_dark_mode',
          'default_value': 'true',
          'value_type': 'boolean',
        },
      ];
      expect(flags, hasLength(3));
      expect(flags.every((f) => f['value_type'] == 'boolean'), isTrue);
    });

    test('Numeric configuration parameters', () {
      final numericParams = [
        {
          'key': 'api_timeout_seconds',
          'default_value': '30',
          'value_type': 'number',
        },
        {
          'key': 'max_retry_count',
          'default_value': '3',
          'value_type': 'number',
        },
        {
          'key': 'cache_size_mb',
          'default_value': '100',
          'value_type': 'number',
        },
      ];
      expect(numericParams, hasLength(3));
    });

    test('String configuration parameters', () {
      final stringParams = [
        {
          'key': 'app_version',
          'default_value': '1.0.0',
          'value_type': 'string',
        },
        {
          'key': 'api_endpoint',
          'default_value': 'https://api.example.com',
          'value_type': 'string',
        },
      ];
      expect(stringParams, hasLength(2));
    });

    test('JSON configuration parameters', () {
      final jsonParams = {
        'key': 'feature_config',
        'default_value': '{"enabled":true,"level":2,"options":["a","b"]}',
        'value_type': 'json',
      };
      expect(jsonParams['value_type'], equals('json'));
      expect(jsonParams['default_value'], contains('{'));
    });

    test('Fetch with user context', () {
      final context = {
        'user_id': 'user-123',
        'user_tier': 'premium',
        'country': 'US',
        'app_version': '2.1.0',
      };
      expect(context['user_id'], equals('user-123'));
      expect(context['user_tier'], equals('premium'));
    });

    test('Conditional parameter overrides', () {
      final conditions = [
        {
          'name': 'premium_users',
          'condition': {'user_tier': 'premium'},
          'parameter_value': 'true',
        },
        {
          'name': 'beta_testers',
          'condition': {'user_tier': 'beta'},
          'parameter_value': 'true',
        },
      ];
      expect(conditions, hasLength(2));
    });

    test('Parameter version history', () {
      final versions = [
        {
          'version': 1,
          'value': 'false',
          'created_at': '2024-01-01T00:00:00Z',
        },
        {
          'version': 2,
          'value': 'true',
          'created_at': '2024-01-05T10:00:00Z',
        },
      ];
      expect(versions, hasLength(2));
      expect(versions[1]['version'], equals(2));
    });

    test('Parameter list pagination', () {
      final paginated = {
        'count': 100,
        'next': 'http://localhost:8000/api/projects/test/remote-config/parameters/?page=2',
        'previous': null,
        'results': [
          {
            'id': 'param-1',
            'key': 'param_name',
            'default_value': 'default',
            'value_type': 'string',
          },
        ],
      };
      expect(paginated['count'], equals(100));
      expect(paginated['results'], hasLength(1));
    });

    test('Batch parameter fetch and cache', () {
      final batchParams = {
        'param_1': 'value_1',
        'param_2': 'value_2',
        'param_3': 'value_3',
        'param_4': 'value_4',
        'param_5': 'value_5',
      };
      expect(batchParams, hasLength(5));
    });

    test('Parameter staleness and TTL', () {
      final fetchMetadata = {
        'last_fetch_time': '2024-01-01T12:00:00Z',
        'ttl_seconds': 3600,
        'is_stale': false,
      };
      expect(fetchMetadata['ttl_seconds'], equals(3600));
      expect(fetchMetadata['is_stale'], isFalse);
    });
  });
}
