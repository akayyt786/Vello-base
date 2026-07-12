import 'client.dart';
import 'types.dart';

/// Push Notifications SDK for OwnFirebase
class PushSDK extends OwnFirebaseClient {
  PushSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Device Tokens ───────────────────────────────────────────────────────────

  Future<PushDeviceToken> registerToken(
    String token,
    String platform,
  ) async {
    return request<PushDeviceToken>(
      'POST',
      projectUrl('push/register-token/'),
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

  Future<Map<String, dynamic>> sendToDevice(
    String tokenId,
    Map<String, dynamic> payload,
  ) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('push/send-to-device/'),
      {
        'token_id': tokenId,
        'payload': payload,
      },
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> sendToTopic(
    String topic,
    Map<String, dynamic> payload,
  ) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('push/send-to-topic/'),
      {
        'topic': topic,
        'payload': payload,
      },
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Topics ──────────────────────────────────────────────────────────────────

  Future<void> subscribeToTopic(String tokenId, String topic) async {
    return request<void>(
      'POST',
      projectUrl('push/subscribe-topic/'),
      {
        'token_id': tokenId,
        'topic': topic,
      },
      fromJson: (_) => null,
    );
  }

  Future<void> unsubscribeFromTopic(String tokenId, String topic) async {
    return request<void>(
      'POST',
      projectUrl('push/unsubscribe-topic/'),
      {
        'token_id': tokenId,
        'topic': topic,
      },
      fromJson: (_) => null,
    );
  }
}
