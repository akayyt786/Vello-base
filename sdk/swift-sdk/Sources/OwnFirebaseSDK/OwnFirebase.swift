import Foundation

public class OwnFirebase {
  public let config: OwnFirebaseConfig
  public let retryConfig: RetryConfig

  // Services
  public lazy var auth: AuthService = AuthService(config: config, retryConfig: retryConfig)
  public lazy var data: DataService = DataService(config: config, retryConfig: retryConfig)
  public lazy var storage: StorageService = StorageService(config: config, retryConfig: retryConfig)
  public lazy var analytics: AnalyticsService = AnalyticsService(config: config, retryConfig: retryConfig)
  public lazy var remoteConfig: RemoteConfigService = RemoteConfigService(config: config, retryConfig: retryConfig)
  public lazy var crashlytics: CrashlyticsService = CrashlyticsService(config: config, retryConfig: retryConfig)

  public init(config: OwnFirebaseConfig, retryConfig: RetryConfig = RetryConfig()) {
    self.config = config
    self.retryConfig = retryConfig
  }

  // MARK: - Session Management

  public func setAccessToken(_ token: String) {
    auth.setAccessToken(token)
    data.setAccessToken(token)
    storage.setAccessToken(token)
    analytics.setAccessToken(token)
    remoteConfig.setAccessToken(token)
    crashlytics.setAccessToken(token)
  }

  public func setProjectId(_ projectId: String) {
    // Note: config.projectId is immutable, so this is a no-op
    // Consider using a mutable config property if this needs to update
    _ = projectId
  }

  // MARK: - Realtime

  public func createRealtimeService(delegate: RealtimeDelegate? = nil) -> RealtimeService {
    return RealtimeService(config: config, retryConfig: retryConfig, delegate: delegate)
  }

  // MARK: - Utility

  public func getAccessToken() -> String? {
    return auth.getAccessToken()
  }
}

// MARK: - Convenience Initialization

public extension OwnFirebase {
  static func initialize(
    baseUrl: String,
    projectId: String? = nil,
    accessToken: String? = nil,
    retryConfig: RetryConfig = RetryConfig()
  ) -> OwnFirebase {
    let config = OwnFirebaseConfig(
      baseUrl: baseUrl,
      projectId: projectId,
      accessToken: accessToken
    )
    return OwnFirebase(config: config, retryConfig: retryConfig)
  }

  static func initializeWithDefaults(baseUrl: String) -> OwnFirebase {
    return OwnFirebase.initialize(baseUrl: baseUrl)
  }
}
