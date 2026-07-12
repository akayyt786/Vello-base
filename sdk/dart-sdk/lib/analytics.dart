import 'client.dart';
import 'types.dart';

/// Analytics SDK for OwnFirebase
class AnalyticsSDK extends OwnFirebaseClient {
  AnalyticsSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Events ──────────────────────────────────────────────────────────────────

  Future<AnalyticsEvent> logEvent(
    String name, {
    Map<String, dynamic>? params,
    String? userId,
    String? sessionId,
  }) async {
    return request<AnalyticsEvent>(
      'POST',
      projectUrl('analytics/events/'),
      {
        'name': name,
        'params': params ?? {},
        if (userId != null) 'user_id': userId,
        if (sessionId != null) 'session_id': sessionId,
      },
      fromJson: (json) => AnalyticsEvent.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<PaginatedResponse<AnalyticsEvent>> listEvents({
    Map<String, String>? filters,
  }) async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('analytics/events/'),
      null,
      query: filters ?? {},
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => AnalyticsEvent.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return PaginatedResponse(
      count: response['count'] as int? ?? 0,
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  // ─── User Properties ─────────────────────────────────────────────────────────

  Future<UserProperty> setUserProperty(String name, String value) async {
    return request<UserProperty>(
      'POST',
      projectUrl('analytics/user-properties/'),
      {'name': name, 'value': value},
      fromJson: (json) => UserProperty.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<PaginatedResponse<UserProperty>> listUserProperties() async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('analytics/user-properties/'),
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => UserProperty.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return PaginatedResponse(
      count: response['count'] as int? ?? 0,
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  // ─── Conversion Events ───────────────────────────────────────────────────────

  Future<PaginatedResponse<Map<String, dynamic>>> listConversionEvents() async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('analytics/conversion-events/'),
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => item as Map<String, dynamic>)
            .toList() ??
        [];

    return PaginatedResponse(
      count: response['count'] as int? ?? 0,
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<Map<String, dynamic>> markConversionEvent(String name) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('analytics/conversion-events/'),
      {'name': name},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Query ───────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> query(Map<String, dynamic> params) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('analytics/query/'),
      params,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }
}
