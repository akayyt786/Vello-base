# OwnFirebase Kotlin SDK

A comprehensive Kotlin SDK for interacting with the OwnFirebase backend API. Provides services for authentication, real-time data synchronization, file storage, analytics, crash reporting, and remote configuration.

## Features

- **Authentication** - Email/password, social login (Google, GitHub), phone OTP, MFA (TOTP/SMS), passwordless auth
- **Real-time Data** - CRUD operations, collections, subcollections, queries, batch transactions
- **File Storage** - Presigned upload URLs, download, list, delete with direct S3/MinIO integration
- **Analytics** - Event tracking, user properties, batch operations, query interface
- **Crash Reporting** - Exception reporting, performance traces, network monitoring
- **Remote Config** - Feature flags, dynamic configuration, conditional rules, caching
- **Real-time Listeners** - WebSocket-based live updates on collections and documents
- **Error Handling** - Automatic retries, exponential backoff, detailed error information
- **JWT Token Management** - Automatic token setting and refresh handling

## Installation

Add to your `build.gradle`:

```gradle
dependencies {
    implementation 'com.ownfirebase:kotlin-sdk:1.0.0'
}
```

Or build from source:

```bash
./gradlew build
./gradlew publishToMavenLocal
```

## Quick Start

```kotlin
import com.ownfirebase.sdk.OwnFirebase

// Initialize SDK
val sdk = OwnFirebase(
    baseUrl = "https://api.example.com",
    projectId = "my-project"
)

// Login
val tokens = sdk.auth().login("user@example.com", "password")
sdk.setAccessToken(tokens.access)

// Read data
val user = sdk.auth().getMe()
val docs = sdk.data().listDocuments("users")

// Track events
sdk.analytics().logEvent("app_opened", mapOf("version" to "1.0.0"))

// Report crashes
try {
    someDangerousOperation()
} catch (e: Exception) {
    sdk.crashlytics().reportException(e)
}

// Get remote config
val maxRetries = sdk.remoteConfig().getNumber("max_retries", 3.0).toInt()

// Listen for real-time updates
sdk.realtime().subscribe("posts")

// Clean up on shutdown
sdk.shutdown()
```

## Services

### Authentication (`sdk.auth()`)

User registration, login, and account management:

```kotlin
// Email/password auth
val tokens = sdk.auth().login("user@example.com", "password")
val registered = sdk.auth().register("new@example.com", "password123", "username")

// Social auth
val googleTokens = sdk.auth().googleSignIn(idToken)
val githubTokens = sdk.auth().githubSignIn(accessToken)

// Passwordless
sdk.auth().sendMagicLink("user@example.com")
val tokens = sdk.auth().verifyMagicLink(magicLinkToken)

// MFA
val totpSetup = sdk.auth().enrollTOTP()
sdk.auth().confirmTOTP(code)
val tokens = sdk.auth().verifyTOTP(code) // at login time

// Anonymous
val anonTokens = sdk.auth().anonymousSignIn()
sdk.auth().upgradeAnonymous("email@example.com", "password", "password")
```

### Data (`sdk.data()`)

CRUD operations on collections and documents:

```kotlin
// Collections
val collections = sdk.data().listCollections()
sdk.data().createCollection("posts")

// Documents
val doc = sdk.data().createDocument("posts", mapOf(
    "title" to "Hello World",
    "content" to "This is my first post"
))

val fetched = sdk.data().getDocument("posts", doc.id)

sdk.data().updateDocument("posts", doc.id, mapOf(
    "content" to "Updated content"
))

sdk.data().replaceDocument("posts", doc.id, mapOf(
    "title" to "New Title",
    "content" to "New Content"
))

sdk.data().deleteDocument("posts", doc.id)

// Batch operations
val batch = listOf(
    WriteBatchOperation("set", "posts", "post1", mapOf("title" to "Post 1")),
    WriteBatchOperation("update", "posts", "post2", mapOf("title" to "Post 2")),
    WriteBatchOperation("delete", "posts", "post3")
)
val result = sdk.data().writeBatch(batch)

// Subcollections (using paths)
val userPosts = sdk.data().listDocuments("users/user123/posts")

// Queries
val filtered = sdk.data().listDocuments(
    "posts",
    mapOf("category" to "tech", "status" to "published")
)
```

### Storage (`sdk.storage()`)

File upload and download:

```kotlin
// Upload from bytes
val file = "Hello World".toByteArray()
val uploaded = sdk.storage().upload(
    file,
    filename = "greeting.txt",
    contentType = "text/plain",
    path = "documents/"
)

// Upload from file
val uploaded = sdk.storage().uploadFile(
    File("/path/to/file.pdf"),
    filename = "document.pdf",
    contentType = "application/pdf",
    path = "documents/"
)

// List files
val files = sdk.storage().listFiles(prefix = "documents/")

// Get file info
val fileInfo = sdk.storage().getFile("documents/document.pdf")

// Download
val bytes = sdk.storage().download("documents/document.pdf")

// Delete
sdk.storage().deleteFile("documents/document.pdf")

// Get presigned URL for manual upload
val uploadUrl = sdk.storage().getUploadUrl(
    filename = "large-file.mp4",
    contentType = "video/mp4",
    path = "videos/"
)
// Client uploads to uploadUrl.upload_url
// Then confirm: sdk.storage().confirmUpload(uploadUrl.object_key)
```

### Analytics (`sdk.analytics()`)

Event tracking and analytics:

```kotlin
// Log individual event
sdk.analytics().logEvent(
    "purchase",
    mapOf(
        "amount" to 99.99,
        "currency" to "USD",
        "items" to 3
    ),
    userId = user.id,
    sessionId = sessionId
)

// Queue event for batch (better performance for high volume)
sdk.analytics().queueEvent("page_view", mapOf("page" to "home"))

// Manually flush batch
sdk.analytics().flush()

// Set user property
sdk.analytics().setUserProperty("plan", "premium")

// Query analytics
val result = sdk.analytics().query(
    metric = "event_count",
    dimension = "event_name",
    startDate = "2024-01-01",
    endDate = "2024-01-31"
)

// Conversion events
sdk.analytics().markConversionEvent("purchase")
```

### Crashlytics (`sdk.crashlytics()`)

Crash and error reporting:

```kotlin
// Report exception
try {
    riskyOperation()
} catch (e: Exception) {
    sdk.crashlytics().reportException(e)
}

// Manual crash report
sdk.crashlytics().reportCrash(
    exceptionType = "NullPointerException",
    message = "User object was null",
    stackTrace = getStackTrace()
)

// Performance tracing
sdk.crashlytics().recordTrace(
    name = "api_call",
    durationMs = 250,
    attributes = mapOf("endpoint" to "/api/users")
)

// Convenience method
val result = sdk.crashlytics().trace("database_query") {
    queryDatabase()
}

// Network monitoring
sdk.crashlytics().recordNetworkRequest(
    url = "https://api.example.com/data",
    method = "GET",
    statusCode = 200,
    durationMs = 150,
    responseSize = 2048
)

// Get crash summary
val summary = sdk.crashlytics().getCrashSummary()

// List crash groups
val groups = sdk.crashlytics().listCrashGroups(
    mapOf("status" to "open")
)
```

### Remote Config (`sdk.remoteConfig()`)

Feature flags and remote configuration:

```kotlin
// Get parameter
val param = sdk.remoteConfig().getParameter("my_feature_enabled")

// Type-safe getters
val featureEnabled = sdk.remoteConfig().getBoolean("feature_x_enabled", false)
val maxRetries = sdk.remoteConfig().getNumber("max_retries", 3.0).toInt()
val apiKey = sdk.remoteConfig().getString("api_key", "default")
val config = sdk.remoteConfig().getJson("app_config", "{}")

// Manage parameters (admin)
sdk.remoteConfig().createParameter(
    key = "new_feature",
    defaultValue = "false",
    description = "Enable new feature",
    valueType = "boolean"
)

sdk.remoteConfig().updateParameter(
    id = "param_id",
    defaultValue = "true"
)

// Conditions
sdk.remoteConfig().createCondition(
    configId = "param_id",
    name = "Premium users only",
    expression = "user.plan == 'premium'",
    value = "true"
)

// Cache management
sdk.remoteConfig().refreshCache()
sdk.remoteConfig().clearCache()
```

### Real-time Listeners (`sdk.realtime()`)

Live updates on data changes:

```kotlin
// Simple listener
sdk.realtime().subscribe("posts")

// Document listener
val docListener = object : RealtimeListener.RealtimeEventListener {
    override fun onEvent(event: RealtimeListener.RealtimeEvent) {
        when (event.type) {
            "create", "update" -> println("Document changed: ${event.data}")
            "delete" -> println("Document deleted")
        }
    }
    
    override fun onError(error: Throwable) {
        println("Error: ${error.message}")
    }
    
    override fun onConnected() {
        println("Connected")
    }
    
    override fun onDisconnected() {
        println("Disconnected")
    }
}

sdk.realtime().addListener(docListener)

// Convenience listeners
val collectionListener = RealtimeCollectionListener(
    onAdd = { docId, data -> println("Added: $docId") },
    onModify = { docId, data -> println("Modified: $docId") },
    onRemove = { docId -> println("Removed: $docId") },
    onError = { error -> println("Error: ${error.message}") }
)

sdk.realtime().addListener(collectionListener)

// Disconnect when done
sdk.realtime().disconnect()
```

## Error Handling

All errors throw `APIError` with status code, message, and detail:

```kotlin
try {
    sdk.data().getDocument("posts", "invalid-id")
} catch (e: APIError) {
    println("Error ${e.status}: ${e.message}")
    println("Detail: ${e.detail}")
} catch (e: NetworkException) {
    println("Network error: ${e.message}")
}
```

## Token Refresh

Handle token expiration:

```kotlin
try {
    sdk.data().listDocuments("posts")
} catch (e: APIError) {
    if (e.status == 401) {
        // Token expired, refresh it
        val newTokens = sdk.auth().refreshToken(refreshToken)
        sdk.setAccessToken(newTokens["access"] as String)
        
        // Retry operation
        sdk.data().listDocuments("posts")
    }
}
```

## Configuration

### Custom HTTP Client

For advanced use cases, you can extend the client classes:

```kotlin
class CustomAuthService(config: OwnFirebaseConfig) : AuthService(config) {
    // Override behavior as needed
}
```

### Batch Size for Analytics

Default batch size is 100 events. Modify by creating a custom analytics service or directly configure at initialization.

## Thread Safety

All services are thread-safe:
- Services use thread-safe data structures
- HTTP requests can be made from multiple threads
- WebSocket listeners use `CopyOnWriteArrayList` for concurrent access

## Best Practices

1. **Initialize once**: Create a single `OwnFirebase` instance and reuse it
2. **Use singletons**: Use `OwnFirebaseProvider` for app-wide access
3. **Handle tokens**: Set tokens after login, refresh on 401 errors
4. **Batch analytics**: Use `queueEvent()` for high-volume tracking
5. **Cache configs**: Remote config automatically caches results
6. **Clean up**: Call `shutdown()` on app termination

## Example: Complete App Setup

```kotlin
class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        
        // Initialize SDK
        OwnFirebaseProvider.initialize(
            baseUrl = "https://api.example.com",
            projectId = "my-project"
        )
        
        // Try to restore session from preferences
        val accessToken = preferences.getString("access_token")
        if (accessToken != null) {
            OwnFirebaseProvider.getInstance().setAccessToken(accessToken)
        }
    }
    
    override fun onTerminate() {
        OwnFirebaseProvider.shutdown()
        super.onTerminate()
    }
}

// In Activity/Fragment
val sdk = OwnFirebaseProvider.getInstance()

// Login
val tokens = sdk.auth().login(email, password)
sdk.setAccessToken(tokens.access)
preferences.putString("access_token", tokens.access)
preferences.putString("refresh_token", tokens.refresh)

// Use services
sdk.analytics().logEvent("screen_view", mapOf("screen" to "home"))
val user = sdk.auth().getMe()
val data = sdk.data().listDocuments("users")
```

## License

MIT
