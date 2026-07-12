# OwnFirebase Swift SDK

A comprehensive Swift SDK for OwnFirebase, providing type-safe access to authentication, data storage, analytics, remote configuration, crash reporting, and real-time updates.

## Features

- **Authentication**: Login, registration, social auth (Google, GitHub), MFA (TOTP, SMS), magic links, anonymous auth
- **Data API**: CRUD operations, collections, batch writes, security rules
- **Storage**: File uploads/downloads with presigned URLs, direct uploads
- **Realtime**: WebSocket-based real-time document listeners with auto-reconnection
- **Analytics**: Event tracking, user properties, conversion events, batching
- **Remote Config**: Parameter management with built-in caching
- **Crashlytics**: Error reporting, performance traces, network monitoring
- **Error Handling**: Automatic retries with exponential backoff
- **Async/Await**: Full Swift Concurrency support

## Installation

### Swift Package Manager

Add to your `Package.swift`:

```swift
.package(url: "https://github.com/your-org/ownfirebase-swift-sdk.git", from: "1.0.0")
```

Or in Xcode: File → Add Packages → Enter the repository URL

## Quick Start

### Initialize the SDK

```swift
import OwnFirebaseSDK

let firebase = OwnFirebase(
  config: OwnFirebaseConfig(
    baseUrl: "https://api.example.com",
    projectId: "my-project",
    accessToken: nil  // Will be set after login
  )
)
```

Or use the convenience initializer:

```swift
let firebase = OwnFirebase.initialize(
  baseUrl: "https://api.example.com",
  projectId: "my-project"
)
```

### Authentication

```swift
// Register
let tokens = try await firebase.auth.register(
  email: "user@example.com",
  password: "secure-password",
  username: "john_doe"
)
firebase.setAccessToken(tokens.access)

// Login
let loginTokens = try await firebase.auth.login(
  email: "user@example.com",
  password: "password"
)
firebase.setAccessToken(loginTokens.access)

// Anonymous sign-in
let anonTokens = try await firebase.auth.anonymousSignIn()
firebase.setAccessToken(anonTokens.access)

// Get current user
let user = try await firebase.auth.getMe()

// Logout
try await firebase.auth.logout(refresh: loginTokens.refresh)
```

### Social Auth

```swift
// Google Sign-In
let tokens = try await firebase.auth.googleSignIn(idToken: googleIdToken)
firebase.setAccessToken(tokens.access)

// GitHub Sign-In
let tokens = try await firebase.auth.githubSignIn(accessToken: githubAccessToken)
firebase.setAccessToken(tokens.access)

// List linked accounts
let accounts = try await firebase.auth.listLinkedAccounts()

// Unlink social account
try await firebase.auth.unlinkSocialAccount(accountId)
```

### MFA (Multi-Factor Authentication)

```swift
// Enroll TOTP
let totp = try await firebase.auth.enrollTOTP()
// Display QR code: totp.totp_uri
// Share secret: totp.secret

// Confirm TOTP enrollment
try await firebase.auth.confirmTOTP(code: "123456")

// Verify with TOTP during login
let tokens = try await firebase.auth.verifyTOTP(code: "123456")

// SMS MFA
try await firebase.auth.enrollSMS(phoneNumber: "+1234567890")
try await firebase.auth.confirmSMS(deviceId: "device-id", code: "123456")
let tokens = try await firebase.auth.verifySMS(deviceId: "device-id", code: "123456")
```

### Data Operations

```swift
// Create a collection
let collection = try await firebase.data.createCollection(name: "users")

// List collections
let collections = try await firebase.data.listCollections()

// Create a document
let doc = try await firebase.data.createDocument(
  collection: "users",
  data: [
    "name": AnyCodable("John Doe"),
    "email": AnyCodable("john@example.com"),
    "age": AnyCodable(30)
  ]
)

// Get a document
let retrieved = try await firebase.data.getDocument(collection: "users", docId: doc.id)

// Update a document (merge)
let updated = try await firebase.data.updateDocument(
  collection: "users",
  docId: doc.id,
  data: ["age": AnyCodable(31)]
)

// Replace a document (overwrite)
let replaced = try await firebase.data.replaceDocument(
  collection: "users",
  docId: doc.id,
  data: ["age": AnyCodable(32)]
)

// List documents with filters
let results = try await firebase.data.listDocuments(
  collection: "users",
  filters: ["email": "john@example.com"]
)

// Delete a document
try await firebase.data.deleteDocument(collection: "users", docId: doc.id)

// Batch write
let operations: [WriteBatchOperation] = [
  WriteBatchOperation(op: "set", collection: "users", doc_id: "user-1", data: ["name": AnyCodable("Alice")]),
  WriteBatchOperation(op: "update", collection: "users", doc_id: "user-2", data: ["age": AnyCodable(25)]),
  WriteBatchOperation(op: "delete", collection: "users", doc_id: "user-3")
]
let result = try await firebase.data.writeBatch(operations: operations)
```

### Storage

```swift
// Get upload URL
let uploadUrl = try await firebase.storage.getUploadUrl(
  filename: "profile.jpg",
  contentType: "image/jpeg",
  path: "avatars/"
)

// Upload file (high-level helper)
let imageData = ... // your image data
let storageObject = try await firebase.storage.upload(
  data: imageData,
  filename: "profile.jpg",
  contentType: "image/jpeg",
  path: "avatars/"
)

// List files
let files = try await firebase.storage.listFiles(prefix: "avatars/")

// Get file info
let fileInfo = try await firebase.storage.getFile(path: "avatars/profile.jpg")

// Download file
let fileData = try await firebase.storage.downloadFile(url: fileInfo.url)

// Delete file
try await firebase.storage.deleteFile(path: "avatars/profile.jpg")
```

### Analytics

```swift
// Log an event
try await firebase.analytics.logEvent(
  name: "user_signup",
  params: ["source": AnyCodable("mobile_app")],
  userId: "user-123"
)

// Batch event logging (more efficient)
firebase.analytics.logEventBatched(
  name: "page_view",
  params: ["page": AnyCodable("home")]
)

// Flush pending events
try await firebase.analytics.flushEventBatch()

// Set user property
try await firebase.analytics.setUserProperty(
  name: "plan_type",
  value: "premium"
)

// Mark conversion event
let conversionEvent = try await firebase.analytics.markConversionEvent(name: "purchase")

// Query analytics
let results = try await firebase.analytics.query(
  params: AnalyticsQueryParams(
    metric: "user_count",
    dimension: "country",
    start_date: "2024-01-01",
    end_date: "2024-01-31"
  )
)
```

### Remote Config

```swift
// Fetch parameters (with caching)
let response = try await firebase.remoteConfig.listParameters(useCache: true)

// Get specific parameter
let parameter = try await firebase.remoteConfig.getParameter(id: "feature_flag_new_ui")

// Create parameter
let newParam = try await firebase.remoteConfig.createParameter(
  RemoteConfigParameterInput(
    key: "feature_flag_new_ui",
    defaultValue: "false",
    description: "Enable new UI",
    valueType: "boolean"
  )
)

// Update parameter
let updated = try await firebase.remoteConfig.updateParameter(
  id: parameter.id,
  updates: RemoteConfigParameterInput(
    key: parameter.key,
    defaultValue: "true",
    description: "Enable new UI",
    valueType: "boolean"
  )
)

// Manage conditions
let conditions = try await firebase.remoteConfig.listConditions(configId: parameter.id)

// Clear cache
firebase.remoteConfig.clearCache()

// Set custom cache TTL
firebase.remoteConfig.setCacheTTL(7200)  // 2 hours
```

### Crashlytics

```swift
// Report crash
try await firebase.crashlytics.reportCrash(
  exceptionType: "RuntimeException",
  message: "Application crashed",
  stackTrace: "...",
  appVersion: "1.0.0",
  platform: "iOS",
  deviceInfo: [
    "device_model": AnyCodable("iPhone 13"),
    "os_version": AnyCodable("17.0")
  ]
)

// Batch crash reporting
firebase.crashlytics.reportCrashBatched(
  exceptionType: "NetworkError",
  message: "Failed to fetch data",
  stackTrace: "...",
  appVersion: "1.0.0",
  platform: "iOS"
)

// Flush pending crashes
try await firebase.crashlytics.flushReports()

// Record performance trace
try await firebase.crashlytics.recordTrace(
  name: "database_query",
  durationMs: 250,
  startedAt: ISO8601DateFormatter().string(from: Date()),
  attributes: ["table": "users"],
  metrics: ["rows_affected": 100]
)

// Record network request
try await firebase.crashlytics.recordNetworkRequest(
  url: "https://api.example.com/users",
  method: "GET",
  statusCode: 200,
  durationMs: 150
)

// Get crash summary
let summary = try await firebase.crashlytics.getCrashSummary()
print("Total crashes: \(summary.total_crashes)")
print("Crash-free users: \(summary.crash_free_users_percentage)%")
```

### Real-time Listeners

```swift
class MyRealtimeDelegate: RealtimeDelegate {
  func realtimeDidConnect() {
    print("Connected to realtime updates")
  }

  func realtimeDidDisconnect(error: Error?) {
    print("Disconnected: \(error?.localizedDescription ?? "normal")")
  }

  func realtimeDidReceiveMessage(_ message: RealtimeMessage) {
    print("Received: \(message.type) for \(message.doc_id)")
  }

  func realtimeDidEncounterError(_ error: Error) {
    print("Error: \(error)")
  }
}

// Create realtime service
let delegate = MyRealtimeDelegate()
let realtime = firebase.createRealtimeService(delegate: delegate)

// Connect and subscribe
try await realtime.connect()
try await realtime.subscribe(to: "users")

// Subscribe with filters
try await realtime.subscribeWithFilter(
  to: "orders",
  filters: ["status": "pending"]
)

// Unsubscribe
try await realtime.unsubscribe(from: "users")

// Disconnect
realtime.disconnect()
```

## Error Handling

```swift
do {
  let tokens = try await firebase.auth.login(
    email: "user@example.com",
    password: "password"
  )
} catch let error as OwnFirebaseError {
  switch error {
  case .networkError(let urlError):
    print("Network error: \(urlError.localizedDescription)")
  case .apiError(let apiError):
    print("API error \(apiError.status): \(apiError.message)")
  case .decodingError(let decodingError):
    print("Decoding error: \(decodingError)")
  case .retryExhausted(let attempts):
    print("Request failed after \(attempts) attempts")
  default:
    print("Unknown error: \(error)")
  }
} catch {
  print("Unexpected error: \(error)")
}
```

## Retry Configuration

By default, the SDK retries failed requests with exponential backoff:

- Max attempts: 3
- Initial delay: 100ms
- Max delay: 10 seconds
- Backoff multiplier: 2x
- Retryable status codes: 408, 429, 500, 502, 503, 504

Customize retry behavior:

```swift
let customRetry = RetryConfig(
  maxAttempts: 5,
  initialDelayMs: 200,
  maxDelayMs: 30000,
  backoffMultiplier: 1.5,
  retryableStatusCodes: [429, 500, 502, 503, 504]
)

let firebase = OwnFirebase(
  config: config,
  retryConfig: customRetry
)
```

## Architecture

### Module Structure

```
OwnFirebaseSDK/
├── OwnFirebase.swift          # Main SDK class bundling all services
├── Client.swift               # Base HTTP client with retry logic
├── Types.swift                # All data types and codables
├── Auth.swift                 # Authentication service
├── Data.swift                 # Data API service
├── Storage.swift              # Storage service
├── Analytics.swift            # Analytics service with batching
├── RemoteConfig.swift         # Remote config service with caching
├── Crashlytics.swift          # Crashlytics service with batching
├── Realtime.swift             # WebSocket-based realtime service
└── OwnFirebaseSDK.swift       # Module exports
```

### Service Inheritance

All services (Auth, Data, Storage, Analytics, RemoteConfig, Crashlytics) inherit from `OwnFirebaseClient`, which provides:

- HTTP request handling
- Authentication header management
- Automatic retries with exponential backoff
- Error response parsing
- JSON encoding/decoding

## Thread Safety

- Analytics batching is thread-safe using `DispatchQueue`
- Crashlytics reporting is thread-safe using `DispatchQueue`
- RemoteConfig caching is thread-safe using `DispatchQueue`
- All network operations use Swift's async/await model

## Testing

Run tests with:

```bash
swift test
```

## License

MIT
