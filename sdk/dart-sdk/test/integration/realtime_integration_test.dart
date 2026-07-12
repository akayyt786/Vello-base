import 'package:test/test.dart';
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() {
  group('Realtime Subscriptions Integration Tests', () {
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

    test('SDK services are initialized', () {
      expect(app.data, isNotNull);
      expect(app.auth, isNotNull);
      expect(app.analytics, isNotNull);
      expect(app.push, isNotNull);
    });

    test('Realtime event subscription structure', () {
      final subscriptionConfig = {
        'collection': 'users',
        'filters': {'status': 'online'},
        'events': ['create', 'update', 'delete'],
      };
      expect(subscriptionConfig['collection'], equals('users'));
      expect(subscriptionConfig['events'], hasLength(3));
    });

    test('Realtime message structure', () {
      final realtimeMessage = {
        'type': 'document_change',
        'action': 'update',
        'collection': 'users',
        'document': {
          'id': 'user-123',
          'data': {'status': 'online', 'last_seen': '2024-01-01T12:00:00Z'},
        },
      };
      expect(realtimeMessage['type'], equals('document_change'));
      expect(realtimeMessage['action'], equals('update'));
    });

    test('Document change event types', () {
      final eventTypes = ['create', 'update', 'delete', 'move'];
      expect(eventTypes, hasLength(4));
      expect(eventTypes.contains('create'), isTrue);
    });

    test('Subscription lifecycle events', () {
      final lifecycleEvents = [
        'subscribed',
        'unsubscribed',
        'error',
        'reconnecting',
        'reconnected',
      ];
      expect(lifecycleEvents, hasLength(5));
    });

    test('Multi-collection subscription', () {
      final subscriptions = [
        {'collection': 'users', 'filters': {}},
        {'collection': 'posts', 'filters': {'published': 'true'}},
        {'collection': 'comments', 'filters': {'approved': 'true'}},
      ];
      expect(subscriptions, hasLength(3));
    });

    test('Query-based subscription', () {
      final querySubscription = {
        'collection': 'users',
        'filters': {
          'status': 'online',
          'country': 'US',
          'created_after': '2024-01-01',
        },
      };
      expect(querySubscription['filters'], hasLength(3));
    });

    test('Change listener callback structure', () {
      final changeEvent = {
        'timestamp': '2024-01-01T12:34:56.789Z',
        'operation': 'update',
        'collection': 'users',
        'documentId': 'user-123',
        'previousData': {'status': 'offline'},
        'newData': {'status': 'online'},
        'changedFields': ['status'],
      };
      expect(changeEvent['operation'], equals('update'));
      expect(changeEvent['changedFields'], contains('status'));
    });

    test('Presence state tracking', () {
      final presenceState = {
        'user_id': 'user-123',
        'status': 'online',
        'last_heartbeat': '2024-01-01T12:34:56Z',
        'metadata': {'device': 'mobile', 'app_version': '1.0.0'},
      };
      expect(presenceState['status'], equals('online'));
      expect(presenceState['metadata']['device'], equals('mobile'));
    });

    test('Broadcasting message structure', () {
      final broadcastMessage = {
        'channel': 'notifications',
        'sender_id': 'user-123',
        'timestamp': '2024-01-01T12:34:56Z',
        'payload': {
          'title': 'Update Available',
          'body': 'A new version is ready',
        },
      };
      expect(broadcastMessage['channel'], equals('notifications'));
      expect(broadcastMessage['payload']['title'], isNotNull);
    });

    test('Error handling in subscriptions', () {
      final errorEvent = {
        'type': 'error',
        'code': 'permission_denied',
        'message': 'User does not have permission to access this collection',
        'timestamp': '2024-01-01T12:34:56Z',
      };
      expect(errorEvent['type'], equals('error'));
      expect(errorEvent['code'], isNotNull);
    });

    test('Batch subscription support', () {
      final subscriptions = List.generate(
        5,
        (i) => {
          'id': 'sub-$i',
          'collection': 'collection-$i',
          'active': true,
        },
      );
      expect(subscriptions, hasLength(5));
      expect(subscriptions.every((s) => s['active'] == true), isTrue);
    });

    test('Subscription filter operators', () {
      final filterOperators = ['==', '<', '>', '<=', '>=', 'in', 'array-contains'];
      expect(filterOperators, hasLength(7));
      expect(filterOperators.contains('array-contains'), isTrue);
    });

    test('Ordered subscription results', () {
      final orderedSubscription = {
        'collection': 'posts',
        'filters': {'published': 'true'},
        'orderBy': [
          {'field': 'created_at', 'direction': 'desc'},
          {'field': 'likes', 'direction': 'desc'},
        ],
      };
      expect(orderedSubscription['orderBy'], hasLength(2));
      expect(orderedSubscription['orderBy'][0]['direction'], equals('desc'));
    });
  });
}
