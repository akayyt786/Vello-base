# OwnFirebase Swift SDK - API Reference

Complete API reference for all SDK classes and methods.

## Core Classes

### OwnFirebase

Main SDK class that bundles all services.

```swift
public class OwnFirebase {
  // Properties
  public let config: OwnFirebaseConfig
  public let retryConfig: RetryConfig
  public lazy var auth: AuthService
  public lazy var data: DataService
  public lazy var storage: StorageService
  public lazy var analytics: AnalyticsService
  public lazy var remoteConfig: RemoteConfigService
  public lazy var crashlytics: CrashlyticsService

  // Initialization
  public init(config: OwnFirebaseConfig, retryConfig: RetryConfig = RetryConfig())

  // Methods
  public func setAccessToken(_ token: String)
  public func setProjectId(_ projectId: String)
  public func createRealtimeService(delegate: RealtimeDelegate? = nil) -> RealtimeService
  public func getAccessToken() -> String?
}
```

### OwnFirebaseClient

Base class for all services, provides HTTP client functionality.

```swift
open class OwnFirebaseClient {
  public let config: OwnFirebaseConfig
  public let retryConfig: RetryConfig

  public init(config: OwnFirebaseConfig, retryConfig: RetryConfig = RetryConfig())
  
  public func setAccessToken(_ token: String)
  public func getAccessToken() -> String?
  public func projectUrl(_ path: String) -> String
  
  public func request<T: Decodable>(
    _ method: String,
    url: String,
    body: Encodable? = nil,
    options: RequestOptions = RequestOptions()
  ) async throws -> T
  
  public func requestData(
    _ method: String,
    url: String,
    body: Encodable? = nil,
    options: RequestOptions = RequestOptions()
  ) async throws -> Data
  
  public func requestVoid(
    _ method: String,
    url: String,
    body: Encodable? = nil,
    options: RequestOptions = RequestOptions()
  ) async throws
}
```

## Authentication Service

### AuthService

Handles all authentication operations.

```swift
public class AuthService: OwnFirebaseClient {
  // Core Auth
  public func register(
    email: String,
    password: String,
    username: String? = nil
  ) async throws -> AuthTokens
  
  public func login(email: String, password: String) async throws -> AuthTokens
  public func refreshToken(refresh: String) async throws -> TokenRefreshResponse
  public func logout(refresh: String) async throws
  public func getMe() async throws -> User
  public func anonymousSignIn() async throws -> AuthTokens
  public func setCustomClaims(_ claims: [String: AnyCodable]) async throws -> MessageResponse
  
  // Social Auth
  public func googleSignIn(idToken: String) async throws -> AuthTokens
  public func githubSignIn(accessToken: String) async throws -> AuthTokens
  public func listLinkedAccounts() async throws -> [LinkedSocialAccount]
  public func unlinkSocialAccount(_ accountId: String) async throws
  
  // Phone / OTP
  public func sendPhoneOTP(phoneNumber: String) async throws -> MessageResponse
  public func verifyPhoneOTP(phoneNumber: String, code: String) async throws -> AuthTokens
  
  // MFA
  public func enrollTOTP() async throws -> EnrollTOTPResponse
  public func confirmTOTP(code: String) async throws -> MessageResponse
  public func verifyTOTP(code: String) async throws -> AuthTokens
  public func enrollSMS(phoneNumber: String) async throws -> MessageResponse
  public func confirmSMS(deviceId: String, code: String) async throws -> MessageResponse
  public func verifySMS(deviceId: String, code: String) async throws -> AuthTokens
  public func sendSMSCode(deviceId: String) async throws -> MessageResponse
  public func listMFADevices() async throws -> [MFADevice]
  public func deleteMFADevice(_ deviceId: String) async throws
  
  // Magic Link
  public func sendMagicLink(email: String) async throws -> MessageResponse
  public func verifyMagicLink(token: String) async throws -> AuthTokens
  
  // Account Management
  public func upgradeAnonymous(
    email: String,
    password: String,
    password2: String
  ) async throws -> AuthTokens
  
  public func setPassword(
    newPassword: String,
    newPassword2: String,
    currentPassword: String? = nil
  ) async throws -> MessageResponse
  
  public func linkEmail(email: String, password: String) async throws -> MessageResponse
  public func verifyEmailChange(token: String) async throws -> MessageResponse
  
  // Custom Token
  public func issueCustomToken(
    userId: String,
    claims: [String: AnyCodable]? = nil
  ) async throws -> CustomToken
}
```

## Data Service

### DataService

Handles data operations (CRUD, collections, queries).

```swift
public class DataService: OwnFirebaseClient {
  // Collections
  public func listCollections() async throws -> [DataCollection]
  public func createCollection(name: String) async throws -> DataCollection
  
  // Documents
  public func listDocuments(
    collection: String,
    filters: [String: String]? = nil
  ) async throws -> PaginatedResponse<DataDocument>
  
  public func getDocument(collection: String, docId: String) async throws -> DataDocument
  
  public func createDocument(
    collection: String,
    data: [String: AnyCodable]
  ) async throws -> DataDocument
  
  public func updateDocument(
    collection: String,
    docId: String,
    data: [String: AnyCodable]
  ) async throws -> DataDocument
  
  public func replaceDocument(
    collection: String,
    docId: String,
    data: [String: AnyCodable]
  ) async throws -> DataDocument
  
  public func deleteDocument(collection: String, docId: String) async throws
  
  // Batch / Transactions
  public func writeBatch(operations: [WriteBatchOperation]) async throws -> WriteBatchResult
  
  // Security Rules
  public func getRules() async throws -> RulesResponse
  public func updateRules(_ rules: String) async throws -> RulesResponse
  public func testRules(
    rule: String,
    context: [String: AnyCodable]
  ) async throws -> TestRulesResponse
}
```

## Storage Service

### StorageService

Handles file storage operations.

```swift
public class StorageService: OwnFirebaseClient {
  // Upload URL Management
  public func getUploadUrl(
    filename: String,
    contentType: String,
    path: String? = nil
  ) async throws -> StorageUploadUrl
  
  public func confirmUpload(objectKey: String) async throws -> StorageObject
  
  // File Operations
  public func listFiles(prefix: String? = nil) async throws -> PaginatedResponse<StorageObject>
  public func getFile(path: String) async throws -> StorageObject
  public func deleteFile(path: String) async throws
  
  // High-Level Upload Helper
  public func upload(
    data: Data,
    filename: String,
    contentType: String,
    path: String? = nil
  ) async throws -> StorageObject
  
  // Download Helper
  public func downloadFile(url: String) async throws -> Data
}
```

## Analytics Service

### AnalyticsService

Handles analytics and event tracking with batching support.

```swift
public class AnalyticsService: OwnFirebaseClient {
  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    batchSize: Int = 50,
    batchFlushInterval: TimeInterval = 30
  )
  
  // Events
  public func logEvent(
    name: String,
    params: [String: AnyCodable]? = nil,
    userId: String? = nil,
    sessionId: String? = nil
  ) async throws -> AnalyticsEvent
  
  public func logEventBatched(
    name: String,
    params: [String: AnyCodable]? = nil,
    userId: String? = nil,
    sessionId: String? = nil
  )
  
  public func flushEventBatch() async throws
  public func listEvents(filters: [String: String]? = nil) async throws -> PaginatedResponse<AnalyticsEvent>
  
  // User Properties
  public func setUserProperty(name: String, value: String) async throws -> UserProperty
  public func listUserProperties() async throws -> PaginatedResponse<UserProperty>
  
  // Conversion Events
  public func listConversionEvents() async throws -> PaginatedResponse<ConversionEvent>
  public func markConversionEvent(name: String) async throws -> ConversionEvent
  
  // Query
  public func query(params: AnalyticsQueryParams) async throws -> AnalyticsQueryResult
}
```

## Remote Config Service

### RemoteConfigService

Handles remote configuration with caching support.

```swift
public class RemoteConfigService: OwnFirebaseClient {
  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    cacheTTL: TimeInterval = 3600
  )
  
  // Parameters
  public func listParameters(useCache: Bool = true) async throws -> PaginatedResponse<RemoteConfigParameter>
  public func getParameter(id: String) async throws -> RemoteConfigParameter
  public func createParameter(_ parameter: RemoteConfigParameterInput) async throws -> RemoteConfigParameter
  public func updateParameter(id: String, updates: RemoteConfigParameterInput) async throws -> RemoteConfigParameter
  public func deleteParameter(id: String) async throws
  
  // Conditions
  public func listConditions(configId: String) async throws -> [ConfigCondition]
  public func createCondition(
    configId: String,
    condition: ConfigConditionInput
  ) async throws -> ConfigCondition
  
  public func updateCondition(
    configId: String,
    conditionId: String,
    updates: ConfigConditionInput
  ) async throws -> ConfigCondition
  
  public func deleteCondition(configId: String, conditionId: String) async throws
  
  // Cache Management
  public func clearCache()
  public func setCacheTTL(_ ttl: TimeInterval)
}
```

## Crashlytics Service

### CrashlyticsService

Handles crash reporting and performance monitoring with batching support.

```swift
public class CrashlyticsService: OwnFirebaseClient {
  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    reportBatchSize: Int = 50,
    reportBatchInterval: TimeInterval = 60
  )
  
  // Crash Groups
  public func listCrashGroups(filters: [String: String]? = nil) async throws -> PaginatedResponse<CrashGroup>
  public func getCrashGroup(id: String) async throws -> CrashGroup
  
  // Crash Reports
  public func reportCrash(
    exceptionType: String,
    message: String,
    stackTrace: String,
    appVersion: String,
    platform: String,
    deviceInfo: [String: AnyCodable]? = nil
  ) async throws -> CrashReport
  
  public func reportCrashBatched(
    exceptionType: String,
    message: String,
    stackTrace: String,
    appVersion: String,
    platform: String,
    deviceInfo: [String: AnyCodable]? = nil
  )
  
  public func flushReports() async throws
  public func listCrashReports(filters: [String: String]? = nil) async throws -> PaginatedResponse<CrashReport>
  public func getCrashSummary() async throws -> CrashSummary
  
  // Performance Traces
  public func recordTrace(
    name: String,
    durationMs: Int,
    startedAt: String,
    attributes: [String: String]? = nil,
    metrics: [String: Double]? = nil
  ) async throws -> PerformanceTrace
  
  public func listTraces(filters: [String: String]? = nil) async throws -> PaginatedResponse<PerformanceTrace>
  
  // Network Requests
  public func recordNetworkRequest(
    url: String,
    method: String,
    statusCode: Int,
    durationMs: Int,
    requestSize: Int? = nil,
    responseSize: Int? = nil
  ) async throws -> NetworkRequestRecord
  
  public func listNetworkRequests(filters: [String: String]? = nil) async throws -> PaginatedResponse<NetworkRequestRecord>
}
```

## Realtime Service

### RealtimeService

Handles real-time updates via WebSocket.

```swift
public class RealtimeService: NSObject, OwnFirebaseClient, URLSessionWebSocketDelegate {
  public init(
    config: OwnFirebaseConfig,
    retryConfig: RetryConfig = RetryConfig(),
    delegate: RealtimeDelegate? = nil
  )
  
  // Connection Management
  public func connect() async throws
  public func disconnect()
  
  // Subscriptions
  public func subscribe(to collection: String) async throws
  public func subscribeWithFilter(
    to collection: String,
    filters: [String: String]
  ) async throws
  public func unsubscribe(from collection: String) async throws
}
```

### RealtimeDelegate

Protocol for handling real-time events.

```swift
public protocol RealtimeDelegate: AnyObject {
  func realtimeDidConnect()
  func realtimeDidDisconnect(error: Error?)
  func realtimeDidReceiveMessage(_ message: RealtimeMessage)
  func realtimeDidEncounterError(_ error: Error)
}
```

## Configuration Types

### OwnFirebaseConfig

SDK configuration.

```swift
public struct OwnFirebaseConfig {
  public let baseUrl: String
  public let projectId: String?
  public let accessToken: String?

  public init(baseUrl: String, projectId: String? = nil, accessToken: String? = nil)
}
```

### RetryConfig

Retry behavior configuration.

```swift
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
  )
}
```

### RequestOptions

HTTP request options.

```swift
public struct RequestOptions {
  public var noAuth: Bool
  public var query: [String: String]?

  public init(noAuth: Bool = false, query: [String: String]? = nil)
}
```

## Error Types

### OwnFirebaseError

Enumeration of SDK errors.

```swift
public enum OwnFirebaseError: Error, LocalizedError {
  case networkError(URLError)
  case invalidResponse
  case decodingError(DecodingError)
  case apiError(APIError)
  case missingProjectId
  case missingAccessToken
  case invalidURL
  case retryExhausted(Int)
}
```

### APIError

API error response.

```swift
public struct APIError: Error, Decodable {
  public let status: Int
  public let message: String
  public let detail: AnyCodable?
}
```

## Type-Safe Data Handling

### AnyCodable

Type-erased codable value for flexible JSON handling.

```swift
public struct AnyCodable: Codable {
  public let value: Any

  public init(_ value: Any)
  public init(from decoder: Decoder) throws
  public func encode(to encoder: Encoder) throws
}
```

## Response Types

### PaginatedResponse

Generic paginated response wrapper.

```swift
public struct PaginatedResponse<T: Codable>: Codable {
  public let count: Int
  public let next: String?
  public let previous: String?
  public let results: [T]
}
```

### RealtimeMessage

Real-time update message.

```swift
public struct RealtimeMessage: Codable {
  public let type: String
  public let collection: String
  public let doc_id: String
  public let data: [String: AnyCodable]?
  public let timestamp: String
}
```

## Thread Safety

- All async/await operations are safe to call from any thread
- Analytics batching is thread-safe (DispatchQueue)
- Crashlytics reporting is thread-safe (DispatchQueue)
- RemoteConfig caching is thread-safe (DispatchQueue)
- Realtime WebSocket operations are thread-safe (URLSession)
