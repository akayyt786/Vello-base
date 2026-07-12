import Foundation

public class AnalyticsService: OwnFirebaseClient {
  private let batchQueue = DispatchQueue(label: "com.ownfirebase.analytics.batch")
  private var eventBatch: [LogEventRequest] = []
  private var batchTimer: Timer?
  private let batchSize: Int
  private let batchFlushInterval: TimeInterval

  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    batchSize: Int = 50,
    batchFlushInterval: TimeInterval = 30
  ) {
    self.batchSize = batchSize
    self.batchFlushInterval = batchFlushInterval
    super.init(config: config, retryConfig: retryConfig)
  }

  deinit {
    batchTimer?.invalidate()
  }

  // MARK: - Events

  public func logEvent(
    name: String,
    params: [String: AnyCodable]? = nil,
    userId: String? = nil,
    sessionId: String? = nil
  ) async throws -> AnalyticsEvent {
    let body = LogEventRequest(
      name: name,
      params: params ?? [:],
      user_id: userId,
      session_id: sessionId
    )
    return try await request(
      "POST",
      url: projectUrl("analytics/events/"),
      body: body
    )
  }

  public func logEventBatched(
    name: String,
    params: [String: AnyCodable]? = nil,
    userId: String? = nil,
    sessionId: String? = nil
  ) {
    let request = LogEventRequest(
      name: name,
      params: params ?? [:],
      user_id: userId,
      session_id: sessionId
    )

    batchQueue.sync {
      eventBatch.append(request)

      if eventBatch.count >= batchSize {
        // Flush events asynchronously
        Task {
          try? await flushEventBatch()
        }
      } else if batchTimer == nil {
        startBatchTimer()
      }
    }
  }

  public func flushEventBatch() async throws {
    let batch = batchQueue.sync { eventBatch }
    guard !batch.isEmpty else { return }

    let body = BatchLogEventsRequest(events: batch)
    _ = try await request(
      "POST",
      url: projectUrl("analytics/events/batch/"),
      body: body
    ) as MessageResponse

    batchQueue.sync {
      eventBatch.removeAll()
    }

    batchTimer?.invalidate()
    batchTimer = nil
  }

  private func startBatchTimer() {
    batchTimer = Timer.scheduledTimer(withTimeInterval: batchFlushInterval, repeats: false) { [weak self] _ in
      Task {
        try? await self?.flushEventBatch()
      }
    }
  }

  public func listEvents(filters: [String: String]? = nil) async throws -> PaginatedResponse<AnalyticsEvent> {
    var options = RequestOptions()
    options.query = filters

    return try await request(
      "GET",
      url: projectUrl("analytics/events/"),
      options: options
    )
  }

  // MARK: - User Properties

  public func setUserProperty(name: String, value: String) async throws -> UserProperty {
    let body = SetUserPropertyRequest(name: name, value: value)
    return try await request(
      "POST",
      url: projectUrl("analytics/user-properties/"),
      body: body
    )
  }

  public func listUserProperties() async throws -> PaginatedResponse<UserProperty> {
    return try await request(
      "GET",
      url: projectUrl("analytics/user-properties/")
    )
  }

  // MARK: - Conversion Events

  public func listConversionEvents() async throws -> PaginatedResponse<ConversionEvent> {
    return try await request(
      "GET",
      url: projectUrl("analytics/conversion-events/")
    )
  }

  public func markConversionEvent(name: String) async throws -> ConversionEvent {
    let body = MarkConversionEventRequest(name: name)
    return try await request(
      "POST",
      url: projectUrl("analytics/conversion-events/"),
      body: body
    )
  }

  // MARK: - Query

  public func query(params: AnalyticsQueryParams) async throws -> AnalyticsQueryResult {
    return try await request(
      "POST",
      url: projectUrl("analytics/query/"),
      body: params
    )
  }
}

// MARK: - Request Types

public struct AnalyticsQueryParams: Encodable {
  public let metric: String
  public let dimension: String?
  public let start_date: String?
  public let end_date: String?
  public let filters: [String: String]?

  public init(
    metric: String,
    dimension: String? = nil,
    start_date: String? = nil,
    end_date: String? = nil,
    filters: [String: String]? = nil
  ) {
    self.metric = metric
    self.dimension = dimension
    self.start_date = start_date
    self.end_date = end_date
    self.filters = filters
  }
}

public struct AnalyticsQueryRow: Codable {
  public let dimension_value: String?
  public let metric_value: Double
  public let date: String?
}

public struct AnalyticsQueryResult: Codable {
  public let metric: String
  public let dimension: String?
  public let rows: [AnalyticsQueryRow]
}

public struct ConversionEvent: Codable {
  public let id: String
  public let name: String
}

private struct LogEventRequest: Encodable {
  let name: String
  let params: [String: AnyCodable]
  let user_id: String?
  let session_id: String?
}

private struct BatchLogEventsRequest: Encodable {
  let events: [LogEventRequest]
}

private struct SetUserPropertyRequest: Encodable {
  let name: String
  let value: String
}

private struct MarkConversionEventRequest: Encodable {
  let name: String
}
