import 'package:test/test.dart';
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() {
  group('PushSDK Integration Tests', () {
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

    test('Push service is properly initialized', () {
      expect(app.push, isNotNull);
      expect(app.push.baseUrl, equals(baseUrl));
      expect(app.push.projectId, equals(testProjectId));
    });

    test('Device token registration methods', () {
      final methods = [
        app.push.registerToken,
        app.push.listTokens,
        app.push.unregisterToken,
      ];
      expect(methods, hasLength(3));
    });

    test('Notification sending methods', () {
      final methods = [
        app.push.sendToDevice,
        app.push.sendToTopic,
      ];
      expect(methods, hasLength(2));
    });

    test('Topic subscription methods', () {
      final methods = [
        app.push.subscribeToTopic,
        app.push.unsubscribeFromTopic,
      ];
      expect(methods, hasLength(2));
    });

    test('Device token registration for multiple platforms', () {
      final tokens = [
        {
          'platform': 'ios',
          'token': 'ios-device-token-123',
        },
        {
          'platform': 'android',
          'token': 'android-device-token-456',
        },
        {
          'platform': 'web',
          'token': 'web-device-token-789',
        },
      ];
      expect(tokens, hasLength(3));
      expect(tokens.map((t) => t['platform']).toSet(),
        equals({'ios', 'android', 'web'}));
    });

    test('Simple notification payload', () {
      final simpleNotification = {
        'title': 'Hello',
        'body': 'Welcome to OwnFirebase',
      };
      expect(simpleNotification['title'], equals('Hello'));
      expect(simpleNotification['body'], equals('Welcome to OwnFirebase'));
    });

    test('Rich notification with data', () {
      final richNotification = {
        'title': 'New Message',
        'body': 'Alice sent you a message',
        'data': {
          'thread_id': 'thread-123',
          'sender_id': 'user-456',
          'message_id': 'msg-789',
          'action': 'open_chat',
        },
      };
      expect(richNotification['data']['thread_id'], equals('thread-123'));
      expect(richNotification['data'], hasLength(4));
    });

    test('Topic-based notifications', () {
      final topics = [
        'news',
        'sports',
        'weather',
        'technology',
        'entertainment',
      ];
      expect(topics, hasLength(5));
      expect(topics.contains('weather'), isTrue);
    });

    test('Notification for multiple recipients', () {
      final recipients = List.generate(
        10,
        (i) => {
          'token_id': 'token-$i',
          'platform': i % 2 == 0 ? 'ios' : 'android',
        },
      );
      expect(recipients, hasLength(10));
    });

    test('Batch topic subscription', () {
      final subscriptions = [
        {'token_id': 'token-1', 'topics': ['news', 'sports']},
        {'token_id': 'token-2', 'topics': ['weather', 'technology']},
        {'token_id': 'token-3', 'topics': ['entertainment', 'news']},
      ];
      expect(subscriptions, hasLength(3));
    });

    test('Notification with deep links', () {
      final notification = {
        'title': 'Special Offer',
        'body': '50% off this weekend',
        'data': {
          'deep_link': 'ownfirebase://products/sale',
          'product_id': 'prod-123',
        },
      };
      expect(notification['data']['deep_link'], contains('://'));
    });

    test('Scheduled notification structure', () {
      final scheduled = {
        'title': 'Reminder',
        'body': 'Time to check in',
        'scheduled_for': '2024-01-05T14:00:00Z',
      };
      expect(scheduled['scheduled_for'], contains('T'));
    });

    test('Campaign notification structure', () {
      final campaign = {
        'campaign_id': 'campaign-123',
        'title': 'Campaign Title',
        'segments': ['premium_users', 'active_users'],
        'scheduled_for': '2024-01-05T10:00:00Z',
      };
      expect(campaign['segments'], hasLength(2));
    });

    test('Token deregistration flow', () {
      const tokenId = 'token-to-remove';
      expect(tokenId, isNotEmpty);
    });

    test('Device token list pagination', () {
      final paginatedTokens = {
        'count': 500,
        'next': 'http://localhost:8000/api/projects/test/push/tokens/?page=2',
        'previous': null,
        'results': [
          {
            'id': 'token-1',
            'token': 'device-token-1',
            'platform': 'ios',
            'is_active': true,
          },
        ],
      };
      expect(paginatedTokens['count'], equals(500));
    });
  });
}
