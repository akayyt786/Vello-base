# OwnFirebase Swift SDK - Examples

Comprehensive examples demonstrating all SDK features.

## Example 1: Complete Authentication Flow

```swift
import OwnFirebaseSDK

actor AuthenticationManager {
  private let firebase: OwnFirebase
  private var currentUser: User?
  private var refreshToken: String?

  init(baseUrl: String, projectId: String) {
    self.firebase = OwnFirebase.initialize(
      baseUrl: baseUrl,
      projectId: projectId
    )
  }

  // MARK: - Sign Up

  func signUp(
    email: String,
    password: String,
    username: String
  ) async throws -> User {
    do {
      let tokens = try await firebase.auth.register(
        email: email,
        password: password,
        username: username
      )

      firebase.setAccessToken(tokens.access)
      self.refreshToken = tokens.refresh

      let user = try await firebase.auth.getMe()
      self.currentUser = user

      return user
    } catch let error as OwnFirebaseError {
      print("Sign up failed: \(error.errorDescription ?? "Unknown")")
      throw error
    }
  }

  // MARK: - Login

  func login(email: String, password: String) async throws -> User {
    do {
      let tokens = try await firebase.auth.login(email: email, password: password)

      firebase.setAccessToken(tokens.access)
      self.refreshToken = tokens.refresh

      let user = try await firebase.auth.getMe()
      self.currentUser = user

      return user
    } catch let error as OwnFirebaseError {
      print("Login failed: \(error.errorDescription ?? "Unknown")")
      throw error
    }
  }

  // MARK: - Logout

  func logout() async throws {
    guard let refreshToken = refreshToken else { return }

    try await firebase.auth.logout(refresh: refreshToken)
    firebase.setAccessToken("")
    self.currentUser = nil
    self.refreshToken = nil
  }

  // MARK: - Social Auth

  func signInWithGoogle(idToken: String) async throws -> User {
    let tokens = try await firebase.auth.googleSignIn(idToken: idToken)
    firebase.setAccessToken(tokens.access)
    self.refreshToken = tokens.refresh

    let user = try await firebase.auth.getMe()
    self.currentUser = user
    return user
  }

  // MARK: - Anonymous Auth

  func signInAnonymously() async throws -> User {
    let tokens = try await firebase.auth.anonymousSignIn()
    firebase.setAccessToken(tokens.access)
    self.refreshToken = tokens.refresh

    let user = try await firebase.auth.getMe()
    self.currentUser = user
    return user
  }

  // MARK: - Upgrade Anonymous Account

  func upgradeAnonymousAccount(
    email: String,
    password: String
  ) async throws -> User {
    let tokens = try await firebase.auth.upgradeAnonymous(
      email: email,
      password: password,
      password2: password
    )

    firebase.setAccessToken(tokens.access)
    self.refreshToken = tokens.refresh

    let user = try await firebase.auth.getMe()
    self.currentUser = user
    return user
  }

  // MARK: - MFA

  func enrollTOTP() async throws -> (uri: String, secret: String) {
    let result = try await firebase.auth.enrollTOTP()
    return (uri: result.totp_uri, secret: result.secret)
  }

  func confirmTOTPEnrollment(code: String) async throws {
    try await firebase.auth.confirmTOTP(code: code)
  }

  func getCurrentUser() -> User? {
    return currentUser
  }
}
```

## Example 2: User Data Management

```swift
import OwnFirebaseSDK

struct UserProfile: Codable {
  let id: String
  let email: String
  let displayName: String
  let bio: String
  let avatar: String?
  let createdAt: Date
}

class UserDataService {
  private let firebase: OwnFirebase
  private let collectionName = "users"

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  // MARK: - Create Profile

  func createProfile(
    userId: String,
    displayName: String,
    bio: String
  ) async throws {
    let data: [String: AnyCodable] = [
      "id": AnyCodable(userId),
      "display_name": AnyCodable(displayName),
      "bio": AnyCodable(bio),
      "avatar": AnyCodable(NSNull()),
      "created_at": AnyCodable(ISO8601DateFormatter().string(from: Date()))
    ]

    _ = try await firebase.data.createDocument(
      collection: collectionName,
      data: data
    )
  }

  // MARK: - Get Profile

  func getProfile(userId: String) async throws -> UserProfile {
    let doc = try await firebase.data.getDocument(
      collection: collectionName,
      docId: userId
    )

    // Convert AnyCodable values to proper types
    let profile = UserProfile(
      id: doc.id,
      email: (doc.data["email"]?.value as? String) ?? "",
      displayName: (doc.data["display_name"]?.value as? String) ?? "",
      bio: (doc.data["bio"]?.value as? String) ?? "",
      avatar: doc.data["avatar"]?.value as? String,
      createdAt: Date()
    )

    return profile
  }

  // MARK: - Update Profile

  func updateProfile(
    userId: String,
    displayName: String?,
    bio: String?
  ) async throws {
    var updateData: [String: AnyCodable] = [:]

    if let displayName = displayName {
      updateData["display_name"] = AnyCodable(displayName)
    }

    if let bio = bio {
      updateData["bio"] = AnyCodable(bio)
    }

    updateData["updated_at"] = AnyCodable(ISO8601DateFormatter().string(from: Date()))

    _ = try await firebase.data.updateDocument(
      collection: collectionName,
      docId: userId,
      data: updateData
    )
  }

  // MARK: - List All Users

  func listUsers() async throws -> [UserProfile] {
    let response = try await firebase.data.listDocuments(collection: collectionName)

    return response.results.compactMap { doc in
      UserProfile(
        id: doc.id,
        email: (doc.data["email"]?.value as? String) ?? "",
        displayName: (doc.data["display_name"]?.value as? String) ?? "",
        bio: (doc.data["bio"]?.value as? String) ?? "",
        avatar: doc.data["avatar"]?.value as? String,
        createdAt: Date()
      )
    }
  }

  // MARK: - Delete Profile

  func deleteProfile(userId: String) async throws {
    try await firebase.data.deleteDocument(
      collection: collectionName,
      docId: userId
    )
  }

  // MARK: - Batch Operations

  func createMultipleProfiles(_ profiles: [(userId: String, name: String)]) async throws {
    let operations = profiles.map { profile in
      WriteBatchOperation(
        op: "set",
        collection: collectionName,
        doc_id: profile.userId,
        data: [
          "display_name": AnyCodable(profile.name),
          "created_at": AnyCodable(ISO8601DateFormatter().string(from: Date()))
        ]
      )
    }

    let result = try await firebase.data.writeBatch(operations: operations)
    print("Created \(result.written) profiles")
  }
}
```

## Example 3: File Storage with Uploads

```swift
import OwnFirebaseSDK

class PhotoStorageService {
  private let firebase: OwnFirebase

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  // MARK: - Upload Photo

  func uploadProfilePhoto(
    userId: String,
    imageData: Data,
    contentType: String = "image/jpeg"
  ) async throws -> String {
    let filename = "profile_\(userId)_\(UUID().uuidString).jpg"

    let storageObject = try await firebase.storage.upload(
      data: imageData,
      filename: filename,
      contentType: contentType,
      path: "avatars/"
    )

    return storageObject.url
  }

  // MARK: - List Photos

  func listUserPhotos(userId: String) async throws -> [StorageObject] {
    let response = try await firebase.storage.listFiles(prefix: "avatars/\(userId)/")
    return response.results
  }

  // MARK: - Download Photo

  func downloadPhoto(url: String) async throws -> Data {
    return try await firebase.storage.downloadFile(url: url)
  }

  // MARK: - Delete Photo

  func deletePhoto(path: String) async throws {
    try await firebase.storage.deleteFile(path: path)
  }

  // MARK: - Get Direct Upload URL

  func getDirectUploadUrl(
    userId: String,
    filename: String
  ) async throws -> (uploadUrl: String, objectKey: String) {
    let response = try await firebase.storage.getUploadUrl(
      filename: filename,
      contentType: "image/jpeg",
      path: "avatars/\(userId)/"
    )

    return (uploadUrl: response.upload_url, objectKey: response.object_key)
  }
}
```

## Example 4: Analytics and Event Tracking

```swift
import OwnFirebaseSDK

class AnalyticsManager {
  private let firebase: OwnFirebase

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  // MARK: - Track User Events

  func trackUserSignup(
    userId: String,
    method: String,
    referrer: String?
  ) {
    firebase.analytics.logEventBatched(
      name: "user_signup",
      params: [
        "method": AnyCodable(method),
        "referrer": AnyCodable(referrer ?? "direct")
      ],
      userId: userId
    )
  }

  func trackPageView(
    userId: String,
    pageName: String,
    sessionId: String
  ) {
    firebase.analytics.logEventBatched(
      name: "page_view",
      params: ["page": AnyCodable(pageName)],
      userId: userId,
      sessionId: sessionId
    )
  }

  func trackPurchase(
    userId: String,
    amount: Double,
    currency: String,
    items: [String]
  ) {
    firebase.analytics.logEventBatched(
      name: "purchase",
      params: [
        "amount": AnyCodable(amount),
        "currency": AnyCodable(currency),
        "item_count": AnyCodable(items.count),
        "items": AnyCodable(items)
      ],
      userId: userId
    )
  }

  // MARK: - Set User Properties

  func setUserProperties(
    userId: String,
    planType: String,
    accountAge: Int
  ) async throws {
    try await firebase.analytics.setUserProperty(
      name: "subscription_plan",
      value: planType
    )

    try await firebase.analytics.setUserProperty(
      name: "account_age_days",
      value: String(accountAge)
    )
  }

  // MARK: - Mark Conversion

  func markConversion(eventName: String) async throws {
    _ = try await firebase.analytics.markConversionEvent(name: eventName)
  }

  // MARK: - Flush Batch

  func flushAnalytics() async throws {
    try await firebase.analytics.flushEventBatch()
  }

  // MARK: - Query Analytics

  func getUserCount(startDate: String, endDate: String) async throws -> [AnalyticsQueryRow] {
    let result = try await firebase.analytics.query(
      params: AnalyticsQueryParams(
        metric: "user_count",
        start_date: startDate,
        end_date: endDate
      )
    )

    return result.rows
  }
}
```

## Example 5: Crash Reporting

```swift
import OwnFirebaseSDK

class ErrorReporter {
  private let firebase: OwnFirebase
  private let appVersion: String

  init(firebase: OwnFirebase, appVersion: String) {
    self.firebase = firebase
    self.appVersion = appVersion
  }

  // MARK: - Report Exception

  func reportException(
    _ error: Error,
    stackTrace: String? = nil
  ) {
    let errorDescription = "\(type(of: error)): \(error.localizedDescription)"
    let trace = stackTrace ?? Thread.callStackSymbols.joined(separator: "\n")

    firebase.crashlytics.reportCrashBatched(
      exceptionType: String(describing: type(of: error)),
      message: errorDescription,
      stackTrace: trace,
      appVersion: appVersion,
      platform: "iOS",
      deviceInfo: [
        "device_model": AnyCodable(UIDevice.current.model),
        "os_version": AnyCodable(UIDevice.current.systemVersion)
      ]
    )
  }

  // MARK: - Record Performance

  func recordNetworkRequest(
    url: String,
    method: String,
    statusCode: Int,
    durationMs: Int
  ) {
    Task {
      try? await firebase.crashlytics.recordNetworkRequest(
        url: url,
        method: method,
        statusCode: statusCode,
        durationMs: durationMs
      )
    }
  }

  func recordDatabaseOperation(
    name: String,
    durationMs: Int,
    rowsAffected: Int
  ) {
    Task {
      try? await firebase.crashlytics.recordTrace(
        name: name,
        durationMs: durationMs,
        startedAt: ISO8601DateFormatter().string(from: Date()),
        attributes: ["operation": "database"],
        metrics: ["rows_affected": Double(rowsAffected)]
      )
    }
  }

  // MARK: - Flush Reports

  func flushCrashReports() async throws {
    try await firebase.crashlytics.flushReports()
  }
}
```

## Example 6: Remote Configuration

```swift
import OwnFirebaseSDK

class FeatureFlagManager {
  private let firebase: OwnFirebase

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  // MARK: - Feature Flags

  func isFeatureEnabled(_ featureName: String) async throws -> Bool {
    let parameter = try await firebase.remoteConfig.getParameter(
      id: "feature_\(featureName)"
    )

    return parameter.default_value.lowercased() == "true"
  }

  func getConfigValue(_ key: String) async throws -> String {
    let parameter = try await firebase.remoteConfig.getParameter(id: key)
    return parameter.default_value
  }

  // MARK: - Manage Configs

  func createFeatureFlag(
    name: String,
    enabled: Bool,
    description: String
  ) async throws -> RemoteConfigParameter {
    return try await firebase.remoteConfig.createParameter(
      RemoteConfigParameterInput(
        key: "feature_\(name)",
        defaultValue: enabled ? "true" : "false",
        description: description,
        valueType: "boolean"
      )
    )
  }

  func updateFeatureFlag(
    id: String,
    enabled: Bool
  ) async throws -> RemoteConfigParameter {
    let current = try await firebase.remoteConfig.getParameter(id: id)

    return try await firebase.remoteConfig.updateParameter(
      id: id,
      updates: RemoteConfigParameterInput(
        key: current.key,
        defaultValue: enabled ? "true" : "false",
        description: current.description,
        valueType: current.value_type
      )
    )
  }

  // MARK: - Cache Management

  func refreshConfig() async throws {
    firebase.remoteConfig.clearCache()
    _ = try await firebase.remoteConfig.listParameters(useCache: false)
  }
}
```

## Example 7: Real-time Updates

```swift
import OwnFirebaseSDK

class UserPresenceManager: RealtimeDelegate {
  private let firebase: OwnFirebase
  private var realtime: RealtimeService?
  private var presenceData: [String: RealtimeMessage] = [:]

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  // MARK: - Connect to Real-time

  func startListening() async throws {
    realtime = firebase.createRealtimeService(delegate: self)
    try await realtime?.connect()
    try await realtime?.subscribe(to: "user_presence")
  }

  func stopListening() {
    realtime?.disconnect()
  }

  // MARK: - RealtimeDelegate

  func realtimeDidConnect() {
    print("Real-time connected")
  }

  func realtimeDidDisconnect(error: Error?) {
    print("Real-time disconnected: \(error?.localizedDescription ?? "normal")")
  }

  func realtimeDidReceiveMessage(_ message: RealtimeMessage) {
    print("Received update: \(message.type) for \(message.doc_id)")

    // Store presence data
    presenceData[message.doc_id] = message

    // Process different message types
    switch message.type {
    case "document_created":
      onUserOnline(message)
    case "document_updated":
      onUserStatusChanged(message)
    case "document_deleted":
      onUserOffline(message)
    default:
      break
    }
  }

  func realtimeDidEncounterError(_ error: Error) {
    print("Real-time error: \(error)")
  }

  // MARK: - Event Handlers

  private func onUserOnline(_ message: RealtimeMessage) {
    if let userName = message.data?["name"]?.value as? String {
      print("User online: \(userName)")
    }
  }

  private func onUserStatusChanged(_ message: RealtimeMessage) {
    if let status = message.data?["status"]?.value as? String {
      print("User status: \(status)")
    }
  }

  private func onUserOffline(_ message: RealtimeMessage) {
    print("User offline: \(message.doc_id)")
  }

  // MARK: - Utilities

  func getOnlineUsers() -> [String] {
    return Array(presenceData.keys)
  }
}
```

## Example 8: Complete App Integration

```swift
import OwnFirebaseSDK
import SwiftUI

@main
struct MyApp: App {
  @StateObject private var authManager: AuthenticationManager
  @StateObject private var dataService: UserDataService
  @StateObject private var analyticsManager: AnalyticsManager
  @StateObject private var errorReporter: ErrorReporter

  init() {
    let baseUrl = "https://api.example.com"
    let projectId = "my-project"

    let firebase = OwnFirebase.initialize(
      baseUrl: baseUrl,
      projectId: projectId
    )

    _authManager = StateObject(
      wrappedValue: AuthenticationManager(
        baseUrl: baseUrl,
        projectId: projectId
      )
    )
    _dataService = StateObject(wrappedValue: UserDataService(firebase: firebase))
    _analyticsManager = StateObject(wrappedValue: AnalyticsManager(firebase: firebase))
    _errorReporter = StateObject(
      wrappedValue: ErrorReporter(firebase: firebase, appVersion: "1.0.0")
    )
  }

  var body: some Scene {
    WindowGroup {
      if let user = authManager.currentUser {
        MainView()
          .environmentObject(authManager)
          .environmentObject(dataService)
          .environmentObject(analyticsManager)
      } else {
        LoginView()
          .environmentObject(authManager)
      }
    }
  }
}
```

## Testing Tips

```swift
import XCTest
@testable import OwnFirebaseSDK

class MockRealtimeDelegate: RealtimeDelegate {
  var didConnect = false
  var didDisconnect = false
  var receivedMessages: [RealtimeMessage] = []
  var encounteredErrors: [Error] = []

  func realtimeDidConnect() {
    didConnect = true
  }

  func realtimeDidDisconnect(error: Error?) {
    didDisconnect = true
  }

  func realtimeDidReceiveMessage(_ message: RealtimeMessage) {
    receivedMessages.append(message)
  }

  func realtimeDidEncounterError(_ error: Error) {
    encounteredErrors.append(error)
  }
}

// Usage in tests
func testRealtimeConnection() async {
  let delegate = MockRealtimeDelegate()
  let realtime = firebase.createRealtimeService(delegate: delegate)

  try await realtime.connect()

  XCTAssertTrue(delegate.didConnect)
}
```
