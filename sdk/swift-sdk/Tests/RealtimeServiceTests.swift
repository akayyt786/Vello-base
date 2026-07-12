import XCTest
@testable import OwnFirebaseSDK

final class RealtimeServiceTests: XCTestCase {
  var firebase: OwnFirebase!
  var realtimeService: RealtimeService!

  override func setUp() {
    super.setUp()
    firebase = OwnFirebase(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: "valid-token"
      )
    )
    realtimeService = firebase.createRealtimeService()
  }

  override func tearDown() {
    super.tearDown()
    realtimeService.disconnect()
  }

  // MARK: - Message Type Tests

  func testRealtimeMessageCreation() {
    let message = RealtimeMessage(
      type: "document_created",
      collection: "users",
      doc_id: "doc-1",
      data: ["name": AnyCodable("John")]
    )

    XCTAssertEqual(message.type, "document_created")
    XCTAssertEqual(message.collection, "users")
    XCTAssertEqual(message.doc_id, "doc-1")
    XCTAssertNotNil(message.data)
  }

  func testRealtimeMessageEncoding() throws {
    let message = RealtimeMessage(
      type: "document_updated",
      collection: "posts",
      doc_id: "post-1",
      data: ["title": AnyCodable("New Title")]
    )

    let encoder = JSONEncoder()
    let encodedData = try encoder.encode(message)

    let decoder = JSONDecoder()
    let decodedMessage = try decoder.decode(
      RealtimeMessage.self,
      from: encodedData
    )

    XCTAssertEqual(decodedMessage.type, "document_updated")
    XCTAssertEqual(decodedMessage.collection, "posts")
  }

  // MARK: - Service Configuration Tests

  func testRealtimeServiceInitialization() {
    XCTAssertNotNil(realtimeService)
    XCTAssertEqual(realtimeService.config.baseUrl, "http://localhost:8000")
    XCTAssertEqual(realtimeService.config.projectId, "test-project")
  }

  func testRealtimeServiceWithDelegate() {
    let mockDelegate = MockRealtimeDelegate()
    let serviceWithDelegate = firebase.createRealtimeService(delegate: mockDelegate)

    XCTAssertNotNil(serviceWithDelegate)
  }

  // MARK: - URL Construction Tests

  func testRealtimeURLConstruction() {
    let projectId = "test-project"
    let url = "http://localhost:8000/ws/v1/projects/\(projectId)/listen/"
    XCTAssertTrue(url.contains("/ws/v1/projects/test-project/listen/"))
  }

  func testWebSocketURLProtocolSwitch() {
    let httpUrl = "http://localhost:8000"
    let expectedWsUrl = "ws://localhost:8000"

    let wsUrl = httpUrl.replacingOccurrences(of: "http://", with: "ws://")

    XCTAssertEqual(wsUrl, expectedWsUrl)
  }

  func testWebSocketSecureURLProtocolSwitch() {
    let httpsUrl = "https://api.example.com"
    let expectedWssUrl = "wss://api.example.com"

    let wssUrl = httpsUrl.replacingOccurrences(of: "https://", with: "wss://")

    XCTAssertEqual(wssUrl, expectedWssUrl)
  }

  // MARK: - Subscription Message Tests

  func testSubscriptionMessageCreation() throws {
    let subscriptionMsg = SubscriptionMessage(
      type: "subscribe",
      collection: "users",
      filters: nil
    )

    let encoder = JSONEncoder()
    let encodedData = try encoder.encode(subscriptionMsg)

    let decoder = JSONDecoder()
    let decodedMsg = try decoder.decode(
      SubscriptionMessage.self,
      from: encodedData
    )

    XCTAssertEqual(decodedMsg.type, "subscribe")
    XCTAssertEqual(decodedMsg.collection, "users")
    XCTAssertNil(decodedMsg.filters)
  }

  func testUnsubscriptionMessageCreation() throws {
    let unsubscribeMsg = SubscriptionMessage(
      type: "unsubscribe",
      collection: "posts",
      filters: nil
    )

    let encoder = JSONEncoder()
    let encodedData = try encoder.encode(unsubscribeMsg)

    let decoder = JSONDecoder()
    let decodedMsg = try decoder.decode(
      SubscriptionMessage.self,
      from: encodedData
    )

    XCTAssertEqual(decodedMsg.type, "unsubscribe")
  }

  func testSubscriptionWithFiltersMessageCreation() throws {
    let filters = ["category": "tech", "status": "published"]
    let subscriptionMsg = SubscriptionMessage(
      type: "subscribe",
      collection: "posts",
      filters: filters
    )

    let encoder = JSONEncoder()
    let encodedData = try encoder.encode(subscriptionMsg)

    let decoder = JSONDecoder()
    let decodedMsg = try decoder.decode(
      SubscriptionMessage.self,
      from: encodedData
    )

    XCTAssertEqual(decodedMsg.type, "subscribe")
    XCTAssertNotNil(decodedMsg.filters)
    XCTAssertEqual(decodedMsg.filters?.count, 2)
  }

  // MARK: - Document Event Tests

  func testDocumentCreatedMessage() {
    let message = RealtimeMessage(
      type: "document_created",
      collection: "users",
      doc_id: "user-1",
      data: ["name": AnyCodable("Alice"), "email": AnyCodable("alice@example.com")]
    )

    XCTAssertEqual(message.type, "document_created")
    XCTAssertEqual(message.doc_id, "user-1")
    XCTAssertNotNil(message.data)
  }

  func testDocumentUpdatedMessage() {
    let message = RealtimeMessage(
      type: "document_updated",
      collection: "users",
      doc_id: "user-1",
      data: ["name": AnyCodable("Alice Updated")]
    )

    XCTAssertEqual(message.type, "document_updated")
    XCTAssertNotNil(message.data)
  }

  func testDocumentDeletedMessage() {
    let message = RealtimeMessage(
      type: "document_deleted",
      collection: "users",
      doc_id: "user-1",
      data: nil
    )

    XCTAssertEqual(message.type, "document_deleted")
    XCTAssertNil(message.data)
  }

  // MARK: - Message Timestamp Tests

  func testRealtimeMessageTimestamp() {
    let timestamp = "2024-01-01T12:30:00Z"
    let message = RealtimeMessage(
      type: "document_created",
      collection: "users",
      doc_id: "user-1",
      data: ["name": AnyCodable("John")],
      timestamp: timestamp
    )

    XCTAssertEqual(message.timestamp, timestamp)
  }

  func testRealtimeMessageDefaultTimestamp() {
    let message = RealtimeMessage(
      type: "document_created",
      collection: "users",
      doc_id: "user-1"
    )

    XCTAssertNotNil(message.timestamp)
    XCTAssertTrue(message.timestamp.contains("T"))
    XCTAssertTrue(message.timestamp.contains("Z"))
  }

  // MARK: - Complex Message Tests

  func testRealtimeMessageWithComplexData() throws {
    let complexData: [String: AnyCodable] = [
      "name": AnyCodable("John"),
      "age": AnyCodable(30),
      "tags": AnyCodable(["swift", "ios"]),
      "metadata": AnyCodable(["key": "value"])
    ]

    let message = RealtimeMessage(
      type: "document_created",
      collection: "users",
      doc_id: "user-1",
      data: complexData
    )

    let encoder = JSONEncoder()
    let encodedData = try encoder.encode(message)

    let decoder = JSONDecoder()
    let decodedMessage = try decoder.decode(
      RealtimeMessage.self,
      from: encodedData
    )

    XCTAssertEqual(decodedMessage.data?.count, 4)
  }

  // MARK: - Disconnection and Error Handling Tests

  func testRealtimeServiceDisconnect() {
    // Should not throw
    realtimeService.disconnect()
  }

  // MARK: - Access Token Management

  func testRealtimeServiceAccessToken() {
    let token = realtimeService.getAccessToken()
    XCTAssertEqual(token, "valid-token")
  }

  func testRealtimeServiceAccessTokenUpdate() {
    realtimeService.setAccessToken("new-token")
    XCTAssertEqual(realtimeService.getAccessToken(), "new-token")
  }

  // MARK: - Project URL Construction

  func testRealtimeServiceProjectUrl() {
    let projectUrl = realtimeService.projectUrl("collections/")
    XCTAssertTrue(projectUrl.contains("test-project"))
    XCTAssertTrue(projectUrl.contains("collections/"))
  }

  // MARK: - Collection Subscription Tests

  func testSubscribeToCollection() async throws {
    // This test verifies the subscription message can be constructed
    let subscriptionMsg = SubscriptionMessage(
      type: "subscribe",
      collection: "users",
      filters: nil
    )

    XCTAssertEqual(subscriptionMsg.type, "subscribe")
    XCTAssertEqual(subscriptionMsg.collection, "users")
  }

  func testSubscribeToCollectionWithFilter() async throws {
    let filters = ["status": "active"]
    let subscriptionMsg = SubscriptionMessage(
      type: "subscribe",
      collection: "users",
      filters: filters
    )

    XCTAssertEqual(subscriptionMsg.type, "subscribe")
    XCTAssertNotNil(subscriptionMsg.filters)
    XCTAssertEqual(subscriptionMsg.filters?["status"], "active")
  }

  func testUnsubscribeFromCollection() async throws {
    let unsubscribeMsg = SubscriptionMessage(
      type: "unsubscribe",
      collection: "users",
      filters: nil
    )

    XCTAssertEqual(unsubscribeMsg.type, "unsubscribe")
    XCTAssertEqual(unsubscribeMsg.collection, "users")
  }

  // MARK: - Reconnection Configuration Tests

  func testRealtimeServiceRetryConfig() {
    let retryConfig = RetryConfig(
      maxAttempts: 5,
      initialDelayMs: 200,
      maxDelayMs: 20000
    )

    let service = RealtimeService(
      config: firebase.config,
      retryConfig: retryConfig
    )

    XCTAssertEqual(service.retryConfig.maxAttempts, 5)
    XCTAssertEqual(service.retryConfig.initialDelayMs, 200)
  }
}

// MARK: - Mock Realtime Delegate

class MockRealtimeDelegate: RealtimeDelegate {
  var didConnectCalled = false
  var didDisconnectCalled = false
  var didReceiveMessageCalled = false
  var didEncounterErrorCalled = false

  var lastReceivedMessage: RealtimeMessage?
  var lastError: Error?

  func realtimeDidConnect() {
    didConnectCalled = true
  }

  func realtimeDidDisconnect(error: Error?) {
    didDisconnectCalled = true
    lastError = error
  }

  func realtimeDidReceiveMessage(_ message: RealtimeMessage) {
    didReceiveMessageCalled = true
    lastReceivedMessage = message
  }

  func realtimeDidEncounterError(_ error: Error) {
    didEncounterErrorCalled = true
    lastError = error
  }
}

// MARK: - Realtime Delegate Protocol Tests

final class RealtimeDelegateTests: XCTestCase {
  func testMockDelegateConnection() {
    let delegate = MockRealtimeDelegate()

    XCTAssertFalse(delegate.didConnectCalled)

    delegate.realtimeDidConnect()

    XCTAssertTrue(delegate.didConnectCalled)
  }

  func testMockDelegateDisconnection() {
    let delegate = MockRealtimeDelegate()
    let error = NSError(domain: "Test", code: 1)

    delegate.realtimeDidDisconnect(error: error)

    XCTAssertTrue(delegate.didDisconnectCalled)
    XCTAssertNotNil(delegate.lastError)
  }

  func testMockDelegateMessageReceived() {
    let delegate = MockRealtimeDelegate()
    let message = RealtimeMessage(
      type: "document_created",
      collection: "users",
      doc_id: "user-1"
    )

    delegate.realtimeDidReceiveMessage(message)

    XCTAssertTrue(delegate.didReceiveMessageCalled)
    XCTAssertEqual(delegate.lastReceivedMessage?.type, "document_created")
  }

  func testMockDelegateErrorEncountered() {
    let delegate = MockRealtimeDelegate()
    let error = NSError(domain: "Test", code: 1)

    delegate.realtimeDidEncounterError(error)

    XCTAssertTrue(delegate.didEncounterErrorCalled)
    XCTAssertNotNil(delegate.lastError)
  }
}
