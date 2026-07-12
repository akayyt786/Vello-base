import Foundation

public class RemoteConfigService: OwnFirebaseClient {
  private let cacheQueue = DispatchQueue(label: "com.ownfirebase.remoteconfig.cache")
  private var parameterCache: [String: RemoteConfigParameter] = [:]
  private var cacheTTL: TimeInterval = 3600 // 1 hour default
  private var lastCacheUpdate: Date?

  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    cacheTTL: TimeInterval = 3600
  ) {
    self.cacheTTL = cacheTTL
    super.init(config: config, retryConfig: retryConfig)
  }

  // MARK: - Parameters

  public func listParameters(useCache: Bool = true) async throws -> PaginatedResponse<RemoteConfigParameter> {
    if useCache, let cached = getCachedParameters() {
      return PaginatedResponse(
        count: cached.count,
        next: nil,
        previous: nil,
        results: cached
      )
    }

    let response: PaginatedResponse<RemoteConfigParameter> = try await request(
      "GET",
      url: projectUrl("config/parameters/")
    )

    cacheQueue.sync {
      parameterCache = Dictionary(uniqueKeysWithValues: response.results.map { ($0.id, $0) })
      lastCacheUpdate = Date()
    }

    return response
  }

  public func getParameter(id: String) async throws -> RemoteConfigParameter {
    if let cached = getCachedParameter(id: id) {
      return cached
    }

    let parameter: RemoteConfigParameter = try await request(
      "GET",
      url: projectUrl("config/parameters/\(id)/")
    )

    cacheQueue.sync {
      parameterCache[id] = parameter
    }

    return parameter
  }

  public func createParameter(_ parameter: RemoteConfigParameterInput) async throws -> RemoteConfigParameter {
    let created: RemoteConfigParameter = try await request(
      "POST",
      url: projectUrl("config/parameters/"),
      body: parameter
    )

    cacheQueue.sync {
      parameterCache[created.id] = created
      lastCacheUpdate = Date()
    }

    return created
  }

  public func updateParameter(id: String, updates: RemoteConfigParameterInput) async throws -> RemoteConfigParameter {
    let updated: RemoteConfigParameter = try await request(
      "PATCH",
      url: projectUrl("config/parameters/\(id)/"),
      body: updates
    )

    cacheQueue.sync {
      parameterCache[id] = updated
      lastCacheUpdate = Date()
    }

    return updated
  }

  public func deleteParameter(id: String) async throws {
    try await requestVoid(
      "DELETE",
      url: projectUrl("config/parameters/\(id)/")
    )

    _ = cacheQueue.sync {
      parameterCache.removeValue(forKey: id)
    }
  }

  // MARK: - Conditions

  public func listConditions(configId: String) async throws -> [ConfigCondition] {
    return try await request(
      "GET",
      url: projectUrl("config/parameters/\(configId)/conditions/")
    )
  }

  public func createCondition(
    configId: String,
    condition: ConfigConditionInput
  ) async throws -> ConfigCondition {
    return try await request(
      "POST",
      url: projectUrl("config/parameters/\(configId)/conditions/"),
      body: condition
    )
  }

  public func updateCondition(
    configId: String,
    conditionId: String,
    updates: ConfigConditionInput
  ) async throws -> ConfigCondition {
    return try await request(
      "PATCH",
      url: projectUrl("config/parameters/\(configId)/conditions/\(conditionId)/"),
      body: updates
    )
  }

  public func deleteCondition(configId: String, conditionId: String) async throws {
    try await requestVoid(
      "DELETE",
      url: projectUrl("config/parameters/\(configId)/conditions/\(conditionId)/")
    )
  }

  // MARK: - Cache Management

  public func clearCache() {
    cacheQueue.sync {
      parameterCache.removeAll()
      lastCacheUpdate = nil
    }
  }

  public func setCacheTTL(_ ttl: TimeInterval) {
    cacheQueue.sync {
      self.cacheTTL = ttl
    }
  }

  private func getCachedParameters() -> [RemoteConfigParameter]? {
    return cacheQueue.sync {
      guard let lastUpdate = lastCacheUpdate else { return nil }
      guard Date().timeIntervalSince(lastUpdate) < cacheTTL else { return nil }
      return Array(parameterCache.values)
    }
  }

  private func getCachedParameter(id: String) -> RemoteConfigParameter? {
    return cacheQueue.sync {
      guard let cached = parameterCache[id] else { return nil }
      guard let lastUpdate = lastCacheUpdate else { return nil }
      guard Date().timeIntervalSince(lastUpdate) < cacheTTL else { return nil }
      return cached
    }
  }
}

// MARK: - Request Types

public struct ConfigCondition: Codable {
  public let id: String
  public let name: String
  public let expression: String
  public let value: String

  public init(id: String, name: String, expression: String, value: String) {
    self.id = id
    self.name = name
    self.expression = expression
    self.value = value
  }
}

public struct ConfigConditionInput: Encodable {
  public let name: String
  public let expression: String
  public let value: String

  public init(name: String, expression: String, value: String) {
    self.name = name
    self.expression = expression
    self.value = value
  }
}

public struct RemoteConfigParameterInput: Encodable {
  public let key: String
  public let default_value: String
  public let description: String
  public let value_type: String

  public init(key: String, defaultValue: String, description: String, valueType: String) {
    self.key = key
    self.default_value = defaultValue
    self.description = description
    self.value_type = valueType
  }
}
