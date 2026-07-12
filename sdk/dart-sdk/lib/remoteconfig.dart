import 'client.dart';
import 'types.dart';

/// Remote Config SDK for OwnFirebase
class RemoteConfigSDK extends OwnFirebaseClient {
  RemoteConfigSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Parameters ───────────────────────────────────────────────────────────────

  Future<PaginatedResponse<RemoteConfigParameter>> listParameters() async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('remote-config/parameters/'),
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => RemoteConfigParameter.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return PaginatedResponse(
      count: response['count'] as int? ?? 0,
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<RemoteConfigParameter> getParameter(String key) async {
    return request<RemoteConfigParameter>(
      'GET',
      projectUrl('remote-config/parameters/$key/'),
      null,
      fromJson: (json) => RemoteConfigParameter.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<RemoteConfigParameter> createParameter({
    required String key,
    required String defaultValue,
    required String description,
    required String valueType,
  }) async {
    return request<RemoteConfigParameter>(
      'POST',
      projectUrl('remote-config/parameters/'),
      {
        'key': key,
        'default_value': defaultValue,
        'description': description,
        'value_type': valueType,
      },
      fromJson: (json) => RemoteConfigParameter.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<RemoteConfigParameter> updateParameter(
    String key, {
    required String defaultValue,
    required String description,
  }) async {
    return request<RemoteConfigParameter>(
      'PUT',
      projectUrl('remote-config/parameters/$key/'),
      {
        'default_value': defaultValue,
        'description': description,
      },
      fromJson: (json) => RemoteConfigParameter.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<void> deleteParameter(String key) async {
    return request<void>(
      'DELETE',
      projectUrl('remote-config/parameters/$key/'),
      null,
      fromJson: (_) => null,
    );
  }

  // ─── Fetch ────────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> fetch() async {
    return request<Map<String, dynamic>>(
      'GET',
      projectUrl('remote-config/fetch/'),
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> fetchWithContext(Map<String, dynamic> context) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('remote-config/fetch/'),
      {'context': context},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }
}
