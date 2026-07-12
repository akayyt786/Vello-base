import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/push.dart';

void main() {
  group('PushSDK Unit Tests (Mocked)', () {
    late PushSDK push;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      push = PushSDK(config: config);
    });

    test('PushSDK initializes with config', () {
      expect(push.baseUrl, equals('http://localhost:8000'));
      expect(push.projectId, equals('test-project'));
    });

    test('PushDeviceToken.fromJson parses correctly', () {
      final json = {
        'id': 'token-123',
        'token': 'device-token-abc123',
        'platform': 'ios',
        'is_active': true,
      };
      final token = PushDeviceToken.fromJson(json);
      expect(token.id, equals('token-123'));
      expect(token.token, equals('device-token-abc123'));
      expect(token.platform, equals('ios'));
      expect(token.isActive, isTrue);
    });

    test('PushDeviceToken for different platforms', () {
      final iosToken = PushDeviceToken(
        id: 'ios-1',
        token: 'ios-token',
        platform: 'ios',
        isActive: true,
      );
      final androidToken = PushDeviceToken(
        id: 'android-1',
        token: 'android-token',
        platform: 'android',
        isActive: true,
      );
      final webToken = PushDeviceToken(
        id: 'web-1',
        token: 'web-token',
        platform: 'web',
        isActive: true,
      );

      expect(iosToken.platform, equals('ios'));
      expect(androidToken.platform, equals('android'));
      expect(webToken.platform, equals('web'));
    });

    test('Notification payload structure', () {
      final payload = <String, dynamic>{
        'title': 'Hello',
        'body': 'World',
        'data': {
          'screen': 'home',
          'action': 'navigate',
        },
      };
      expect(payload['title'], equals('Hello'));
      expect(payload['body'], equals('World'));
      expect(payload['data']['screen'], equals('home'));
    });

    test('Topic subscription structure', () {
      // Matches push/views.py's TopicViewSet.subscribe: the topic id is part
      // of the URL path (push/topics/{topicId}/subscribe/) and the body
      // carries only device_token_id.
      final subscriptionBody = {
        'device_token_id': 'token-123',
      };
      expect(subscriptionBody['device_token_id'], equals('token-123'));
    });

    test('Multiple topics support', () {
      final topics = ['news', 'sports', 'weather', 'technology'];
      expect(topics, hasLength(4));
      expect(topics.contains('news'), isTrue);
      expect(topics.contains('sports'), isTrue);
    });

    test('Inactive device token', () {
      final json = {
        'id': 'token-123',
        'token': 'device-token',
        'platform': 'ios',
        'is_active': false,
      };
      final token = PushDeviceToken.fromJson(json);
      expect(token.isActive, isFalse);
    });

    test('Send to device payload', () {
      // Matches push/serializers.py's PushNotificationSerializer: device_token
      // plus flat title/body fields, posted to push/notifications/ — no
      // nested 'payload' wrapper and no separate send-to-device endpoint.
      final sendPayload = {
        'device_token': 'token-123',
        'title': 'Test',
        'body': 'Message',
      };
      expect(sendPayload['device_token'], isNotNull);
      expect(sendPayload['title'], equals('Test'));
      expect(sendPayload['body'], equals('Message'));
    });

    test('Send to topic payload', () {
      final sendPayload = <String, dynamic>{
        'topic': 'news',
        'title': 'Breaking News',
        'body': 'Important update',
      };
      expect(sendPayload['topic'], equals('news'));
      expect(sendPayload['title'], equals('Breaking News'));
    });

    test('List tokens paginated response', () {
      final response = {
        'count': 50,
        'next': 'http://localhost:8000/api/projects/test/push/tokens/?page=2',
        'previous': null,
        'results': [
          {
            'id': 'token-1',
            'token': 'device-token-1',
            'platform': 'ios',
            'is_active': true,
          },
          {
            'id': 'token-2',
            'token': 'device-token-2',
            'platform': 'android',
            'is_active': true,
          },
        ],
      };
      expect(response['count'], equals(50));
      expect(response['results'], hasLength(2));
    });

    test('Rich notification with custom data', () {
      final richPayload = <String, dynamic>{
        'title': 'Purchase Confirmation',
        'body': 'Order #12345 has shipped',
        'data': {
          'order_id': '12345',
          'status': 'shipped',
          'tracking_url': 'https://tracking.example.com/12345',
          'estimated_delivery': '2024-01-05',
        },
      };
      expect(richPayload['data']['order_id'], equals('12345'));
      expect(richPayload['data'], hasLength(4));
    });
  });
}
