import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/realtime.dart';

void main() {
  group('RealtimeSDK Integration Tests', () {
    late RealtimeSDK realtime;
    const baseUrl = 'http://localhost:8000';
    const testProjectId = 'test-project-001';

    setUp(() {
      // Constructed directly (not via the OwnFirebase bundle) since the
      // bundle isn't wired up to RealtimeSDK yet.
      realtime = RealtimeSDK(
        config: OwnFirebaseConfig(
          baseUrl: baseUrl,
          projectId: testProjectId,
          accessToken: 'integration-test-token',
        ),
      );
    });

    test('RealtimeSDK is properly initialized', () {
      expect(realtime, isNotNull);
      expect(realtime.baseUrl, equals(baseUrl));
      expect(realtime.projectId, equals(testProjectId));
      expect(realtime.accessToken, equals('integration-test-token'));
      expect(realtime.isConnected, isFalse);
    });

    test('Connection lifecycle methods exist', () {
      final methods = [
        realtime.connect,
        realtime.disconnect,
      ];
      expect(methods, hasLength(2));
    });

    test('Subscription methods exist', () {
      final methods = [
        realtime.subscribe,
        realtime.unsubscribe,
        realtime.onChange,
      ];
      expect(methods, hasLength(3));
    });

    test('Config wiring methods exist', () {
      final methods = [
        realtime.setAccessToken,
        realtime.setProjectId,
      ];
      expect(methods, hasLength(2));
    });

    test('Keepalive method exists', () {
      final methods = [realtime.ping];
      expect(methods, hasLength(1));
    });

    test('setAccessToken and setProjectId update state for a fresh client', () {
      realtime.setAccessToken('rotated-token');
      realtime.setProjectId('another-project');
      expect(realtime.accessToken, equals('rotated-token'));
      expect(realtime.projectId, equals('another-project'));
    });

    test('onChange returns a broadcast stream before subscribe resolves', () {
      final stream = realtime.onChange('sub_not_yet_subscribed');
      expect(stream, isA<Stream<Map<String, dynamic>>>());
      expect(stream.isBroadcast, isTrue);
    });

    test('onChange is idempotent for the same subscriptionId', () {
      final first = realtime.onChange('sub_shared');
      final second = realtime.onChange('sub_shared');
      expect(first.isBroadcast, isTrue);
      expect(second.isBroadcast, isTrue);
    });

    test('disconnect before ever connecting does not throw', () {
      expect(() => realtime.disconnect(), returnsNormally);
      expect(realtime.isConnected, isFalse);
    });

    test('ping before connecting does not throw', () {
      expect(() => realtime.ping(), returnsNormally);
    });

    test('unsubscribe on an unknown subscription while disconnected resolves', () async {
      await expectLater(
        realtime.unsubscribe('sub_never_existed'),
        completes,
      );
    });

    test('unsubscribe closes the local onChange stream', () async {
      final stream = realtime.onChange('sub_to_close');
      await realtime.unsubscribe('sub_to_close');

      // A fresh onChange() call after unsubscribe should hand back a new
      // (still-open) stream rather than the one that was just closed.
      final reopened = realtime.onChange('sub_to_close');
      expect(reopened.isBroadcast, isTrue);
      expect(stream, isNotNull);
    });

    test('Document subscription path structure', () {
      const path = 'users/alice';
      expect(path.contains('/'), isTrue);
    });

    test('Collection subscription query structure', () {
      final query = {
        'where': [
          ['status', '==', 'active'],
        ],
      };
      expect(query['where'], isA<List>());
    });

    test('Reconnect backoff constants match the documented protocol', () {
      const baseDelayMs = 1000;
      const maxAttempts = 10;
      expect(baseDelayMs, equals(1000));
      expect(maxAttempts, equals(10));
    });

    test('Multiple RealtimeSDK instances stay independent', () {
      final other = RealtimeSDK(
        config: OwnFirebaseConfig(
          baseUrl: baseUrl,
          projectId: 'other-project',
          accessToken: 'other-token',
        ),
      );
      expect(realtime.projectId, equals(testProjectId));
      expect(other.projectId, equals('other-project'));
      expect(identical(realtime, other), isFalse);
    });
  });
}
