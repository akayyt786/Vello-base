import XCTest
@testable import OwnFirebaseSDK

final class StorageServiceTests: XCTestCase {
  var firebase: OwnFirebase!

  override func setUp() {
    super.setUp()
    URLProtocol.registerClass(StorageMockURLProtocol.self)

    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [StorageMockURLProtocol.self]

    firebase = OwnFirebase(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      )
    )
  }

  override func tearDown() {
    super.tearDown()
    URLProtocol.unregisterClass(StorageMockURLProtocol.self)
    StorageMockURLProtocol.mockData = nil
    StorageMockURLProtocol.mockResponse = nil
    StorageMockURLProtocol.mockError = nil
    StorageMockURLProtocol.responseQueue = []
  }

  // MARK: - Upload URL Tests

  func testGetUploadUrlSuccess() async throws {
    let expectedUrl = StorageUploadUrl(
      file_id: "file-1",
      upload_url: "https://s3.example.com/presigned-url",
      method: "PUT",
      expires_in: 3600,
      path: "uploads/file.txt",
      bucket: "test-bucket"
    )

    let jsonData = try JSONEncoder().encode(expectedUrl)
    StorageMockURLProtocol.mockData = jsonData
    StorageMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/storage/upload-url/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.storage.getUploadUrl(
      path: "uploads/file.txt",
      contentType: "text/plain"
    )

    XCTAssertEqual(result.file_id, "file-1")
    XCTAssertTrue(result.upload_url.contains("s3.example.com"))
  }

  func testConfirmUploadSuccess() async throws {
    let expectedObject = StorageObject(
      id: "obj-1",
      path: "uploads/file.txt",
      original_name: "file.txt",
      content_type: "text/plain",
      size: 1024,
      status: "confirmed",
      metadata: [:],
      thumbnails: [:],
      download_url: "https://storage.example.com/file.txt",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedObject)
    StorageMockURLProtocol.mockData = jsonData
    StorageMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/storage/confirm/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.storage.confirmUpload(fileId: "obj-1")

    XCTAssertEqual(result.original_name, "file.txt")
    XCTAssertEqual(result.size, 1024)
  }

  // MARK: - File Operations Tests

  func testListFilesSuccess() async throws {
    let files = [
      StorageObject(
        id: "obj-1",
        path: "uploads/file1.txt",
        original_name: "file1.txt",
        content_type: "text/plain",
        size: 1024,
        status: "confirmed",
        metadata: [:],
        thumbnails: [:],
        download_url: "https://storage.example.com/file1.txt",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z"
      ),
      StorageObject(
        id: "obj-2",
        path: "uploads/file2.txt",
        original_name: "file2.txt",
        content_type: "text/plain",
        size: 2048,
        status: "confirmed",
        metadata: [:],
        thumbnails: [:],
        download_url: "https://storage.example.com/file2.txt",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z"
      )
    ]

    let response = PaginatedResponse(
      count: 2,
      next: nil,
      previous: nil,
      results: files
    )

    let jsonData = try JSONEncoder().encode(response)
    StorageMockURLProtocol.mockData = jsonData
    StorageMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/storage/files/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.storage.listFiles()

    XCTAssertEqual(result.count, 2)
    XCTAssertEqual(result.results.count, 2)
  }

  func testGetFileSuccess() async throws {
    let expectedFile = StorageObject(
      id: "obj-1",
      path: "uploads/file.txt",
      original_name: "file.txt",
      content_type: "text/plain",
      size: 1024,
      status: "confirmed",
      metadata: [:],
      thumbnails: [:],
      download_url: "https://storage.example.com/file.txt",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedFile)
    StorageMockURLProtocol.mockData = jsonData
    StorageMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/storage/files/file.txt/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.storage.getFile(path: "file.txt")

    XCTAssertEqual(result.original_name, "file.txt")
  }

  func testDeleteFileSuccess() async throws {
    StorageMockURLProtocol.mockData = Data()
    StorageMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/storage/files/file.txt/")!,
      statusCode: 204,
      httpVersion: nil,
      headerFields: nil
    )

    try await firebase.storage.deleteFile(path: "file.txt")
  }

  // MARK: - Upload Helper Tests

  func testUploadSuccess() async throws {
    let uploadUrl = StorageUploadUrl(
      file_id: "obj-1",
      upload_url: "https://s3.example.com/presigned-url",
      method: "PUT",
      expires_in: 3600,
      path: "uploads/file.txt",
      bucket: "test-bucket"
    )

    let confirmObject = StorageObject(
      id: "obj-1",
      path: "uploads/file.txt",
      original_name: "file.txt",
      content_type: "text/plain",
      size: 1024,
      status: "confirmed",
      metadata: [:],
      thumbnails: [:],
      download_url: "https://storage.example.com/file.txt",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    // Queue sequential responses for the three legs of upload():
    // 1) POST storage/upload-url/  2) PUT to the presigned URL  3) POST storage/confirm/
    let okResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )!
    StorageMockURLProtocol.responseQueue = [
      (try JSONEncoder().encode(uploadUrl), okResponse),
      (Data(), okResponse),
      (try JSONEncoder().encode(confirmObject), okResponse),
    ]

    let fileData = "test file content".data(using: .utf8)!

    let result = try await firebase.storage.upload(
      data: fileData,
      path: "uploads/file.txt",
      contentType: "text/plain"
    )

    XCTAssertEqual(result.original_name, "file.txt")
    XCTAssertEqual(result.id, "obj-1")
  }
}

final class RemoteConfigServiceTests: XCTestCase {
  var firebase: OwnFirebase!
  var remoteConfigService: RemoteConfigService!

  override func setUp() {
    super.setUp()
    URLProtocol.registerClass(ConfigMockURLProtocol.self)

    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [ConfigMockURLProtocol.self]

    firebase = OwnFirebase(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      )
    )
    remoteConfigService = firebase.remoteConfig
  }

  override func tearDown() {
    super.tearDown()
    URLProtocol.unregisterClass(ConfigMockURLProtocol.self)
    ConfigMockURLProtocol.mockData = nil
    ConfigMockURLProtocol.mockResponse = nil
    ConfigMockURLProtocol.mockError = nil
  }

  // MARK: - Parameter Tests

  func testListParametersSuccess() async throws {
    let parameters = [
      RemoteConfigParameter(
        id: "param-1",
        key: "api_version",
        default_value: "v1",
        description: "API version",
        value_type: "string"
      ),
      RemoteConfigParameter(
        id: "param-2",
        key: "max_retries",
        default_value: "3",
        description: "Max retries",
        value_type: "number"
      )
    ]

    let response = PaginatedResponse(
      count: 2,
      next: nil,
      previous: nil,
      results: parameters
    )

    let jsonData = try JSONEncoder().encode(response)
    ConfigMockURLProtocol.mockData = jsonData
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await remoteConfigService.listParameters()

    XCTAssertEqual(result.count, 2)
    XCTAssertEqual(result.results[0].key, "api_version")
  }

  func testListParametersWithCache() async throws {
    let parameters = [
      RemoteConfigParameter(
        id: "param-1",
        key: "api_version",
        default_value: "v1",
        description: "API version",
        value_type: "string"
      )
    ]

    let response = PaginatedResponse(
      count: 1,
      next: nil,
      previous: nil,
      results: parameters
    )

    let jsonData = try JSONEncoder().encode(response)
    ConfigMockURLProtocol.mockData = jsonData
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    // First call - fetches from server
    let result1 = try await remoteConfigService.listParameters(useCache: true)

    // Second call - should use cache
    let result2 = try await remoteConfigService.listParameters(useCache: true)

    XCTAssertEqual(result1.count, 1)
    XCTAssertEqual(result2.count, 1)
  }

  func testGetParameterSuccess() async throws {
    let expectedParameter = RemoteConfigParameter(
      id: "param-1",
      key: "api_version",
      default_value: "v1",
      description: "API version",
      value_type: "string"
    )

    let jsonData = try JSONEncoder().encode(expectedParameter)
    ConfigMockURLProtocol.mockData = jsonData
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/param-1/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await remoteConfigService.getParameter(id: "param-1")

    XCTAssertEqual(result.key, "api_version")
    XCTAssertEqual(result.default_value, "v1")
  }

  func testCreateParameterSuccess() async throws {
    let expectedParameter = RemoteConfigParameter(
      id: "param-1",
      key: "new_param",
      default_value: "default",
      description: "A new parameter",
      value_type: "string"
    )

    let jsonData = try JSONEncoder().encode(expectedParameter)
    ConfigMockURLProtocol.mockData = jsonData
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let input = RemoteConfigParameterInput(
      key: "new_param",
      defaultValue: "default",
      description: "A new parameter",
      valueType: "string"
    )

    let result = try await remoteConfigService.createParameter(input)

    XCTAssertEqual(result.key, "new_param")
  }

  func testUpdateParameterSuccess() async throws {
    let expectedParameter = RemoteConfigParameter(
      id: "param-1",
      key: "api_version",
      default_value: "v2",
      description: "API version",
      value_type: "string"
    )

    let jsonData = try JSONEncoder().encode(expectedParameter)
    ConfigMockURLProtocol.mockData = jsonData
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/param-1/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let input = RemoteConfigParameterInput(
      key: "api_version",
      defaultValue: "v2",
      description: "API version",
      valueType: "string"
    )

    let result = try await remoteConfigService.updateParameter(id: "param-1", updates: input)

    XCTAssertEqual(result.default_value, "v2")
  }

  func testDeleteParameterSuccess() async throws {
    ConfigMockURLProtocol.mockData = Data()
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/param-1/")!,
      statusCode: 204,
      httpVersion: nil,
      headerFields: nil
    )

    try await remoteConfigService.deleteParameter(id: "param-1")
  }

  // MARK: - Condition Tests

  func testListConditionsSuccess() async throws {
    let conditions = [
      ConfigCondition(
        id: "cond-1",
        name: "iOS only",
        expression: "device.os == 'ios'",
        value: "v1"
      )
    ]

    let jsonData = try JSONEncoder().encode(conditions)
    ConfigMockURLProtocol.mockData = jsonData
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/param-1/conditions/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await remoteConfigService.listConditions(configId: "param-1")

    XCTAssertEqual(result.count, 1)
    XCTAssertEqual(result[0].name, "iOS only")
  }

  func testCreateConditionSuccess() async throws {
    let expectedCondition = ConfigCondition(
      id: "cond-1",
      name: "iOS only",
      expression: "device.os == 'ios'",
      value: "v1"
    )

    let jsonData = try JSONEncoder().encode(expectedCondition)
    ConfigMockURLProtocol.mockData = jsonData
    ConfigMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/config/parameters/param-1/conditions/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let input = ConfigConditionInput(
      name: "iOS only",
      expression: "device.os == 'ios'",
      value: "v1"
    )

    let result = try await remoteConfigService.createCondition(
      configId: "param-1",
      condition: input
    )

    XCTAssertEqual(result.name, "iOS only")
  }

  // MARK: - Cache Management Tests

  func testClearCache() {
    remoteConfigService.clearCache()
    // Cache should be cleared
  }

  func testSetCacheTTL() {
    remoteConfigService.setCacheTTL(7200) // 2 hours
    // TTL should be updated
  }
}

final class CrashlyticsServiceTests: XCTestCase {
  var firebase: OwnFirebase!
  var crashlyticsService: CrashlyticsService!

  override func setUp() {
    super.setUp()
    URLProtocol.registerClass(CrashlyticsMockURLProtocol.self)

    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [CrashlyticsMockURLProtocol.self]

    firebase = OwnFirebase(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      )
    )
    crashlyticsService = firebase.crashlytics
  }

  override func tearDown() {
    super.tearDown()
    URLProtocol.unregisterClass(CrashlyticsMockURLProtocol.self)
    CrashlyticsMockURLProtocol.mockData = nil
    CrashlyticsMockURLProtocol.mockResponse = nil
    CrashlyticsMockURLProtocol.mockError = nil
  }

  // MARK: - Crash Report Tests

  func testReportCrashSuccess() async throws {
    let expectedReport = CrashReport(
      id: "crash-1",
      exception_type: "NSException",
      message: "Test crash",
      stack_trace: "Stack trace here",
      occurred_at: "2024-01-01T00:00:00Z",
      app_version: "1.0.0",
      platform: "iOS"
    )

    let jsonData = try JSONEncoder().encode(expectedReport)
    CrashlyticsMockURLProtocol.mockData = jsonData
    CrashlyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/crashlytics/reports/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await crashlyticsService.reportCrash(
      exceptionType: "NSException",
      message: "Test crash",
      stackTrace: "Stack trace here",
      appVersion: "1.0.0",
      platform: "iOS"
    )

    XCTAssertEqual(result.exception_type, "NSException")
    XCTAssertEqual(result.message, "Test crash")
  }

  // MARK: - Crash Batch Tests

  func testReportCrashBatchedAndFlush() async throws {
    let responseMessage = MessageResponse(detail: "Crashes reported")

    let jsonData = try JSONEncoder().encode(responseMessage)
    CrashlyticsMockURLProtocol.mockData = jsonData
    CrashlyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/crashlytics/reports/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    crashlyticsService.reportCrashBatched(
      exceptionType: "NSException",
      message: "Crash 1",
      stackTrace: "Stack trace",
      appVersion: "1.0.0",
      platform: "iOS"
    )

    try await crashlyticsService.flushReports()
  }

  // MARK: - Crash Groups Tests

  func testListCrashGroupsSuccess() async throws {
    let groups = [
      CrashGroup(
        id: "group-1",
        exception_type: "NSException",
        message_summary: "Test crash",
        occurrence_count: 5,
        affected_users: 3,
        first_seen: "2024-01-01T00:00:00Z",
        last_seen: "2024-01-02T00:00:00Z",
        status: "open"
      )
    ]

    let response = PaginatedResponse(
      count: 1,
      next: nil,
      previous: nil,
      results: groups
    )

    let jsonData = try JSONEncoder().encode(response)
    CrashlyticsMockURLProtocol.mockData = jsonData
    CrashlyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/crashlytics/groups/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await crashlyticsService.listCrashGroups()

    XCTAssertEqual(result.count, 1)
    XCTAssertEqual(result.results[0].occurrence_count, 5)
  }

  // MARK: - Performance Trace Tests

  func testRecordTraceSuccess() async throws {
    let expectedTrace = PerformanceTrace(
      id: "trace-1",
      name: "main_screen_load",
      duration_ms: 2500,
      started_at: "2024-01-01T00:00:00Z",
      attributes: ["screen": "home"],
      metrics: ["frame_rate": 60.0]
    )

    let jsonData = try JSONEncoder().encode(expectedTrace)
    CrashlyticsMockURLProtocol.mockData = jsonData
    CrashlyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/crashlytics/traces/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await crashlyticsService.recordTrace(
      name: "main_screen_load",
      durationMs: 2500,
      startedAt: "2024-01-01T00:00:00Z",
      attributes: ["screen": "home"],
      metrics: ["frame_rate": 60.0]
    )

    XCTAssertEqual(result.name, "main_screen_load")
    XCTAssertEqual(result.duration_ms, 2500)
  }

  // MARK: - Network Request Tests

  func testRecordNetworkRequestSuccess() async throws {
    let expectedRecord = NetworkRequestRecord(
      id: "net-1",
      url: "https://api.example.com/data",
      method: "GET",
      status_code: 200,
      duration_ms: 500,
      request_size: 100,
      response_size: 5000,
      timestamp: "2024-01-01T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedRecord)
    CrashlyticsMockURLProtocol.mockData = jsonData
    CrashlyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/crashlytics/network/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await crashlyticsService.recordNetworkRequest(
      url: "https://api.example.com/data",
      method: "GET",
      statusCode: 200,
      durationMs: 500,
      requestSize: 100,
      responseSize: 5000
    )

    XCTAssertEqual(result.url, "https://api.example.com/data")
    XCTAssertEqual(result.status_code, 200)
  }

  // MARK: - Crash Summary Tests

  func testGetCrashSummary() async throws {
    let expectedSummary = CrashSummary(
      total_crashes: 150,
      crash_free_users_percentage: 95.5,
      affected_users: 50,
      open_issues: 5
    )

    let jsonData = try JSONEncoder().encode(expectedSummary)
    CrashlyticsMockURLProtocol.mockData = jsonData
    CrashlyticsMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/crashlytics/summary/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await crashlyticsService.getCrashSummary()

    XCTAssertEqual(result.total_crashes, 150)
    XCTAssertEqual(result.crash_free_users_percentage, 95.5)
  }
}

// MARK: - Mock URL Protocols

class StorageMockURLProtocol: URLProtocol {
  static var mockData: Data?
  static var mockResponse: HTTPURLResponse?
  static var mockError: Error?
  // Optional FIFO queue for tests that exercise multiple sequential requests
  // (e.g. upload-url -> presigned PUT -> confirm) where each leg needs its own response.
  static var responseQueue: [(Data, HTTPURLResponse)] = []

  override class func canInit(with request: URLRequest) -> Bool {
    return true
  }

  override class func canonicalRequest(for request: URLRequest) -> URLRequest {
    return request
  }

  override func startLoading() {
    if let error = StorageMockURLProtocol.mockError {
      client?.urlProtocol(self, didFailWithError: error)
    } else if !StorageMockURLProtocol.responseQueue.isEmpty {
      let (data, response) = StorageMockURLProtocol.responseQueue.removeFirst()
      client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
      client?.urlProtocol(self, didLoad: data)
      client?.urlProtocolDidFinishLoading(self)
    } else if let response = StorageMockURLProtocol.mockResponse {
      client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
      client?.urlProtocol(self, didLoad: StorageMockURLProtocol.mockData ?? Data())
      client?.urlProtocolDidFinishLoading(self)
    }
  }

  override func stopLoading() {}
}

class ConfigMockURLProtocol: URLProtocol {
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
    if let error = ConfigMockURLProtocol.mockError {
      client?.urlProtocol(self, didFailWithError: error)
    } else if let response = ConfigMockURLProtocol.mockResponse {
      client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
      client?.urlProtocol(self, didLoad: ConfigMockURLProtocol.mockData ?? Data())
      client?.urlProtocolDidFinishLoading(self)
    }
  }

  override func stopLoading() {}
}

class CrashlyticsMockURLProtocol: URLProtocol {
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
    if let error = CrashlyticsMockURLProtocol.mockError {
      client?.urlProtocol(self, didFailWithError: error)
    } else if let response = CrashlyticsMockURLProtocol.mockResponse {
      client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
      client?.urlProtocol(self, didLoad: CrashlyticsMockURLProtocol.mockData ?? Data())
      client?.urlProtocolDidFinishLoading(self)
    }
  }

  override func stopLoading() {}
}
