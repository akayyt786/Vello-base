import Foundation

public class CrashlyticsService: OwnFirebaseClient {
  private let reportQueue = DispatchQueue(label: "com.ownfirebase.crashlytics.report")
  private var pendingReports: [CrashReportInput] = []
  private var reportBatchSize: Int
  private var reportBatchInterval: TimeInterval
  private var reportBatchTimer: Timer?

  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    reportBatchSize: Int = 50,
    reportBatchInterval: TimeInterval = 60
  ) {
    self.reportBatchSize = reportBatchSize
    self.reportBatchInterval = reportBatchInterval
    super.init(config: config, retryConfig: retryConfig)
  }

  deinit {
    reportBatchTimer?.invalidate()
  }

  // MARK: - Crash Groups

  public func listCrashGroups(filters: [String: String]? = nil) async throws -> PaginatedResponse<CrashGroup> {
    var options = RequestOptions()
    options.query = filters

    return try await request(
      "GET",
      url: projectUrl("crashlytics/groups/"),
      options: options
    )
  }

  public func getCrashGroup(id: String) async throws -> CrashGroup {
    return try await request(
      "GET",
      url: projectUrl("crashlytics/groups/\(id)/")
    )
  }

  // MARK: - Crash Reports

  public func reportCrash(
    exceptionType: String,
    message: String,
    stackTrace: String,
    appVersion: String,
    platform: String,
    deviceInfo: [String: AnyCodable]? = nil
  ) async throws -> CrashReport {
    let body = CrashReportInput(
      exception_type: exceptionType,
      message: message,
      stack_trace: stackTrace,
      app_version: appVersion,
      platform: platform,
      device_info: deviceInfo
    )
    return try await request(
      "POST",
      url: projectUrl("crashlytics/reports/"),
      body: body
    )
  }

  public func reportCrashBatched(
    exceptionType: String,
    message: String,
    stackTrace: String,
    appVersion: String,
    platform: String,
    deviceInfo: [String: AnyCodable]? = nil
  ) {
    let report = CrashReportInput(
      exception_type: exceptionType,
      message: message,
      stack_trace: stackTrace,
      app_version: appVersion,
      platform: platform,
      device_info: deviceInfo
    )

    reportQueue.sync {
      pendingReports.append(report)

      if pendingReports.count >= reportBatchSize {
        // Flush reports asynchronously
        Task {
          try? await flushReports()
        }
      } else if reportBatchTimer == nil {
        startReportBatchTimer()
      }
    }
  }

  public func flushReports() async throws {
    let batch = reportQueue.sync { pendingReports }
    guard !batch.isEmpty else { return }

    for report in batch {
      _ = try await request(
        "POST",
        url: projectUrl("crashlytics/reports/"),
        body: report
      ) as CrashReport
    }

    reportQueue.sync {
      pendingReports.removeAll()
    }

    reportBatchTimer?.invalidate()
    reportBatchTimer = nil
  }

  private func flushReportsSync() {
    Task {
      try? await flushReports()
    }
  }

  private func startReportBatchTimer() {
    reportBatchTimer = Timer.scheduledTimer(withTimeInterval: reportBatchInterval, repeats: false) { [weak self] _ in
      self?.flushReportsSync()
    }
  }

  public func listCrashReports(filters: [String: String]? = nil) async throws -> PaginatedResponse<CrashReport> {
    var options = RequestOptions()
    options.query = filters

    return try await request(
      "GET",
      url: projectUrl("crashlytics/reports/"),
      options: options
    )
  }

  public func getCrashSummary() async throws -> CrashSummary {
    return try await request(
      "GET",
      url: projectUrl("crashlytics/summary/")
    )
  }

  // MARK: - Performance Traces

  public func recordTrace(
    name: String,
    durationMs: Int,
    startedAt: String,
    attributes: [String: String]? = nil,
    metrics: [String: Double]? = nil
  ) async throws -> PerformanceTrace {
    let body = PerformanceTraceInput(
      name: name,
      duration_ms: durationMs,
      started_at: startedAt,
      attributes: attributes,
      metrics: metrics
    )
    return try await request(
      "POST",
      url: projectUrl("crashlytics/traces/"),
      body: body
    )
  }

  public func listTraces(filters: [String: String]? = nil) async throws -> PaginatedResponse<PerformanceTrace> {
    var options = RequestOptions()
    options.query = filters

    return try await request(
      "GET",
      url: projectUrl("crashlytics/traces/"),
      options: options
    )
  }

  // MARK: - Network Requests

  public func recordNetworkRequest(
    url: String,
    method: String,
    statusCode: Int,
    durationMs: Int,
    requestSize: Int? = nil,
    responseSize: Int? = nil
  ) async throws -> NetworkRequestRecord {
    let body = NetworkRequestInput(
      url: url,
      method: method,
      status_code: statusCode,
      duration_ms: durationMs,
      request_size: requestSize,
      response_size: responseSize
    )
    return try await request(
      "POST",
      url: projectUrl("crashlytics/network/"),
      body: body
    )
  }

  public func listNetworkRequests(filters: [String: String]? = nil) async throws -> PaginatedResponse<NetworkRequestRecord> {
    var options = RequestOptions()
    options.query = filters

    return try await request(
      "GET",
      url: projectUrl("crashlytics/network/"),
      options: options
    )
  }
}

// MARK: - Request Types

struct CrashReportInput: Encodable {
  let exception_type: String
  let message: String
  let stack_trace: String
  let app_version: String
  let platform: String
  let device_info: [String: AnyCodable]?
}

public struct CrashSummary: Codable {
  public let total_crashes: Int
  public let crash_free_users_percentage: Double
  public let affected_users: Int
  public let open_issues: Int
}

struct PerformanceTraceInput: Encodable {
  let name: String
  let duration_ms: Int
  let started_at: String
  let attributes: [String: String]?
  let metrics: [String: Double]?
}

struct NetworkRequestInput: Encodable {
  let url: String
  let method: String
  let status_code: Int
  let duration_ms: Int
  let request_size: Int?
  let response_size: Int?
}

public struct NetworkRequestRecord: Codable {
  public let id: String
  public let url: String
  public let method: String
  public let status_code: Int
  public let duration_ms: Int
  public let request_size: Int
  public let response_size: Int
  public let timestamp: String
}
