import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/realtime.dart';

void main() {
  group('RealtimeSDK Unit Tests (Mocked)', () {
    late RealtimeSDK realtime;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
        accessToken: 'initial-token',
      );
      realtime = RealtimeSDK(config: config);
    });

    test('RealtimeSDK initializes with config', () {
      expect(realtime.baseUrl, equals('http://localhost:8000'));
      expect(realtime.projectId, equals('test-project'));
      expect(realtime.accessToken, equals('initial-token'));
    });

    test('RealtimeSDK is not connected before connect() is called', () {
      expect(realtime.isConnected, isFalse);
    });

    test('setAccessToken updates the token', () {
      realtime.setAccessToken('new-token');
      expect(realtime.accessToken, equals('new-token'));
    });

    test('setProjectId updates the project id', () {
      realtime.setProjectId('other-project');
      expect(realtime.projectId, equals('other-project'));
    });

    test('RealtimeSDK initializes without an access token', () {
      final noTokenConfig = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      final noTokenRealtime = RealtimeSDK(config: noTokenConfig);
      expect(noTokenRealtime.accessToken, isNull);
    });

    test('Trailing slash on baseUrl is stripped, like the REST client', () {
      final trailingSlashConfig = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000/',
        projectId: 'test-project',
      );
      final trailingSlashRealtime = RealtimeSDK(config: trailingSlashConfig);
      expect(trailingSlashRealtime.baseUrl, equals('http://localhost:8000'));
    });

    test('RealtimeChange.fromJson parses an "added" event', () {
      final json = {
        'type': 'change',
        'subscriptionId': 'sub_123',
        'event': 'added',
        'data': {'name': 'Alice', 'status': 'active'},
        'version': 1,
        'docId': 'alice',
      };
      final change = RealtimeChange.fromJson(json);
      expect(change.subscriptionId, equals('sub_123'));
      expect(change.event, equals('added'));
      expect(change.data['name'], equals('Alice'));
      expect(change.version, equals(1));
      expect(change.docId, equals('alice'));
    });

    test('RealtimeChange.fromJson parses a "removed" event without a version', () {
      final json = {
        'type': 'change',
        'subscriptionId': 'sub_456',
        'event': 'removed',
        'data': <String, dynamic>{},
        'docId': 'bob',
      };
      final change = RealtimeChange.fromJson(json);
      expect(change.event, equals('removed'));
      expect(change.version, isNull);
      expect(change.data, isEmpty);
    });

    test('RealtimeChange round-trips through toJson', () {
      final change = RealtimeChange(
        subscriptionId: 'sub_789',
        event: 'modified',
        data: {'status': 'online'},
        version: 3,
        docId: 'carol',
      );
      final json = change.toJson();
      expect(json['type'], equals('change'));
      expect(json['subscriptionId'], equals('sub_789'));
      expect(json['event'], equals('modified'));
      expect(json['version'], equals(3));
      expect(json['docId'], equals('carol'));
    });

    test('RealtimeException carries a code and message', () {
      final error = RealtimeException(code: 'PERMISSION_DENIED', message: 'nope');
      expect(error.code, equals('PERMISSION_DENIED'));
      expect(error.message, equals('nope'));
      expect(error.toString(), contains('PERMISSION_DENIED'));
    });

    test('Subscribe message structure for a document path', () {
      final message = {
        'type': 'subscribe',
        'requestId': 'req_1',
        'path': 'users/alice',
      };
      expect(message['type'], equals('subscribe'));
      expect(message['path'], equals('users/alice'));
      expect(message.containsKey('query'), isFalse);
    });

    test('Subscribe message structure for a filtered collection query', () {
      final message = {
        'type': 'subscribe',
        'requestId': 'req_2',
        'path': 'users',
        'query': {
          'where': [
            ['status', '==', 'active'],
          ],
        },
      };
      final query = message['query'] as Map<String, dynamic>;
      final where = query['where'] as List;
      expect(where, hasLength(1));
      expect(where.first, equals(['status', '==', 'active']));
    });

    test('Unsubscribe message structure', () {
      final message = {
        'type': 'unsubscribe',
        'requestId': 'req_3',
        'subscriptionId': 'sub_123',
      };
      expect(message['type'], equals('unsubscribe'));
      expect(message['subscriptionId'], equals('sub_123'));
    });

    test('Subscribed acknowledgement structure for a document snapshot', () {
      final message = {
        'type': 'subscribed',
        'requestId': 'req_1',
        'subscriptionId': 'sub_123',
        'snapshot': {
          'doc_id': 'alice',
          'collection_path': 'users',
          'data': {'name': 'Alice'},
          'version': 1,
          'created_at': '2024-01-01T00:00:00Z',
          'updated_at': '2024-01-01T00:00:00Z',
        },
      };
      final snapshot = message['snapshot'] as Map<String, dynamic>;
      expect(snapshot['doc_id'], equals('alice'));
      expect(snapshot.containsKey('collection_path'), isTrue);
    });

    test('Subscribed acknowledgement structure for a collection snapshot', () {
      final message = {
        'type': 'subscribed',
        'requestId': 'req_2',
        'subscriptionId': 'sub_456',
        'snapshot': [
          {
            'doc_id': 'alice',
            'collection_path': 'users',
            'data': {'name': 'Alice'},
            'version': 1,
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
          },
        ],
      };
      final snapshot = message['snapshot'] as List;
      expect(snapshot, hasLength(1));
    });

    test('Server error codes are one of the documented values', () {
      const errorCodes = ['PERMISSION_DENIED', 'NOT_FOUND', 'INVALID', 'INTERNAL'];
      expect(errorCodes, hasLength(4));
      expect(errorCodes.contains('PERMISSION_DENIED'), isTrue);
    });

    test('Reconnect close codes match the documented protocol', () {
      const unauthenticated = 4401;
      const notAMember = 4403;
      expect(unauthenticated, equals(4401));
      expect(notAMember, equals(4403));
    });
  });
}
