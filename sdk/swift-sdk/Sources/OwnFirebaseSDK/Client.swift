import Foundation

// MARK: - Retry Configuration

public struct RetryConfig {
  public let maxAttempts: Int
  public let initialDelayMs: Int
  public let maxDelayMs: Int
  public let backoffMultiplier: Double
  public let retryableStatusCodes: Set<Int>

  public init(
    maxAttempts: Int = 3,
    initialDelayMs: Int = 100,
    maxDelayMs: Int = 10000,
    backoffMultiplier: Double = 2.0,
    retryableStatusCodes: Set<Int> = [408, 429, 500, 502, 503, 504]
  ) {
    self.maxAttempts = maxAttempts
    self.initialDelayMs = initialDelayMs
    self.maxDelayMs = maxDelayMs
    self.backoffMultiplier = backoffMultiplier
    self.retryableStatusCodes = retryableStatusCodes
  }
}

// MARK: - HTTP Request Options

public struct RequestOptions {
  public var noAuth: Bool = false
  public var query: [String: String]?

  public init(noAuth: Bool = false, query: [String: String]? = nil) {
    self.noAuth = noAuth
    self.query = query
  }
}

// MARK: - OwnFirebaseClient

open class OwnFirebaseClient {
  public let config: OwnFirebaseConfig
  public let retryConfig: RetryConfig

  private var accessToken: String?
  private let urlSession: URLSession
  private let jsonDecoder: JSONDecoder
  private let jsonEncoder: JSONEncoder

  public init(config: OwnFirebaseConfig, retryConfig: RetryConfig = RetryConfig()) {
    self.config = config
    self.retryConfig = retryConfig
    self.accessToken = config.accessToken

    let sessionConfig = URLSessionConfiguration.default
    sessionConfig.timeoutIntervalForRequest = 30
    sessionConfig.timeoutIntervalForResource = 300
    sessionConfig.waitsForConnectivity = true

    self.urlSession = URLSession(configuration: sessionConfig)

    self.jsonDecoder = JSONDecoder()
    self.jsonDecoder.dateDecodingStrategy = .iso8601

    self.jsonEncoder = JSONEncoder()
    self.jsonEncoder.dateEncodingStrategy = .iso8601
  }

  // MARK: - Token Management

  public func setAccessToken(_ token: String) {
    self.accessToken = token
  }

  public func getAccessToken() -> String? {
    return accessToken
  }

  // MARK: - URL Construction

  public func projectUrl(_ path: String) -> String {
    guard let projectId = config.projectId else {
      return "\(config.baseUrl)/api/projects/INVALID/\(path)"
    }
    return "\(config.baseUrl)/api/projects/\(projectId)/\(path)"
  }

  // MARK: - Request Methods

  public func request<T: Decodable>(
    _ method: String,
    url: String,
    body: Encodable? = nil,
    options: RequestOptions = RequestOptions()
  ) async throws -> T {
    return try await requestWithRetry(
      method: method,
      url: url,
      body: body,
      options: options,
      attempt: 1
    )
  }

  public func requestData(
    _ method: String,
    url: String,
    body: Encodable? = nil,
    options: RequestOptions = RequestOptions()
  ) async throws -> Data {
    return try await requestDataWithRetry(
      method: method,
      url: url,
      body: body,
      options: options,
      attempt: 1
    )
  }

  public func requestVoid(
    _ method: String,
    url: String,
    body: Encodable? = nil,
    options: RequestOptions = RequestOptions()
  ) async throws {
    _ = try await requestWithRetry(
      method: method,
      url: url,
      body: body,
      options: options,
      attempt: 1
    ) as EmptyResponse
  }

  // MARK: - Private Request Methods

  private func requestWithRetry<T: Decodable>(
    method: String,
    url: String,
    body: Encodable?,
    options: RequestOptions,
    attempt: Int
  ) async throws -> T {
    do {
      let data = try await requestDataWithRetry(
        method: method,
        url: url,
        body: body,
        options: options,
        attempt: attempt
      )

      if T.self == EmptyResponse.self {
        return EmptyResponse() as! T
      }

      return try jsonDecoder.decode(T.self, from: data)
    } catch let error as DecodingError {
      throw OwnFirebaseError.decodingError(error)
    } catch let error as URLError {
      throw OwnFirebaseError.networkError(error)
    } catch let error as OwnFirebaseError {
      throw error
    } catch {
      throw error
    }
  }

  private func requestDataWithRetry(
    method: String,
    url: String,
    body: Encodable?,
    options: RequestOptions,
    attempt: Int
  ) async throws -> Data {
    do {
      let (data, response) = try await performRequest(
        method: method,
        url: url,
        body: body,
        options: options
      )

      guard let httpResponse = response as? HTTPURLResponse else {
        throw OwnFirebaseError.invalidResponse
      }

      if httpResponse.statusCode == 204 {
        return Data()
      }

      guard httpResponse.statusCode >= 200 && httpResponse.statusCode < 300 else {
        let apiError = try parseErrorResponse(data, statusCode: httpResponse.statusCode)
        throw OwnFirebaseError.apiError(apiError)
      }

      return data
    } catch let error as OwnFirebaseError {
      if shouldRetry(error: error, attempt: attempt) {
        let delay = calculateBackoffDelay(attempt: attempt)
        try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000))
        return try await requestDataWithRetry(
          method: method,
          url: url,
          body: body,
          options: options,
          attempt: attempt + 1
        )
      }
      throw error
    } catch let urlError as URLError {
      if shouldRetry(urlError: urlError, attempt: attempt) {
        let delay = calculateBackoffDelay(attempt: attempt)
        try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000))
        return try await requestDataWithRetry(
          method: method,
          url: url,
          body: body,
          options: options,
          attempt: attempt + 1
        )
      }
      throw OwnFirebaseError.networkError(urlError)
    } catch {
      throw error
    }
  }

  private func performRequest(
    method: String,
    url: String,
    body: Encodable?,
    options: RequestOptions
  ) async throws -> (Data, URLResponse) {
    var urlComponents = URLComponents(string: url)
    if let query = options.query {
      urlComponents?.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
    }

    guard let finalUrl = urlComponents?.url ?? URL(string: url) else {
      throw OwnFirebaseError.invalidURL
    }

    var request = URLRequest(url: finalUrl)
    request.httpMethod = method
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    if !options.noAuth, let token = accessToken {
      request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    }

    if let body = body, !(body is EmptyRequest) {
      request.httpBody = try jsonEncoder.encode(body)
    }

    return try await urlSession.data(for: request)
  }

  private func parseErrorResponse(_ data: Data, statusCode: Int) throws -> APIError {
    do {
      if let errorResponse = try? jsonDecoder.decode(ErrorResponse.self, from: data) {
        return APIError(
          status: statusCode,
          message: errorResponse.description,
          detail: nil
        )
      }

      if let dict = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
        let detail = AnyCodable(dict)
        return APIError(
          status: statusCode,
          message: HTTPURLResponse.localizedString(forStatusCode: statusCode),
          detail: detail
        )
      }
    } catch {
      // Fallback to status code message
    }

    return APIError(
      status: statusCode,
      message: HTTPURLResponse.localizedString(forStatusCode: statusCode),
      detail: nil
    )
  }

  // MARK: - Retry Logic

  private func shouldRetry(error: OwnFirebaseError, attempt: Int) -> Bool {
    guard attempt < retryConfig.maxAttempts else { return false }

    switch error {
    case .apiError(let apiError):
      return retryConfig.retryableStatusCodes.contains(apiError.status)
    case .networkError(let urlError):
      return shouldRetry(urlError: urlError, attempt: attempt)
    default:
      return false
    }
  }

  private func shouldRetry(urlError: URLError, attempt: Int) -> Bool {
    guard attempt < retryConfig.maxAttempts else { return false }

    let retryableErrors: [URLError.Code] = [
      .timedOut,
      .networkConnectionLost,
      .notConnectedToInternet,
      .serverCertificateUntrusted,
      .cannotLoadFromNetwork,
    ]

    return retryableErrors.contains(urlError.code)
  }

  private func calculateBackoffDelay(attempt: Int) -> Int {
    let exponentialDelay = Int(Double(retryConfig.initialDelayMs) * pow(retryConfig.backoffMultiplier, Double(attempt - 1)))
    return min(exponentialDelay, retryConfig.maxDelayMs)
  }
}

// MARK: - Helper Types

struct EmptyRequest: Encodable {}

struct EmptyResponse: Decodable {}
