# OwnFirebase Swift SDK - Integration Guide

Complete guide for integrating the OwnFirebase Swift SDK into your iOS, macOS, or other Apple platform applications.

## Prerequisites

- Xcode 14.0 or later
- Swift 5.7 or later
- iOS 14.0+ / macOS 11.0+ / tvOS 14.0+ / watchOS 7.0+
- An OwnFirebase backend instance

## Installation

### 1. Using Swift Package Manager (Recommended)

#### Option A: In Xcode

1. Open your Xcode project
2. Go to **File → Add Packages**
3. Enter the repository URL: `https://github.com/your-org/ownfirebase-swift-sdk.git`
4. Select version: **Up to Next Major** and specify `1.0.0`
5. Choose your target and click **Add Package**

#### Option B: In Package.swift

Add to your `Package.swift`:

```swift
dependencies: [
  .package(
    url: "https://github.com/your-org/ownfirebase-swift-sdk.git",
    from: "1.0.0"
  )
]
```

Then in your target dependencies:

```swift
.product(name: "OwnFirebaseSDK", package: "ownfirebase-swift-sdk")
```

### 2. Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/ownfirebase-swift-sdk.git
   ```

2. Add the package to your Xcode project:
   - Drag `sdk/swift-sdk` folder to your project
   - Select your target in the dialog that appears

## Configuration

### Step 1: Import the SDK

```swift
import OwnFirebaseSDK
```

### Step 2: Initialize the SDK

Initialize the SDK in your app's entry point or startup code:

```swift
import SwiftUI
import OwnFirebaseSDK

@main
struct MyApp: App {
  private let firebase: OwnFirebase

  init() {
    self.firebase = OwnFirebase.initialize(
      baseUrl: "https://api.your-domain.com",
      projectId: "your-project-id"
    )
  }

  var body: some Scene {
    WindowGroup {
      ContentView()
        .environmentObject(firebase)
    }
  }
}
```

### Step 3: Make Firebase Available Throughout Your App

Use `@EnvironmentObject` to pass the SDK instance:

```swift
struct ContentView: View {
  @EnvironmentObject private var firebase: OwnFirebase

  var body: some View {
    // Your UI code
  }
}
```

## Setting Up Authentication

### 1. Store Authentication State

```swift
class AuthenticationState: ObservableObject {
  @Published var isLoggedIn = false
  @Published var currentUser: User?
  @Published var error: Error?

  private let firebase: OwnFirebase

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  func login(email: String, password: String) {
    Task {
      do {
        let tokens = try await firebase.auth.login(
          email: email,
          password: password
        )
        firebase.setAccessToken(tokens.access)

        let user = try await firebase.auth.getMe()
        await MainActor.run {
          self.currentUser = user
          self.isLoggedIn = true
        }
      } catch {
        await MainActor.run {
          self.error = error
        }
      }
    }
  }

  func logout() {
    Task {
      // Implement logout
      await MainActor.run {
        self.isLoggedIn = false
        self.currentUser = nil
      }
    }
  }
}
```

### 2. Create Login View

```swift
struct LoginView: View {
  @StateObject private var state: AuthenticationState
  @State private var email = ""
  @State private var password = ""

  init(firebase: OwnFirebase) {
    _state = StateObject(wrappedValue: AuthenticationState(firebase: firebase))
  }

  var body: some View {
    VStack(spacing: 16) {
      TextField("Email", text: $email)
        .textContentType(.emailAddress)
        .keyboardType(.emailAddress)
        .padding()
        .border(Color.gray)

      SecureField("Password", text: $password)
        .textContentType(.password)
        .padding()
        .border(Color.gray)

      Button("Login") {
        state.login(email: email, password: password)
      }
      .disabled(email.isEmpty || password.isEmpty)

      if let error = state.error {
        Text("Error: \(error.localizedDescription)")
          .foregroundColor(.red)
      }
    }
    .padding()
  }
}
```

## Setting Up Data Management

### 1. Create a Data Service

```swift
class UserDataService: ObservableObject {
  @Published var users: [UserProfile] = []
  @Published var isLoading = false
  @Published var error: Error?

  private let firebase: OwnFirebase

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  func fetchUsers() {
    Task {
      await MainActor.run { self.isLoading = true }

      do {
        let response = try await firebase.data.listDocuments(collection: "users")

        let profiles = response.results.map { doc in
          UserProfile(
            id: doc.id,
            name: (doc.data["name"]?.value as? String) ?? "",
            email: (doc.data["email"]?.value as? String) ?? ""
          )
        }

        await MainActor.run {
          self.users = profiles
          self.isLoading = false
        }
      } catch {
        await MainActor.run {
          self.error = error
          self.isLoading = false
        }
      }
    }
  }

  func createUser(name: String, email: String) {
    Task {
      do {
        _ = try await firebase.data.createDocument(
          collection: "users",
          data: [
            "name": AnyCodable(name),
            "email": AnyCodable(email)
          ]
        )
        await MainActor.run {
          self.fetchUsers()
        }
      } catch {
        await MainActor.run {
          self.error = error
        }
      }
    }
  }
}
```

### 2. Create a Data View

```swift
struct UsersView: View {
  @StateObject private var service: UserDataService
  @EnvironmentObject var firebase: OwnFirebase

  init() {
    _service = StateObject(wrappedValue: UserDataService(firebase: OwnFirebase(config: OwnFirebaseConfig(baseUrl: "", projectId: ""))))
  }

  var body: some View {
    List {
      ForEach(service.users, id: \.id) { user in
        VStack(alignment: .leading) {
          Text(user.name)
            .font(.headline)
          Text(user.email)
            .font(.caption)
            .foregroundColor(.gray)
        }
      }
    }
    .onAppear { service.fetchUsers() }
  }
}
```

## Setting Up Analytics

### 1. Create Analytics Manager

```swift
class AnalyticsManager {
  private let firebase: OwnFirebase
  private var sessionId = UUID().uuidString

  init(firebase: OwnFirebase) {
    self.firebase = firebase
  }

  func trackScreenView(_ screenName: String) {
    firebase.analytics.logEventBatched(
      name: "screen_view",
      params: ["screen_name": AnyCodable(screenName)],
      sessionId: sessionId
    )
  }

  func trackUserAction(_ action: String, details: [String: String] = [:]) {
    var params: [String: AnyCodable] = ["action": AnyCodable(action)]
    details.forEach { key, value in
      params[key] = AnyCodable(value)
    }

    firebase.analytics.logEventBatched(
      name: "user_action",
      params: params,
      sessionId: sessionId
    )
  }

  func flushAnalytics() async throws {
    try await firebase.analytics.flushEventBatch()
  }
}
```

### 2. Track Events in Views

```swift
struct MyView: View {
  @EnvironmentObject var firebase: OwnFirebase
  private let analytics: AnalyticsManager

  init(firebase: OwnFirebase) {
    self.analytics = AnalyticsManager(firebase: firebase)
  }

  var body: some View {
    VStack {
      Button("Action") {
        analytics.trackUserAction("button_tap", details: ["button": "action"])
      }
    }
    .onAppear {
      analytics.trackScreenView("MyView")
    }
  }
}
```

## Setting Up Real-time Updates

### 1. Create Realtime Manager

```swift
class RealtimeManager: NSObject, RealtimeDelegate, ObservableObject {
  @Published var messages: [RealtimeMessage] = []
  @Published var isConnected = false
  @Published var lastError: Error?

  private let firebase: OwnFirebase
  private var realtime: RealtimeService?

  init(firebase: OwnFirebase) {
    self.firebase = firebase
    super.init()
  }

  func connect() async throws {
    realtime = firebase.createRealtimeService(delegate: self)
    try await realtime?.connect()
  }

  func disconnect() {
    realtime?.disconnect()
  }

  func subscribe(to collection: String) async throws {
    try await realtime?.subscribe(to: collection)
  }

  // MARK: - RealtimeDelegate

  func realtimeDidConnect() {
    DispatchQueue.main.async {
      self.isConnected = true
    }
  }

  func realtimeDidDisconnect(error: Error?) {
    DispatchQueue.main.async {
      self.isConnected = false
    }
  }

  func realtimeDidReceiveMessage(_ message: RealtimeMessage) {
    DispatchQueue.main.async {
      self.messages.append(message)
    }
  }

  func realtimeDidEncounterError(_ error: Error) {
    DispatchQueue.main.async {
      self.lastError = error
    }
  }
}
```

### 2. Use Realtime in Views

```swift
struct RealtimeView: View {
  @StateObject private var realtime: RealtimeManager
  @EnvironmentObject var firebase: OwnFirebase

  init() {
    _realtime = StateObject(wrappedValue: RealtimeManager(firebase: OwnFirebase(config: OwnFirebaseConfig(baseUrl: "", projectId: ""))))
  }

  var body: some View {
    List {
      ForEach(realtime.messages, id: \.timestamp) { message in
        VStack(alignment: .leading) {
          Text(message.type)
            .font(.headline)
          Text(message.doc_id)
            .font(.caption)
        }
      }
    }
    .onAppear {
      Task {
        try await realtime.connect()
        try await realtime.subscribe(to: "documents")
      }
    }
    .onDisappear {
      realtime.disconnect()
    }
  }
}
```

## Error Handling Best Practices

### 1. Handle Specific Errors

```swift
func handleAuthError(_ error: Error) {
  if let error = error as? OwnFirebaseError {
    switch error {
    case .apiError(let apiError):
      if apiError.status == 401 {
        // Handle unauthorized
      } else if apiError.status == 404 {
        // Handle not found
      }
    case .networkError(let urlError):
      // Handle network error
      print("Network error: \(urlError.localizedDescription)")
    case .decodingError(let decodingError):
      // Handle decoding error
      print("Decoding error: \(decodingError)")
    case .retryExhausted(let attempts):
      // Handle retry exhaustion
      print("Failed after \(attempts) attempts")
    default:
      break
    }
  }
}
```

### 2. Create Error Display View

```swift
struct ErrorBanner: View {
  let error: Error?

  var body: some View {
    if let error = error {
      VStack {
        HStack {
          Image(systemName: "exclamationmark.circle.fill")
          Text(error.localizedDescription)
        }
        .padding()
        .background(Color.red.opacity(0.1))
        .cornerRadius(8)
      }
    }
  }
}
```

## Testing Your Integration

### 1. Create Mock Firebase

```swift
class MockFirebase {
  func createMockConfig(baseUrl: String = "http://localhost:8000") -> OwnFirebaseConfig {
    return OwnFirebaseConfig(
      baseUrl: baseUrl,
      projectId: "test-project",
      accessToken: "test-token"
    )
  }

  func createMockFirebase() -> OwnFirebase {
    return OwnFirebase(config: createMockConfig())
  }
}
```

### 2. Test Views

```swift
struct UsersView_Previews: PreviewProvider {
  static var previews: some View {
    let mock = MockFirebase()
    let firebase = mock.createMockFirebase()

    UsersView()
      .environmentObject(firebase)
  }
}
```

## Performance Optimization

### 1. Batch Analytics Events

```swift
// Good: Batched
firebase.analytics.logEventBatched(name: "event")
Task { try await firebase.analytics.flushEventBatch() }

// Avoid: Individual sends
try await firebase.analytics.logEvent(name: "event")
```

### 2. Cache Remote Config

```swift
// Good: Uses built-in cache
let params = try await firebase.remoteConfig.listParameters(useCache: true)

// Avoid: Always fetch
let params = try await firebase.remoteConfig.listParameters(useCache: false)
```

### 3. Handle Large Datasets

```swift
// Implement pagination
var allDocuments: [DataDocument] = []
var nextPage: String? = nil

func loadMore() async throws {
  let response = try await firebase.data.listDocuments(collection: "users")
  allDocuments.append(contentsOf: response.results)
  nextPage = response.next
}
```

## Security Best Practices

### 1. Secure Token Storage

```swift
import Security

class TokenStorage {
  static let shared = TokenStorage()

  private let keychainService = "com.yourapp.ownfirebase"

  func saveToken(_ token: String) throws {
    let query: [String: Any] = [
      kSecClass as String: kSecClassGenericPassword,
      kSecAttrService as String: keychainService,
      kSecValueData as String: token.data(using: .utf8)!
    ]

    SecItemDelete(query as CFDictionary)
    try SecItemAdd(query as CFDictionary, nil).then { status in
      guard status == errSecSuccess else { throw NSError(domain: NSOSStatusErrorDomain, code: Int(status)) }
    }
  }

  func retrieveToken() -> String? {
    let query: [String: Any] = [
      kSecClass as String: kSecClassGenericPassword,
      kSecAttrService as String: keychainService,
      kSecReturnData as String: true
    ]

    var result: AnyObject?
    SecItemCopyMatching(query as CFDictionary, &result)

    if let data = result as? Data, let token = String(data: data, encoding: .utf8) {
      return token
    }
    return nil
  }
}
```

### 2. Validate User Input

```swift
func validateEmail(_ email: String) -> Bool {
  let emailRegex = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"
  let emailPredicate = NSPredicate(format: "SELF MATCHES %@", emailRegex)
  return emailPredicate.evaluate(with: email)
}

func validatePassword(_ password: String) -> Bool {
  return password.count >= 8 &&
    password.contains(where: { $0.isUppercase }) &&
    password.contains(where: { $0.isLowercase }) &&
    password.contains(where: { $0.isNumber })
}
```

## Troubleshooting

### Issue: "Module not found"

**Solution:** Ensure you've added the package correctly:
1. Check **Build Phases → Link Binary With Libraries** includes OwnFirebaseSDK
2. Verify **Build Settings → Framework Search Paths**

### Issue: "Cannot find 'firebase' in scope"

**Solution:** Make sure to import the SDK:
```swift
import OwnFirebaseSDK
```

### Issue: "Type mismatch" with AnyCodable

**Solution:** Always cast values properly:
```swift
let stringValue = doc.data["name"]?.value as? String
let numberValue = doc.data["age"]?.value as? Int
```

### Issue: Networking errors in debugger

**Solution:** Check your `baseUrl` and `projectId`:
- Ensure baseUrl has correct scheme (http/https)
- Remove trailing slashes
- Verify projectId matches backend

### Issue: Realtime connection not working

**Solution:** Ensure WebSocket URL is correct:
- Use `ws://` or `wss://` (not http/https)
- Check firewall settings
- Verify backend supports WebSockets

## Next Steps

1. Read the [API Reference](API_REFERENCE.md) for detailed API documentation
2. Review [Examples](EXAMPLES.md) for comprehensive usage patterns
3. Set up error tracking with Crashlytics
4. Configure Remote Config for feature flags
5. Implement analytics tracking for your features

## Support

For issues or questions:
1. Check the [README](README.md)
2. Review [Examples](EXAMPLES.md)
3. Check existing issues on GitHub
4. Create a new issue with detailed information
