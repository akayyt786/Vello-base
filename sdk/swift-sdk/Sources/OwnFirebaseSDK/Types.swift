import Foundation

// MARK: - Configuration

public struct OwnFirebaseConfig {
  public let baseUrl: String
  public let projectId: String?
  public let accessToken: String?

  public init(baseUrl: String, projectId: String? = nil, accessToken: String? = nil) {
    self.baseUrl = baseUrl.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    self.projectId = projectId
    self.accessToken = accessToken
  }
}

// MARK: - Errors

public struct APIError: Error, Decodable {
  public let status: Int
  public let message: String
  public let detail: AnyCodable?

  public init(status: Int, message: String, detail: AnyCodable? = nil) {
    self.status = status
    self.message = message
    self.detail = detail
  }
}

public enum OwnFirebaseError: Error, LocalizedError {
  case networkError(URLError)
  case invalidResponse
  case decodingError(DecodingError)
  case apiError(APIError)
  case missingProjectId
  case missingAccessToken
  case invalidURL
  case retryExhausted(Int)

  public var errorDescription: String? {
    switch self {
    case .networkError(let error):
      return "Network error: \(error.localizedDescription)"
    case .invalidResponse:
      return "Invalid response from server"
    case .decodingError(let error):
      return "Failed to decode response: \(error.localizedDescription)"
    case .apiError(let error):
      return "API error: \(error.message)"
    case .missingProjectId:
      return "Project ID is required for this operation"
    case .missingAccessToken:
      return "Access token is required for this operation"
    case .invalidURL:
      return "Invalid URL"
    case .retryExhausted(let attempts):
      return "Request failed after \(attempts) attempts"
    }
  }
}

// MARK: - Type Erasure for Any Codable

public struct AnyCodable: Codable {
  public let value: Any

  public init(_ value: Any) {
    self.value = value
  }

  public init(from decoder: Decoder) throws {
    let container = try decoder.singleValueContainer()

    if container.decodeNil() {
      self.value = NSNull()
    } else if let bool = try? container.decode(Bool.self) {
      self.value = bool
    } else if let int = try? container.decode(Int.self) {
      self.value = int
    } else if let double = try? container.decode(Double.self) {
      self.value = double
    } else if let string = try? container.decode(String.self) {
      self.value = string
    } else if let array = try? container.decode([AnyCodable].self) {
      self.value = array.map { $0.value }
    } else if let dict = try? container.decode([String: AnyCodable].self) {
      self.value = dict.mapValues { $0.value }
    } else {
      throw DecodingError.dataCorruptedError(
        in: container,
        debugDescription: "Cannot decode AnyCodable"
      )
    }
  }

  public func encode(to encoder: Encoder) throws {
    var container = encoder.singleValueContainer()

    switch value {
    case is NSNull:
      try container.encodeNil()
    case let bool as Bool:
      try container.encode(bool)
    case let int as Int:
      try container.encode(int)
    case let double as Double:
      try container.encode(double)
    case let string as String:
      try container.encode(string)
    case let array as [Any]:
      try container.encode(array.map { AnyCodable($0) })
    case let dict as [String: Any]:
      try container.encode(dict.mapValues { AnyCodable($0) })
    default:
      let context = EncodingError.Context(
        codingPath: container.codingPath,
        debugDescription: "Cannot encode AnyCodable with value \(type(of: value))"
      )
      throw EncodingError.invalidValue(value, context)
    }
  }
}

// MARK: - Auth Types

public struct AuthTokens: Codable {
  public let access: String
  public let refresh: String
  public let user_id: String
  public let email: String?

  public init(access: String, refresh: String, user_id: String, email: String? = nil) {
    self.access = access
    self.refresh = refresh
    self.user_id = user_id
    self.email = email
  }
}

public struct User: Codable {
  public let id: String
  public let email: String
  public let username: String
  public let first_name: String
  public let last_name: String
  public let is_active: Bool

  public init(id: String, email: String, username: String, first_name: String,
              last_name: String, is_active: Bool) {
    self.id = id
    self.email = email
    self.username = username
    self.first_name = first_name
    self.last_name = last_name
    self.is_active = is_active
  }
}

public struct LinkedSocialAccount: Codable {
  public let id: String
  public let provider: String
  public let provider_uid: String
  public let email: String?
  public let linked_at: String
}

public struct MFADevice: Codable {
  public let id: String
  public let type: String
  public let name: String
  public let confirmed: Bool
  public let created_at: String
}

public struct CustomToken: Codable {
  public let custom_token: String
}

// MARK: - Data Types

public struct DataDocument: Codable {
  public let id: String
  public let collection: String
  public let data: [String: AnyCodable]
  public let created_at: String
  public let updated_at: String
}

public struct DataCollection: Codable {
  public let id: String
  public let name: String
  public let document_count: Int
}

public struct WriteBatchOperation: Codable {
  public let op: String // "set", "update", "delete"
  public let collection: String
  public let doc_id: String?
  public let data: [String: AnyCodable]?

  public init(op: String, collection: String, doc_id: String? = nil, data: [String: AnyCodable]? = nil) {
    self.op = op
    self.collection = collection
    self.doc_id = doc_id
    self.data = data
  }
}

public struct WriteBatchResult: Codable {
  public let written: Int
  public let errors: [AnyCodable]
}

// MARK: - Storage Types

public struct StorageObject: Codable {
  public let id: String
  public let name: String
  public let size: Int
  public let content_type: String
  public let url: String
  public let created_at: String
}

public struct StorageUploadUrl: Codable {
  public let upload_url: String
  public let object_key: String
  public let expires_at: String
}

// MARK: - Analytics Types

public struct AnalyticsEvent: Codable {
  public let id: String
  public let name: String
  public let params: [String: AnyCodable]
  public let timestamp: String
  public let user_id: String?
  public let session_id: String?
}

public struct UserProperty: Codable {
  public let id: String
  public let name: String
  public let value: String
  public let user_id: String
}

// MARK: - Remote Config Types

public struct RemoteConfigParameter: Codable {
  public let id: String
  public let key: String
  public let default_value: String
  public let description: String
  public let value_type: String // "string", "boolean", "number", "json"
}

// MARK: - Crashlytics Types

public struct CrashReport: Codable {
  public let id: String
  public let exception_type: String
  public let message: String
  public let stack_trace: String
  public let occurred_at: String
  public let app_version: String
  public let platform: String
}

public struct PerformanceTrace: Codable {
  public let id: String
  public let name: String
  public let duration_ms: Int
  public let started_at: String
  public let attributes: [String: String]
  public let metrics: [String: Double]
}

public struct CrashGroup: Codable {
  public let id: String
  public let exception_type: String
  public let message_summary: String
  public let occurrence_count: Int
  public let affected_users: Int
  public let first_seen: String
  public let last_seen: String
  public let status: String
}

// MARK: - Pagination

public struct PaginatedResponse<T: Codable>: Codable {
  public let count: Int
  public let next: String?
  public let previous: String?
  public let results: [T]
}

// MARK: - Request/Response Helpers

public struct ErrorResponse: Decodable {
  public let detail: String?
  public let error: String?
  public let message: String?

  public var description: String {
    return detail ?? error ?? message ?? "Unknown error"
  }
}

public struct SuccessResponse<T: Codable>: Codable {
  public let data: T?
  public let detail: String?
}
