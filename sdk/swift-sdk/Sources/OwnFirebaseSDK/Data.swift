import Foundation

public class DataService: OwnFirebaseClient {
  // MARK: - Collections

  public func listCollections() async throws -> [DataCollection] {
    return try await request(
      "GET",
      url: projectUrl("collections/")
    )
  }

  public func createCollection(name: String) async throws -> DataCollection {
    let body = CreateCollectionRequest(name: name)
    return try await request(
      "POST",
      url: projectUrl("collections/"),
      body: body
    )
  }

  // MARK: - Documents

  public func listDocuments(
    collection: String,
    filters: [String: String]? = nil
  ) async throws -> PaginatedResponse<DataDocument> {
    var options = RequestOptions()
    options.query = filters

    return try await request(
      "GET",
      url: projectUrl("collections/\(collection)/docs/"),
      options: options
    )
  }

  public func getDocument(collection: String, docId: String) async throws -> DataDocument {
    return try await request(
      "GET",
      url: projectUrl("collections/\(collection)/docs/\(docId)/")
    )
  }

  public func createDocument(
    collection: String,
    data: [String: AnyCodable]
  ) async throws -> DataDocument {
    let body = CreateDocumentRequest(data: data)
    return try await request(
      "POST",
      url: projectUrl("collections/\(collection)/docs/"),
      body: body
    )
  }

  public func updateDocument(
    collection: String,
    docId: String,
    data: [String: AnyCodable]
  ) async throws -> DataDocument {
    let body = UpdateDocumentRequest(data: data)
    return try await request(
      "PATCH",
      url: projectUrl("collections/\(collection)/docs/\(docId)/"),
      body: body
    )
  }

  public func replaceDocument(
    collection: String,
    docId: String,
    data: [String: AnyCodable]
  ) async throws -> DataDocument {
    let body = ReplaceDocumentRequest(data: data)
    return try await request(
      "PUT",
      url: projectUrl("collections/\(collection)/docs/\(docId)/"),
      body: body
    )
  }

  public func deleteDocument(collection: String, docId: String) async throws {
    try await requestVoid(
      "DELETE",
      url: projectUrl("collections/\(collection)/docs/\(docId)/")
    )
  }

  // MARK: - Batch / Transactions

  public func writeBatch(operations: [WriteBatchOperation]) async throws -> WriteBatchResult {
    let body = WriteBatchRequest(operations: operations)
    return try await request(
      "POST",
      url: projectUrl("transaction/"),
      body: body
    )
  }

  // MARK: - Security Rules

  public func getRules() async throws -> RulesResponse {
    return try await request(
      "GET",
      url: "\(config.baseUrl)/api/v1/rules/"
    )
  }

  public func updateRules(_ rules: String) async throws -> RulesResponse {
    let body = UpdateRulesRequest(rules: rules)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/rules/",
      body: body
    )
  }

  public func testRules(
    rule: String,
    context: [String: AnyCodable]
  ) async throws -> TestRulesResponse {
    let body = TestRulesRequest(rule: rule, context: context)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/rules/test/",
      body: body
    )
  }
}

// MARK: - Request Types

private struct CreateCollectionRequest: Encodable {
  let name: String
}

private struct CreateDocumentRequest: Encodable {
  let data: [String: AnyCodable]
}

private struct UpdateDocumentRequest: Encodable {
  let data: [String: AnyCodable]
}

private struct ReplaceDocumentRequest: Encodable {
  let data: [String: AnyCodable]
}

private struct WriteBatchRequest: Encodable {
  let operations: [WriteBatchOperation]
}

private struct UpdateRulesRequest: Encodable {
  let rules: String
}

public struct RulesResponse: Codable {
  public let rules: String
}

private struct TestRulesRequest: Encodable {
  let rule: String
  let context: [String: AnyCodable]
}

public struct TestRulesResponse: Codable {
  public let allowed: Bool
  public let reason: String?
}
