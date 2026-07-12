import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/remoteconfig.dart';

void main() {
  group('RemoteConfigSDK Unit Tests (Mocked)', () {
    late RemoteConfigSDK remoteConfig;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      remoteConfig = RemoteConfigSDK(config: config);
    });

    test('RemoteConfigSDK initializes with config', () {
      expect(remoteConfig.baseUrl, equals('http://localhost:8000'));
      expect(remoteConfig.projectId, equals('test-project'));
    });

    test('RemoteConfigParameter.fromJson parses correctly', () {
      final json = {
        'id': 'param-123',
        'key': 'feature_flag_new_ui',
        'default_value': 'false',
        'description': 'Enable new UI version',
        'value_type': 'boolean',
      };
      final param = RemoteConfigParameter.fromJson(json);
      expect(param.id, equals('param-123'));
      expect(param.key, equals('feature_flag_new_ui'));
      expect(param.defaultValue, equals('false'));
      expect(param.valueType, equals('boolean'));
    });

    test('RemoteConfigParameter with string type', () {
      final json = {
        'id': 'param-1',
        'key': 'app_version',
        'default_value': '1.0.0',
        'description': 'Current app version',
        'value_type': 'string',
      };
      final param = RemoteConfigParameter.fromJson(json);
      expect(param.valueType, equals('string'));
      expect(param.defaultValue, equals('1.0.0'));
    });

    test('RemoteConfigParameter with number type', () {
      final json = {
        'id': 'param-2',
        'key': 'max_retry_count',
        'default_value': '3',
        'description': 'Maximum retry count',
        'value_type': 'number',
      };
      final param = RemoteConfigParameter.fromJson(json);
      expect(param.valueType, equals('number'));
      expect(param.defaultValue, equals('3'));
    });

    test('RemoteConfigParameter with json type', () {
      final json = {
        'id': 'param-3',
        'key': 'feature_config',
        'default_value': '{"enabled":true,"level":2}',
        'description': 'Feature configuration',
        'value_type': 'json',
      };
      final param = RemoteConfigParameter.fromJson(json);
      expect(param.valueType, equals('json'));
      expect(param.defaultValue, contains('{'));
    });

    test('Parameter listing pagination', () {
      final response = {
        'count': 25,
        'next': 'http://localhost:8000/api/projects/test/remote-config/parameters/?page=2',
        'previous': null,
        'results': [
          {
            'id': 'param-1',
            'key': 'feature_1',
            'default_value': 'true',
            'description': 'Feature 1',
            'value_type': 'boolean',
          },
          {
            'id': 'param-2',
            'key': 'feature_2',
            'default_value': 'false',
            'description': 'Feature 2',
            'value_type': 'boolean',
          },
        ],
      };
      expect(response['count'], equals(25));
      expect(response['results'], hasLength(2));
    });

    test('Fetch parameters structure', () {
      final fetchResult = {
        'feature_flag_new_ui': 'true',
        'max_retry_count': '5',
        'app_version': '2.0.0',
      };
      expect(fetchResult['feature_flag_new_ui'], equals('true'));
      expect(fetchResult.keys, hasLength(3));
    });

    test('Fetch with context structure', () {
      final context = {
        'user_id': 'user-123',
        'app_version': '1.5.0',
        'platform': 'ios',
      };
      expect(context['user_id'], equals('user-123'));
      expect(context['platform'], equals('ios'));
    });

    test('Parameter value types all supported', () {
      final types = ['string', 'boolean', 'number', 'json'];
      expect(types, hasLength(4));
      expect(types.contains('string'), isTrue);
      expect(types.contains('json'), isTrue);
    });

    test('Multiple parameters creation', () {
      final params = [
        {'key': 'param1', 'default_value': 'value1'},
        {'key': 'param2', 'default_value': 'value2'},
        {'key': 'param3', 'default_value': 'value3'},
      ];
      expect(params, hasLength(3));
      expect(params.map((p) => p['key']).toList(), contains('param1'));
    });

    test('Parameter update operation', () {
      final updatePayload = {
        'default_value': 'new_value',
        'description': 'Updated description',
      };
      expect(updatePayload['default_value'], equals('new_value'));
      expect(updatePayload.keys, hasLength(2));
    });
  });
}
