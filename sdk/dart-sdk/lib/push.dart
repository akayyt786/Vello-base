import 'client.dart';
import 'types.dart';

/// Push Notifications SDK for OwnFirebase
class PushSDK extends OwnFirebaseClient {
  PushSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Device Tokens ───────────────────────────────────────────────────────────

  /// Registers (or reactivates) a device token.
  ///
  /// [platform] must be one of `fcm`, `apns`, or `web`
  /// (`push/models.py`'s `DeviceToken.PLATFORM_CHOICES`) — not `ios`/`android`.
  Future<PushDeviceToken> registerToken(
    String token,
    String platform,
  ) async {
    return request<PushDeviceToken>(
      'POST',
      projectUrl('push/tokens/register/'),
      {
        'token': token,
        'platform': platform,
      },
      fromJson: (json) => PushDeviceToken.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<PaginatedResponse<PushDeviceToken>> listTokens() async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('push/tokens/'),
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => PushDeviceToken.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return PaginatedResponse(
      count: response['count'] as int? ?? 0,
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<void> unregisterToken(String tokenId) async {
    return request<void>(
      'DELETE',
      projectUrl('push/tokens/$tokenId/'),
      null,
      fromJson: (_) => null,
    );
  }

  // ─── Send Notifications ──────────────────────────────────────────────────────

  /// Sends a notification to a single device token.
  ///
  /// Both this and [sendToTopic] post to the same `push/notifications/`
  /// endpoint (`push/serializers.py`'s `PushNotificationSerializer`), which
  /// requires exactly one of `device_token`/`topic` plus flat `title`/`body`/
  /// `data`/`image_url` fields — there is no separate `send-to-device`
  /// endpoint and no nested `payload` wrapper. [payload] should contain
  /// `title`/`body` and optionally `data`/`image_url`.
  Future<Map<String, dynamic>> sendToDevice(
    String deviceTokenId,
    Map<String, dynamic> payload,
  ) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('push/notifications/'),
      {
        'device_token': deviceTokenId,
        ...payload,
      },
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  /// Sends a notification to all subscribers of a topic.
  ///
  /// [topicId] is the topic's `id` (not its name). See [sendToDevice] for the
  /// shared endpoint/serializer contract.
  Future<Map<String, dynamic>> sendToTopic(
    String topicId,
    Map<String, dynamic> payload,
  ) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('push/notifications/'),
      {
        'topic': topicId,
        ...payload,
      },
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Topics ──────────────────────────────────────────────────────────────────

  /// Subscribes a device token to a topic.
  ///
  /// [topicId] is the topic's `id` (in the URL path); [deviceTokenId] is sent
  /// as `device_token_id` in the body
  /// (`push/views.py`'s `TopicViewSet.subscribe`).
  Future<void> subscribeToTopic(String topicId, String deviceTokenId) async {
    return request<void>(
      'POST',
      projectUrl('push/topics/$topicId/subscribe/'),
      {
        'device_token_id': deviceTokenId,
      },
      fromJson: (_) => null,
    );
  }

  /// Unsubscribes a device token from a topic. See [subscribeToTopic] for the
  /// endpoint/body contract.
  Future<void> unsubscribeFromTopic(String topicId, String deviceTokenId) async {
    return request<void>(
      'POST',
      projectUrl('push/topics/$topicId/unsubscribe/'),
      {
        'device_token_id': deviceTokenId,
      },
      fromJson: (_) => null,
    );
  }
}
