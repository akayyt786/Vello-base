import XCTest
@testable import OwnFirebaseSDK

final class AnalyticsServiceTests: XCTestCase {
  var firebase: OwnFirebase!
  var analyticsService: AnalyticsService!

  override func setUp() {
    super.setUp()
    URLProtocol.registerClass(AnalyticsMockURLProtocol.self)

    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [AnalyticsMockURLProtocol.self]

    firebase = OwnFirebase(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      )
    )
    analyticsService = firebase.analytics
  }

  override func tearDown() {
    super.tearDown()
    URLProtocol.unregisterClass(AnalyticsMockURLProtocol.self)
    AnalyticsMockURLProtocol.mockData = nil
    AnalyticsMockURLProtocol.mockResponse = nil
    AnalyticsMockURLProtocol.mockError = nil
  }

  // MARK: - Single Event Tests

  func testLogEventSuccess() async throws {
    let expectedEvent = AnalyticsEvent(
      id: "event-1",
      name: "page_view",
      params: ["page": AnyCodable("home")],
      timestamp: "2024-01-01T00:00:00Z",
      user_id: "user-123",
      session_id: "session-123"
    )

    let jsonData = try JSONEncoder().encode(expectedEvent)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.logEvent(
      name: "page_view",
      params: ["page": AnyCodable("home")],
      userId: "user-123",
      sessionId: "session-123"
    )

    XCTAssertEqual(result.name, "page_view")
    XCTAssertEqual(result.user_id, "user-123")
  }

  func testLogEventWithoutParams() async throws {
    let expectedEvent = AnalyticsEvent(
      id: "event-1",
      name: "app_open",
      params: [:],
      timestamp: "2024-01-01T00:00:00Z",
      user_id: nil,
      session_id: nil
    )

    let jsonData = try JSONEncoder().encode(expectedEvent)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.logEvent(name: "app_open")

    XCTAssertEqual(result.name, "app_open")
  }

  func testLogEventWithComplexParams() async throws {
    let params: [String: AnyCodable] = [
      "page": AnyCodable("product"),
      "product_id": AnyCodable("prod-123"),
      "price": AnyCodable(99.99),
      "tags": AnyCodable(["sale", "featured"])
    ]

    let expectedEvent = AnalyticsEvent(
      id: "event-1",
      name: "view_product",
      params: params,
      timestamp: "2024-01-01T00:00:00Z",
      user_id: "user-123",
      session_id: "session-123"
    )

    let jsonData = try JSONEncoder().encode(expectedEvent)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.logEvent(
      name: "view_product",
      params: params,
      userId: "user-123",
      sessionId: "session-123"
    )

    XCTAssertEqual(result.name, "view_product")
    XCTAssertEqual(result.params.count, 4)
  }

  // MARK: - Batch Event Tests

  func testLogEventBatchedAndFlush() async throws {
    let responseMessage = MessageResponse(detail: "Events logged")

    let jsonData = try JSONEncoder().encode(responseMessage)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/batch/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    // Log events (should be queued, not sent immediately)
    analyticsService.logEventBatched(name: "event1")
    analyticsService.logEventBatched(name: "event2")
    analyticsService.logEventBatched(name: "event3")

    // Flush the batch
    try await analyticsService.flushEventBatch()
  }

  func testLogEventBatchedAutomaticFlush() async throws {
    let batchService = AnalyticsService(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      ),
      batchSize: 3,
      batchFlushInterval: 60
    )

    let responseMessage = MessageResponse(detail: "Events logged")

    let jsonData = try JSONEncoder().encode(responseMessage)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/batch/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    // Log 3 events (should trigger automatic flush)
    batchService.logEventBatched(name: "event1")
    batchService.logEventBatched(name: "event2")
    batchService.logEventBatched(name: "event3")

    // Wait a bit for the batch to be processed
    try await Task.sleep(nanoseconds: 100_000_000)
  }

  func testLogEventBatchedMultipleBatches() async throws {
    let batchService = AnalyticsService(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      ),
      batchSize: 2,
      batchFlushInterval: 60
    )

    let responseMessage = MessageResponse(detail: "Events logged")

    let jsonData = try JSONEncoder().encode(responseMessage)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/batch/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    // Log 5 events (should trigger multiple flushes)
    for i in 1...5 {
      batchService.logEventBatched(name: "event\(i)")
    }

    try await Task.sleep(nanoseconds: 100_000_000)
  }

  // MARK: - List Events Tests

  func testListEventsSuccess() async throws {
    let events = [
      AnalyticsEvent(
        id: "event-1",
        name: "page_view",
        params: ["page": AnyCodable("home")],
        timestamp: "2024-01-01T00:00:00Z",
        user_id: "user-123",
        session_id: "session-123"
      ),
      AnalyticsEvent(
        id: "event-2",
        name: "click",
        params: ["element": AnyCodable("button")],
        timestamp: "2024-01-01T00:01:00Z",
        user_id: "user-123",
        session_id: "session-123"
      )
    ]

    let response = PaginatedResponse(
      count: 2,
      next: nil,
      previous: nil,
      results: events
    )

    let jsonData = try JSONEncoder().encode(response)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.listEvents()

    XCTAssertEqual(result.count, 2)
    XCTAssertEqual(result.results.count, 2)
  }

  func testListEventsWithFilters() async throws {
    let events = [
      AnalyticsEvent(
        id: "event-1",
        name: "page_view",
        params: ["page": AnyCodable("home")],
        timestamp: "2024-01-01T00:00:00Z",
        user_id: "user-123",
        session_id: "session-123"
      )
    ]

    let response = PaginatedResponse(
      count: 1,
      next: nil,
      previous: nil,
      results: events
    )

    let jsonData = try JSONEncoder().encode(response)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.listEvents(
      filters: ["name": "page_view"]
    )

    XCTAssertEqual(result.count, 1)
  }

  // MARK: - User Properties Tests

  func testSetUserPropertySuccess() async throws {
    let expectedProperty = UserProperty(
      id: "prop-1",
      name: "user_type",
      value: "premium",
      user_id: "user-123"
    )

    let jsonData = try JSONEncoder().encode(expectedProperty)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/user-properties/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.setUserProperty(
      name: "user_type",
      value: "premium"
    )

    XCTAssertEqual(result.name, "user_type")
    XCTAssertEqual(result.value, "premium")
  }

  func testListUserPropertiesSuccess() async throws {
    let properties = [
      UserProperty(
        id: "prop-1",
        name: "user_type",
        value: "premium",
        user_id: "user-123"
      ),
      UserProperty(
        id: "prop-2",
        name: "plan",
        value: "annual",
        user_id: "user-123"
      )
    ]

    let response = PaginatedResponse(
      count: 2,
      next: nil,
      previous: nil,
      results: properties
    )

    let jsonData = try JSONEncoder().encode(response)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/user-properties/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.listUserProperties()

    XCTAssertEqual(result.count, 2)
  }

  // MARK: - Conversion Events Tests

  func testListConversionEventsSuccess() async throws {
    let events = [
      ConversionEvent(id: "conv-1", name: "purchase"),
      ConversionEvent(id: "conv-2", name: "signup")
    ]

    let response = PaginatedResponse(
      count: 2,
      next: nil,
      previous: nil,
      results: events
    )

    let jsonData = try JSONEncoder().encode(response)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/conversion-events/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.listConversionEvents()

    XCTAssertEqual(result.count, 2)
  }

  func testMarkConversionEventSuccess() async throws {
    let expectedEvent = ConversionEvent(
      id: "conv-1",
      name: "purchase"
    )

    let jsonData = try JSONEncoder().encode(expectedEvent)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/conversion-events/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await analyticsService.markConversionEvent(name: "purchase")

    XCTAssertEqual(result.name, "purchase")
  }

  // MARK: - Analytics Query Tests

  func testAnalyticsQuerySuccess() async throws {
    let expectedResult = AnalyticsQueryResult(
      metric: "page_views",
      dimension: "page",
      rows: [
        AnalyticsQueryRow(
          dimension_value: "home",
          metric_value: 100,
          date: "2024-01-01"
        ),
        AnalyticsQueryRow(
          dimension_value: "about",
          metric_value: 50,
          date: "2024-01-01"
        )
      ]
    )

    let jsonData = try JSONEncoder().encode(expectedResult)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/query/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let params = AnalyticsQueryParams(
      metric: "page_views",
      dimension: "page",
      start_date: "2024-01-01",
      end_date: "2024-01-31"
    )

    let result = try await analyticsService.query(params: params)

    XCTAssertEqual(result.metric, "page_views")
    XCTAssertEqual(result.rows.count, 2)
    XCTAssertEqual(result.rows[0].metric_value, 100)
  }

  func testAnalyticsQueryWithFilters() async throws {
    let expectedResult = AnalyticsQueryResult(
      metric: "revenue",
      dimension: "country",
      rows: [
        AnalyticsQueryRow(
          dimension_value: "US",
          metric_value: 5000,
          date: "2024-01-01"
        )
      ]
    )

    let jsonData = try JSONEncoder().encode(expectedResult)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/query/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let params = AnalyticsQueryParams(
      metric: "revenue",
      dimension: "country",
      filters: ["currency": "USD"]
    )

    let result = try await analyticsService.query(params: params)

    XCTAssertEqual(result.metric, "revenue")
  }

  // MARK: - Error Handling Tests

  func testLogEventWithInvalidData() async throws {
    let errorResponse = APIError(status: 400, message: "Invalid event data")

    let jsonData = try JSONEncoder().encode(errorResponse)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/")!,
      statusCode: 400,
      httpVersion: nil,
      headerFields: nil
    )

    do {
      _ = try await analyticsService.logEvent(name: "")
      XCTFail("Should throw error")
    } catch {
      XCTAssertTrue(error is OwnFirebaseError)
    }
  }

  // MARK: - Batch Event Timing Tests

  func testBatchFlushTimerFires() async throws {
    let batchService = AnalyticsService(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      ),
      batchSize: 100, // High batch size so timer is the trigger
      batchFlushInterval: 0.1 // 100ms
    )

    let responseMessage = MessageResponse(detail: "Events logged")

    let jsonData = try JSONEncoder().encode(responseMessage)
    AnalyticsMockURLProtocol.mockData = jsonData
    AnalyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/analytics/events/batch/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    // Log one event (should queue and start timer)
    batchService.logEventBatched(name: "test_event")

    // Wait for timer to fire
    try await Task.sleep(nanoseconds: 200_000_000) // 200ms
  }
}

// MARK: - Mock URL Protocol

class AnalyticsMockURLProtocol: URLProtocol {
  static var mockData: Data?
  static var mockResponse: HTTPURLResponse?
  static var mockError: Error?

  override class func canInit(with request: URLRequest) -> Bool {
    return true
  }

  override class func canonicalRequest(for request: URLRequest) -> URLRequest {
    return request
  }

  override func startLoading() {
    if let error = AnalyticsMockURLProtocol.mockError {
      client?.urlProtocol(self, didFailWithError: error)
    } else if let response = AnalyticsMockURLProtocol.mockResponse {
      client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
      client?.urlProtocol(self, didLoad: AnalyticsMockURLProtocol.mockData ?? Data())
      client?.urlProtocolDidFinishLoading(self)
    }
  }

  override func stopLoading() {}
}
