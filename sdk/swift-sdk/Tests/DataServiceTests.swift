import XCTest
@testable import OwnFirebaseSDK

final class DataServiceTests: XCTestCase {
  var firebase: OwnFirebase!

  override func setUp() {
    super.setUp()
    URLProtocol.registerClass(DataMockURLProtocol.self)

    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [DataMockURLProtocol.self]

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
    URLProtocol.unregisterClass(DataMockURLProtocol.self)
    DataMockURLProtocol.mockData = nil
    DataMockURLProtocol.mockResponse = nil
    DataMockURLProtocol.mockError = nil
  }

  // MARK: - Collection Tests

  func testListCollectionsSuccess() async throws {
    let collections = [
      DataCollection(id: "col-1", name: "users", document_count: 5),
      DataCollection(id: "col-2", name: "posts", document_count: 10)
    ]

    let jsonData = try JSONEncoder().encode(collections)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.listCollections()

    XCTAssertEqual(result.count, 2)
    XCTAssertEqual(result[0].name, "users")
  }

  func testCreateCollectionSuccess() async throws {
    let expectedCollection = DataCollection(
      id: "col-1",
      name: "users",
      document_count: 0
    )

    let jsonData = try JSONEncoder().encode(expectedCollection)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.createCollection(name: "users")

    XCTAssertEqual(result.name, "users")
    XCTAssertEqual(result.document_count, 0)
  }

  // MARK: - Document CRUD Tests

  func testCreateDocumentSuccess() async throws {
    let documentData: [String: AnyCodable] = [
      "name": AnyCodable("John Doe"),
      "age": AnyCodable(30),
      "email": AnyCodable("john@example.com")
    ]

    let expectedDoc = DataDocument(
      id: "doc-1",
      collection: "users",
      data: documentData,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedDoc)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.createDocument(
      collection: "users",
      data: documentData
    )

    XCTAssertEqual(result.id, "doc-1")
    XCTAssertEqual(result.collection, "users")
    XCTAssertEqual(result.data.count, 3)
  }

  func testReadDocumentSuccess() async throws {
    let documentData: [String: AnyCodable] = [
      "name": AnyCodable("John Doe"),
      "age": AnyCodable(30)
    ]

    let expectedDoc = DataDocument(
      id: "doc-1",
      collection: "users",
      data: documentData,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedDoc)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/doc-1/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.getDocument(
      collection: "users",
      docId: "doc-1"
    )

    XCTAssertEqual(result.id, "doc-1")
    XCTAssertEqual(result.data.count, 2)
  }

  func testUpdateDocumentSuccess() async throws {
    let updateData: [String: AnyCodable] = [
      "age": AnyCodable(31)
    ]

    let expectedDoc = DataDocument(
      id: "doc-1",
      collection: "users",
      data: updateData,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-02T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedDoc)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/doc-1/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.updateDocument(
      collection: "users",
      docId: "doc-1",
      data: updateData
    )

    XCTAssertEqual(result.id, "doc-1")
  }

  func testReplaceDocumentSuccess() async throws {
    let newData: [String: AnyCodable] = [
      "name": AnyCodable("Jane Doe"),
      "age": AnyCodable(28)
    ]

    let expectedDoc = DataDocument(
      id: "doc-1",
      collection: "users",
      data: newData,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-02T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedDoc)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/doc-1/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.replaceDocument(
      collection: "users",
      docId: "doc-1",
      data: newData
    )

    XCTAssertEqual(result.id, "doc-1")
  }

  func testDeleteDocumentSuccess() async throws {
    DataMockURLProtocol.mockData = Data()
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/doc-1/")!,
      statusCode: 204,
      httpVersion: nil,
      headerFields: nil
    )

    try await firebase.data.deleteDocument(
      collection: "users",
      docId: "doc-1"
    )
  }

  // MARK: - List Documents Tests

  func testListDocumentsSuccess() async throws {
    let doc1 = DataDocument(
      id: "doc-1",
      collection: "users",
      data: ["name": AnyCodable("John")],
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let doc2 = DataDocument(
      id: "doc-2",
      collection: "users",
      data: ["name": AnyCodable("Jane")],
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let response = PaginatedResponse(
      count: 2,
      next: nil,
      previous: nil,
      results: [doc1, doc2]
    )

    let jsonData = try JSONEncoder().encode(response)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.listDocuments(collection: "users")

    XCTAssertEqual(result.count, 2)
    XCTAssertEqual(result.results.count, 2)
  }

  func testListDocumentsWithFilters() async throws {
    let doc = DataDocument(
      id: "doc-1",
      collection: "users",
      data: ["name": AnyCodable("John"), "age": AnyCodable(30)],
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let response = PaginatedResponse(
      count: 1,
      next: nil,
      previous: nil,
      results: [doc]
    )

    let jsonData = try JSONEncoder().encode(response)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.listDocuments(
      collection: "users",
      filters: ["age": "30"]
    )

    XCTAssertEqual(result.count, 1)
  }

  // MARK: - Batch/Transaction Tests

  func testWriteBatchSuccess() async throws {
    let operations = [
      WriteBatchOperation(op: "set", collection: "users", doc_id: "doc-1", data: ["name": AnyCodable("John")]),
      WriteBatchOperation(op: "update", collection: "users", doc_id: "doc-2", data: ["age": AnyCodable(30)]),
      WriteBatchOperation(op: "delete", collection: "users", doc_id: "doc-3")
    ]

    let expectedResult = WriteBatchResult(written: 3, errors: [])

    let jsonData = try JSONEncoder().encode(expectedResult)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/transaction/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.writeBatch(operations: operations)

    XCTAssertEqual(result.written, 3)
    XCTAssertEqual(result.errors.count, 0)
  }

  func testWriteBatchWithErrors() async throws {
    let operations = [
      WriteBatchOperation(op: "set", collection: "users", doc_id: "doc-1", data: ["name": AnyCodable("John")])
    ]

    let expectedResult = WriteBatchResult(
      written: 0,
      errors: [AnyCodable("Permission denied")]
    )

    let jsonData = try JSONEncoder().encode(expectedResult)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/transaction/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.writeBatch(operations: operations)

    XCTAssertEqual(result.written, 0)
    XCTAssertEqual(result.errors.count, 1)
  }

  // MARK: - Security Rules Tests

  func testGetRulesSuccess() async throws {
    let expectedResponse = RulesResponse(
      rules: "rules_version = '2'; allow read, write: if false;"
    )

    let jsonData = try JSONEncoder().encode(expectedResponse)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/rules/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.getRules()

    XCTAssertTrue(result.rules.contains("rules_version"))
  }

  func testUpdateRulesSuccess() async throws {
    let newRules = "rules_version = '2'; allow read: if true; allow write: if false;"
    let expectedResponse = RulesResponse(rules: newRules)

    let jsonData = try JSONEncoder().encode(expectedResponse)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/rules/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.updateRules(newRules)

    XCTAssertEqual(result.rules, newRules)
  }

  func testTestRulesAllow() async throws {
    let expectedResponse = TestRulesResponse(allowed: true, reason: nil)

    let jsonData = try JSONEncoder().encode(expectedResponse)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/rules/test/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.testRules(
      rule: "allow read: if true;",
      context: ["user_id": AnyCodable("123")]
    )

    XCTAssertTrue(result.allowed)
  }

  func testTestRulesDeny() async throws {
    let expectedResponse = TestRulesResponse(
      allowed: false,
      reason: "User not authenticated"
    )

    let jsonData = try JSONEncoder().encode(expectedResponse)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/rules/test/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.testRules(
      rule: "allow write: if false;",
      context: [:]
    )

    XCTAssertFalse(result.allowed)
  }

  // MARK: - Error Handling Tests

  func testGetDocumentNotFound() async throws {
    let errorResponse = APIError(status: 404, message: "Document not found")

    let jsonData = try JSONEncoder().encode(errorResponse)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/nonexistent/")!,
      statusCode: 404,
      httpVersion: nil,
      headerFields: nil
    )

    do {
      _ = try await firebase.data.getDocument(
        collection: "users",
        docId: "nonexistent"
      )
      XCTFail("Should throw error")
    } catch {
      XCTAssertTrue(error is OwnFirebaseError)
    }
  }

  func testDeleteNonexistentDocument() async throws {
    let errorResponse = APIError(status: 404, message: "Document not found")

    let jsonData = try JSONEncoder().encode(errorResponse)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/nonexistent/")!,
      statusCode: 404,
      httpVersion: nil,
      headerFields: nil
    )

    do {
      try await firebase.data.deleteDocument(
        collection: "users",
        docId: "nonexistent"
      )
      XCTFail("Should throw error")
    } catch {
      XCTAssertTrue(error is OwnFirebaseError)
    }
  }

  // MARK: - Complex Data Types Tests

  func testCreateDocumentWithComplexData() async throws {
    let complexData: [String: AnyCodable] = [
      "name": AnyCodable("John"),
      "age": AnyCodable(30),
      "tags": AnyCodable(["swift", "ios"]),
      "metadata": AnyCodable(["key": "value"])
    ]

    let expectedDoc = DataDocument(
      id: "doc-1",
      collection: "users",
      data: complexData,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z"
    )

    let jsonData = try JSONEncoder().encode(expectedDoc)
    DataMockURLProtocol.mockData = jsonData
    DataMockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/collections/users/docs/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.data.createDocument(
      collection: "users",
      data: complexData
    )

    XCTAssertEqual(result.id, "doc-1")
    XCTAssertEqual(result.data.count, 4)
  }
}

// MARK: - Mock URL Protocol

class DataMockURLProtocol: URLProtocol {
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
    if let error = DataMockURLProtocol.mockError {
      client?.urlProtocol(self, didFailWithError: error)
    } else if let response = DataMockURLProtocol.mockResponse {
      client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
      client?.urlProtocol(self, didLoad: DataMockURLProtocol.mockData ?? Data())
      client?.urlProtocolDidFinishLoading(self)
    }
  }

  override func stopLoading() {}
}
