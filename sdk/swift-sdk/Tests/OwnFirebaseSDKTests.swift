import XCTest
@testable import OwnFirebaseSDK

final class OwnFirebaseSDKTests: XCTestCase {
  var firebase: OwnFirebase!
  let testBaseUrl = "http://localhost:8000"
  let testProjectId = "test-project"

  override func setUp() {
    super.setUp()
    firebase = OwnFirebase(
      config: OwnFirebaseConfig(
        baseUrl: testBaseUrl,
        projectId: testProjectId,
        accessToken: "test-token"
      )
    )
  }

  func testInitialization() {
    XCTAssertEqual(firebase.config.baseUrl, testBaseUrl)
    XCTAssertEqual(firebase.config.projectId, testProjectId)
    XCTAssertNotNil(firebase.auth)
    XCTAssertNotNil(firebase.data)
    XCTAssertNotNil(firebase.storage)
    XCTAssertNotNil(firebase.analytics)
    XCTAssertNotNil(firebase.remoteConfig)
    XCTAssertNotNil(firebase.crashlytics)
  }

  func testProjectUrlConstruction() {
    let projectUrl = firebase.auth.projectUrl("test/path/")
    XCTAssertTrue(projectUrl.contains("test-project"))
    XCTAssertTrue(projectUrl.contains("test/path/"))
  }

  func testAccessTokenManagement() {
    let newToken = "new-test-token"
    firebase.setAccessToken(newToken)
    XCTAssertEqual(firebase.getAccessToken(), newToken)
  }

  func testConfigCreation() {
    let config = OwnFirebaseConfig(
      baseUrl: "https://api.example.com",
      projectId: "my-project",
      accessToken: "token123"
    )

    XCTAssertEqual(config.baseUrl, "https://api.example.com")
    XCTAssertEqual(config.projectId, "my-project")
    XCTAssertEqual(config.accessToken, "token123")
  }

  func testConfigUrlNormalization() {
    let config1 = OwnFirebaseConfig(baseUrl: "https://api.example.com/")
    let config2 = OwnFirebaseConfig(baseUrl: "https://api.example.com")

    XCTAssertEqual(config1.baseUrl, config2.baseUrl)
  }

  func testRealtimeServiceCreation() {
    let realtime = firebase.createRealtimeService()
    XCTAssertNotNil(realtime)
  }
}

final class TypesTests: XCTestCase {
  func testAuthTokensDecodable() throws {
    let json = """
    {
      "access": "access-token",
      "refresh": "refresh-token",
      "user_id": "user-123",
      "email": "test@example.com"
    }
    """

    let decoder = JSONDecoder()
    let tokens = try decoder.decode(
      AuthTokens.self,
      from: json.data(using: .utf8)!
    )

    XCTAssertEqual(tokens.access, "access-token")
    XCTAssertEqual(tokens.refresh, "refresh-token")
    XCTAssertEqual(tokens.user_id, "user-123")
    XCTAssertEqual(tokens.email, "test@example.com")
  }

  func testUserDecodable() throws {
    let json = """
    {
      "id": "user-123",
      "email": "test@example.com",
      "username": "testuser",
      "first_name": "Test",
      "last_name": "User",
      "is_active": true
    }
    """

    let decoder = JSONDecoder()
    let user = try decoder.decode(
      User.self,
      from: json.data(using: .utf8)!
    )

    XCTAssertEqual(user.id, "user-123")
    XCTAssertEqual(user.email, "test@example.com")
    XCTAssertEqual(user.username, "testuser")
    XCTAssertTrue(user.is_active)
  }

  func testDataDocumentDecodable() throws {
    let json = """
    {
      "id": "doc-123",
      "collection": "users",
      "data": {
        "name": "John",
        "age": 30,
        "active": true
      },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-02T00:00:00Z"
    }
    """

    let decoder = JSONDecoder()
    decoder.dateDecodingStrategy = .iso8601
    let doc = try decoder.decode(
      DataDocument.self,
      from: json.data(using: .utf8)!
    )

    XCTAssertEqual(doc.id, "doc-123")
    XCTAssertEqual(doc.collection, "users")
    XCTAssertEqual(doc.data.count, 3)
  }

  func testAPIErrorDecodable() throws {
    let json = """
    {
      "status": 401,
      "message": "Unauthorized"
    }
    """

    let decoder = JSONDecoder()
    let error = try decoder.decode(
      APIError.self,
      from: json.data(using: .utf8)!
    )

    XCTAssertEqual(error.status, 401)
    XCTAssertEqual(error.message, "Unauthorized")
  }

  func testPaginatedResponseDecodable() throws {
    let json = """
    {
      "count": 100,
      "next": "http://example.com/page2",
      "previous": null,
      "results": [
        {
          "id": "doc-1",
          "name": "Document 1",
          "document_count": 5
        }
      ]
    }
    """

    let decoder = JSONDecoder()
    let response = try decoder.decode(
      PaginatedResponse<DataCollection>.self,
      from: json.data(using: .utf8)!
    )

    XCTAssertEqual(response.count, 100)
    XCTAssertEqual(response.results.count, 1)
    XCTAssertNotNil(response.next)
    XCTAssertNil(response.previous)
  }
}

final class RetryConfigTests: XCTestCase {
  func testDefaultRetryConfig() {
    let config = RetryConfig()

    XCTAssertEqual(config.maxAttempts, 3)
    XCTAssertEqual(config.initialDelayMs, 100)
    XCTAssertEqual(config.maxDelayMs, 10000)
    XCTAssertEqual(config.backoffMultiplier, 2.0)
    XCTAssertTrue(config.retryableStatusCodes.contains(500))
    XCTAssertTrue(config.retryableStatusCodes.contains(503))
  }

  func testCustomRetryConfig() {
    let config = RetryConfig(
      maxAttempts: 5,
      initialDelayMs: 200,
      maxDelayMs: 20000,
      backoffMultiplier: 1.5,
      retryableStatusCodes: [429, 500]
    )

    XCTAssertEqual(config.maxAttempts, 5)
    XCTAssertEqual(config.initialDelayMs, 200)
    XCTAssertEqual(config.maxDelayMs, 20000)
    XCTAssertEqual(config.backoffMultiplier, 1.5)
    XCTAssertEqual(config.retryableStatusCodes.count, 2)
  }
}

final class AnyCodableTests: XCTestCase {
  func testAnyCodableString() throws {
    let value = AnyCodable("hello")
    let encoded = try JSONEncoder().encode(value)
    let decoded = try JSONDecoder().decode(AnyCodable.self, from: encoded)

    XCTAssertEqual(decoded.value as? String, "hello")
  }

  func testAnyCodableInt() throws {
    let value = AnyCodable(42)
    let encoded = try JSONEncoder().encode(value)
    let decoded = try JSONDecoder().decode(AnyCodable.self, from: encoded)

    XCTAssertEqual(decoded.value as? Int, 42)
  }

  func testAnyCodableBool() throws {
    let value = AnyCodable(true)
    let encoded = try JSONEncoder().encode(value)
    let decoded = try JSONDecoder().decode(AnyCodable.self, from: encoded)

    XCTAssertEqual(decoded.value as? Bool, true)
  }

  func testAnyCodableArray() throws {
    let value = AnyCodable([1, "two", 3.0])
    let encoded = try JSONEncoder().encode(value)
    let decoded = try JSONDecoder().decode(AnyCodable.self, from: encoded)

    XCTAssertNotNil(decoded.value as? [Any])
  }

  func testAnyCodableDictionary() throws {
    let dict: [String: Any] = ["key": "value", "number": 42]
    let value = AnyCodable(dict)
    let encoded = try JSONEncoder().encode(value)
    let decoded = try JSONDecoder().decode(AnyCodable.self, from: encoded)

    XCTAssertNotNil(decoded.value as? [String: Any])
  }
}
