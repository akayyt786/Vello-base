import 'client.dart';
import 'types.dart';

/// Crash reporting, performance monitoring, and network diagnostics SDK
/// for OwnFirebase (mirrors Firebase Crashlytics + Performance Monitoring).
///
/// All list endpoints on the backend use cursor pagination
/// (`core/pagination.py` `DefaultCursorPagination`), whose response shape is
/// `{next, previous, results}` — there is no `count` field, unlike the
/// offset-based [PaginatedResponse] used elsewhere in this SDK. That's why
/// list methods here return [CrashlyticsPaginatedResponse] instead.
class CrashlyticsSDK extends OwnFirebaseClient {
  CrashlyticsSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Crash Groups ────────────────────────────────────────────────────────

  /// List crash groups (deduplicated crash signatures). Groups are created
  /// automatically server-side when reports are ingested — there is no
  /// direct create endpoint.
  Future<CrashlyticsPaginatedResponse<CrashGroup>> listCrashGroups({
    Map<String, String>? filters,
  }) async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('crashlytics/groups/'),
      null,
      query: filters ?? {},
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => CrashGroup.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return CrashlyticsPaginatedResponse(
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<CrashGroup> getCrashGroup(String groupId) async {
    return request<CrashGroup>(
      'GET',
      projectUrl('crashlytics/groups/$groupId/'),
      null,
      fromJson: (json) => CrashGroup.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Update a crash group. Only [isResolved] and [notes] are writable by the
  /// backend — every other field on [CrashGroup] is read-only.
  Future<CrashGroup> updateCrashGroup(
    String groupId, {
    bool? isResolved,
    String? notes,
  }) async {
    final body = <String, dynamic>{
      if (isResolved != null) 'is_resolved': isResolved,
      if (notes != null) 'notes': notes,
    };

    return request<CrashGroup>(
      'PATCH',
      projectUrl('crashlytics/groups/$groupId/'),
      body,
      fromJson: (json) => CrashGroup.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Mark a crash group as resolved.
  Future<CrashGroup> resolveCrashGroup(String groupId) async {
    return request<CrashGroup>(
      'POST',
      projectUrl('crashlytics/groups/$groupId/resolve/'),
      null,
      fromJson: (json) => CrashGroup.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Mark a crash group as unresolved (e.g. it regressed).
  Future<CrashGroup> unresolveCrashGroup(String groupId) async {
    return request<CrashGroup>(
      'POST',
      projectUrl('crashlytics/groups/$groupId/unresolve/'),
      null,
      fromJson: (json) => CrashGroup.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Crash Reports ───────────────────────────────────────────────────────

  /// Submit a single crash occurrence. The backend automatically
  /// deduplicates it into a [CrashGroup] server-side.
  ///
  /// [exceptionType], [stackTrace], and [occurredAt] are required by the
  /// backend model. Everything else has a server-side default (e.g.
  /// [platform] defaults to `"android"`, [fatal] defaults to `true`) and may
  /// be omitted.
  Future<CrashReport> reportCrash({
    required String exceptionType,
    required String stackTrace,
    required String occurredAt,
    String? userId,
    String? sessionId,
    String? platform,
    String? appVersion,
    String? osVersion,
    String? deviceModel,
    String? exceptionMessage,
    bool? fatal,
    List<dynamic>? breadcrumbs,
    Map<String, dynamic>? customKeys,
  }) async {
    final body = <String, dynamic>{
      'exception_type': exceptionType,
      'stack_trace': stackTrace,
      'occurred_at': occurredAt,
      if (userId != null) 'user_id': userId,
      if (sessionId != null) 'session_id': sessionId,
      if (platform != null) 'platform': platform,
      if (appVersion != null) 'app_version': appVersion,
      if (osVersion != null) 'os_version': osVersion,
      if (deviceModel != null) 'device_model': deviceModel,
      if (exceptionMessage != null) 'exception_message': exceptionMessage,
      if (fatal != null) 'fatal': fatal,
      if (breadcrumbs != null) 'breadcrumbs': breadcrumbs,
      if (customKeys != null) 'custom_keys': customKeys,
    };

    return request<CrashReport>(
      'POST',
      projectUrl('crashlytics/reports/'),
      body,
      fromJson: (json) => CrashReport.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<CrashlyticsPaginatedResponse<CrashReport>> listCrashReports({
    Map<String, String>? filters,
  }) async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('crashlytics/reports/'),
      null,
      query: filters ?? {},
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => CrashReport.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return CrashlyticsPaginatedResponse(
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<CrashReport> getCrashReport(String reportId) async {
    return request<CrashReport>(
      'GET',
      projectUrl('crashlytics/reports/$reportId/'),
      null,
      fromJson: (json) => CrashReport.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Performance Traces ──────────────────────────────────────────────────

  /// Record a single client-side performance trace. [traceName],
  /// [durationMs], and [occurredAt] are required; the rest have server-side
  /// defaults.
  Future<PerformanceTrace> recordTrace({
    required String traceName,
    required int durationMs,
    required String occurredAt,
    String? userId,
    String? sessionId,
    String? platform,
    String? appVersion,
    Map<String, dynamic>? customAttributes,
    Map<String, dynamic>? customMetrics,
  }) async {
    final body = <String, dynamic>{
      'trace_name': traceName,
      'duration_ms': durationMs,
      'occurred_at': occurredAt,
      if (userId != null) 'user_id': userId,
      if (sessionId != null) 'session_id': sessionId,
      if (platform != null) 'platform': platform,
      if (appVersion != null) 'app_version': appVersion,
      if (customAttributes != null) 'custom_attributes': customAttributes,
      if (customMetrics != null) 'custom_metrics': customMetrics,
    };

    return request<PerformanceTrace>(
      'POST',
      projectUrl('crashlytics/traces/'),
      body,
      fromJson: (json) => PerformanceTrace.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<CrashlyticsPaginatedResponse<PerformanceTrace>> listTraces({
    Map<String, String>? filters,
  }) async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('crashlytics/traces/'),
      null,
      query: filters ?? {},
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => PerformanceTrace.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return CrashlyticsPaginatedResponse(
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<PerformanceTrace> getTrace(String traceId) async {
    return request<PerformanceTrace>(
      'GET',
      projectUrl('crashlytics/traces/$traceId/'),
      null,
      fromJson: (json) => PerformanceTrace.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Bulk-submit up to 500 performance traces in a single request.
  /// Each item in [traces] is the same shape accepted by [recordTrace]
  /// (snake_case keys, e.g. `trace_name`, `duration_ms`, `occurred_at`).
  Future<List<PerformanceTrace>> submitTracesBatch(
    List<Map<String, dynamic>> traces,
  ) async {
    if (traces.length > 500) {
      throw ArgumentError('Batch size exceeds the maximum of 500 items.');
    }

    return request<List<PerformanceTrace>>(
      'POST',
      projectUrl('crashlytics/traces/batch/'),
      traces,
      fromJson: (json) {
        final list = json as List;
        return list
            .map((item) => PerformanceTrace.fromJson(item as Map<String, dynamic>))
            .toList();
      },
    );
  }

  // ─── Network Requests ────────────────────────────────────────────────────

  /// Record a single HTTP network request performance record. [url],
  /// [httpMethod], [durationMs], and [occurredAt] are required; the rest have
  /// server-side defaults (e.g. [responseCode] may be omitted for requests
  /// that never completed).
  Future<NetworkRequestRecord> recordNetworkRequest({
    required String url,
    required String httpMethod,
    required int durationMs,
    required String occurredAt,
    int? responseCode,
    int? requestSizeBytes,
    int? responseSizeBytes,
    String? userId,
    String? sessionId,
    String? platform,
    String? appVersion,
  }) async {
    final body = <String, dynamic>{
      'url': url,
      'http_method': httpMethod,
      'duration_ms': durationMs,
      'occurred_at': occurredAt,
      if (responseCode != null) 'response_code': responseCode,
      if (requestSizeBytes != null) 'request_size_bytes': requestSizeBytes,
      if (responseSizeBytes != null) 'response_size_bytes': responseSizeBytes,
      if (userId != null) 'user_id': userId,
      if (sessionId != null) 'session_id': sessionId,
      if (platform != null) 'platform': platform,
      if (appVersion != null) 'app_version': appVersion,
    };

    return request<NetworkRequestRecord>(
      'POST',
      projectUrl('crashlytics/network/'),
      body,
      fromJson: (json) => NetworkRequestRecord.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<CrashlyticsPaginatedResponse<NetworkRequestRecord>> listNetworkRequests({
    Map<String, String>? filters,
  }) async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('crashlytics/network/'),
      null,
      query: filters ?? {},
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => NetworkRequestRecord.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return CrashlyticsPaginatedResponse(
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<NetworkRequestRecord> getNetworkRequest(String recordId) async {
    return request<NetworkRequestRecord>(
      'GET',
      projectUrl('crashlytics/network/$recordId/'),
      null,
      fromJson: (json) => NetworkRequestRecord.fromJson(json as Map<String, dynamic>),
    );
  }

  /// Bulk-submit up to 500 network request records in a single request.
  /// Each item in [records] is the same shape accepted by
  /// [recordNetworkRequest] (snake_case keys, e.g. `http_method`,
  /// `response_code`, `occurred_at`).
  Future<List<NetworkRequestRecord>> submitNetworkRequestsBatch(
    List<Map<String, dynamic>> records,
  ) async {
    if (records.length > 500) {
      throw ArgumentError('Batch size exceeds the maximum of 500 items.');
    }

    return request<List<NetworkRequestRecord>>(
      'POST',
      projectUrl('crashlytics/network/batch/'),
      records,
      fromJson: (json) {
        final list = json as List;
        return list
            .map((item) => NetworkRequestRecord.fromJson(item as Map<String, dynamic>))
            .toList();
      },
    );
  }

  // ─── Summary ──────────────────────────────────────────────────────────────

  Future<CrashSummary> getCrashSummary() async {
    return request<CrashSummary>(
      'GET',
      projectUrl('crashlytics/summary/'),
      null,
      fromJson: (json) => CrashSummary.fromJson(json as Map<String, dynamic>),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────
// Models
// ─────────────────────────────────────────────────────────────────────────

/// A deduplicated crash signature ("issue"). Multiple [CrashReport]
/// occurrences sharing the same fingerprint collapse into one group.
class CrashGroup {
  final String id;
  final String project;
  final String signature;
  final String title;
  final String exceptionType;
  final String firstSeenAt;
  final String lastSeenAt;
  final int occurrenceCount;
  final int affectedUsersCount;
  final bool isResolved;
  final String? resolvedAt;
  final String notes;
  final String createdAt;
  final String updatedAt;

  CrashGroup({
    required this.id,
    required this.project,
    required this.signature,
    required this.title,
    required this.exceptionType,
    required this.firstSeenAt,
    required this.lastSeenAt,
    required this.occurrenceCount,
    required this.affectedUsersCount,
    required this.isResolved,
    this.resolvedAt,
    required this.notes,
    required this.createdAt,
    required this.updatedAt,
  });

  factory CrashGroup.fromJson(Map<String, dynamic> json) {
    return CrashGroup(
      id: json['id'] as String,
      project: json['project'] as String,
      signature: json['signature'] as String,
      title: json['title'] as String,
      exceptionType: json['exception_type'] as String,
      firstSeenAt: json['first_seen_at'] as String,
      lastSeenAt: json['last_seen_at'] as String,
      occurrenceCount: json['occurrence_count'] as int,
      affectedUsersCount: json['affected_users_count'] as int,
      isResolved: json['is_resolved'] as bool,
      resolvedAt: json['resolved_at'] as String?,
      notes: (json['notes'] ?? '') as String,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
    );
  }
}

/// A single crash occurrence, linked (after server-side grouping) to a
/// [CrashGroup].
class CrashReport {
  final String id;
  final String project;
  final String? group;
  final String userId;
  final String sessionId;
  final String platform;
  final String appVersion;
  final String osVersion;
  final String deviceModel;
  final String exceptionType;
  final String exceptionMessage;
  final String stackTrace;
  final bool fatal;
  final List<dynamic> breadcrumbs;
  final Map<String, dynamic> customKeys;
  final String occurredAt;
  final String createdAt;

  CrashReport({
    required this.id,
    required this.project,
    this.group,
    required this.userId,
    required this.sessionId,
    required this.platform,
    required this.appVersion,
    required this.osVersion,
    required this.deviceModel,
    required this.exceptionType,
    required this.exceptionMessage,
    required this.stackTrace,
    required this.fatal,
    required this.breadcrumbs,
    required this.customKeys,
    required this.occurredAt,
    required this.createdAt,
  });

  factory CrashReport.fromJson(Map<String, dynamic> json) {
    return CrashReport(
      id: json['id'] as String,
      project: json['project'] as String,
      group: json['group'] as String?,
      userId: (json['user_id'] ?? '') as String,
      sessionId: (json['session_id'] ?? '') as String,
      platform: json['platform'] as String,
      appVersion: (json['app_version'] ?? '') as String,
      osVersion: (json['os_version'] ?? '') as String,
      deviceModel: (json['device_model'] ?? '') as String,
      exceptionType: json['exception_type'] as String,
      exceptionMessage: (json['exception_message'] ?? '') as String,
      stackTrace: json['stack_trace'] as String,
      fatal: json['fatal'] as bool,
      breadcrumbs: (json['breadcrumbs'] ?? []) as List<dynamic>,
      customKeys: Map<String, dynamic>.from(json['custom_keys'] as Map? ?? {}),
      occurredAt: json['occurred_at'] as String,
      createdAt: json['created_at'] as String,
    );
  }
}

/// A client-side performance measurement (custom trace).
class PerformanceTrace {
  final String id;
  final String project;
  final String traceName;
  final int durationMs;
  final String userId;
  final String sessionId;
  final String platform;
  final String appVersion;
  final Map<String, dynamic> customAttributes;
  final Map<String, dynamic> customMetrics;
  final String occurredAt;
  final String createdAt;

  PerformanceTrace({
    required this.id,
    required this.project,
    required this.traceName,
    required this.durationMs,
    required this.userId,
    required this.sessionId,
    required this.platform,
    required this.appVersion,
    required this.customAttributes,
    required this.customMetrics,
    required this.occurredAt,
    required this.createdAt,
  });

  factory PerformanceTrace.fromJson(Map<String, dynamic> json) {
    return PerformanceTrace(
      id: json['id'] as String,
      project: json['project'] as String,
      traceName: json['trace_name'] as String,
      durationMs: json['duration_ms'] as int,
      userId: (json['user_id'] ?? '') as String,
      sessionId: (json['session_id'] ?? '') as String,
      platform: json['platform'] as String,
      appVersion: (json['app_version'] ?? '') as String,
      customAttributes: Map<String, dynamic>.from(json['custom_attributes'] as Map? ?? {}),
      customMetrics: Map<String, dynamic>.from(json['custom_metrics'] as Map? ?? {}),
      occurredAt: json['occurred_at'] as String,
      createdAt: json['created_at'] as String,
    );
  }
}

/// An HTTP network request performance record.
class NetworkRequestRecord {
  final String id;
  final String project;
  final String url;
  final String httpMethod;
  final int? responseCode;
  final int requestSizeBytes;
  final int responseSizeBytes;
  final int durationMs;
  final String userId;
  final String sessionId;
  final String platform;
  final String appVersion;
  final String occurredAt;
  final String createdAt;

  NetworkRequestRecord({
    required this.id,
    required this.project,
    required this.url,
    required this.httpMethod,
    this.responseCode,
    required this.requestSizeBytes,
    required this.responseSizeBytes,
    required this.durationMs,
    required this.userId,
    required this.sessionId,
    required this.platform,
    required this.appVersion,
    required this.occurredAt,
    required this.createdAt,
  });

  factory NetworkRequestRecord.fromJson(Map<String, dynamic> json) {
    return NetworkRequestRecord(
      id: json['id'] as String,
      project: json['project'] as String,
      url: json['url'] as String,
      httpMethod: json['http_method'] as String,
      responseCode: json['response_code'] as int?,
      requestSizeBytes: (json['request_size_bytes'] ?? 0) as int,
      responseSizeBytes: (json['response_size_bytes'] ?? 0) as int,
      durationMs: json['duration_ms'] as int,
      userId: (json['user_id'] ?? '') as String,
      sessionId: (json['session_id'] ?? '') as String,
      platform: json['platform'] as String,
      appVersion: (json['app_version'] ?? '') as String,
      occurredAt: json['occurred_at'] as String,
      createdAt: json['created_at'] as String,
    );
  }
}

/// One entry in [CrashSummary.topCrashes].
class TopCrashEntry {
  final String signature;
  final String title;
  final int count;
  final String? lastSeen;

  TopCrashEntry({
    required this.signature,
    required this.title,
    required this.count,
    this.lastSeen,
  });

  factory TopCrashEntry.fromJson(Map<String, dynamic> json) {
    return TopCrashEntry(
      signature: json['signature'] as String,
      title: json['title'] as String,
      count: json['count'] as int,
      lastSeen: json['last_seen'] as String?,
    );
  }
}

/// Project-level crash + performance dashboard summary
/// (`GET crashlytics/summary/`).
class CrashSummary {
  final int totalCrashGroups;
  final int unresolvedGroups;
  final int totalReportsLast7d;
  final int affectedUsersLast7d;
  final List<TopCrashEntry> topCrashes;

  CrashSummary({
    required this.totalCrashGroups,
    required this.unresolvedGroups,
    required this.totalReportsLast7d,
    required this.affectedUsersLast7d,
    required this.topCrashes,
  });

  factory CrashSummary.fromJson(Map<String, dynamic> json) {
    return CrashSummary(
      totalCrashGroups: json['total_crash_groups'] as int,
      unresolvedGroups: json['unresolved_groups'] as int,
      totalReportsLast7d: json['total_reports_last_7d'] as int,
      affectedUsersLast7d: json['affected_users_last_7d'] as int,
      topCrashes: ((json['top_crashes'] ?? []) as List)
          .map((item) => TopCrashEntry.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Cursor-paginated list response shape used by all Crashlytics list
/// endpoints (`{next, previous, results}` — no `count`, since
/// `CursorPagination` can't report a total). Kept local to this module
/// rather than reusing the shared [PaginatedResponse], whose `count` field
/// is non-nullable and would otherwise require faking a `count: 0`.
class CrashlyticsPaginatedResponse<T> {
  final String? next;
  final String? previous;
  final List<T> results;

  CrashlyticsPaginatedResponse({
    this.next,
    this.previous,
    required this.results,
  });
}
