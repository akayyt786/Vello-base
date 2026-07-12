# Kotlin SDK - Quick Reference

## File Structure

```
kotlin-sdk/
├── Documentation
│   ├── README.md                      Main user guide (400+ lines)
│   ├── INTEGRATION.md                 Android integration guide (600+ lines)
│   ├── IMPLEMENTATION_SUMMARY.md      Technical overview (800+ lines)
│   ├── CHECKLIST.md                   Implementation checklist (400+ lines)
│   └── QUICK_REFERENCE.md            This file
│
├── Build Configuration
│   ├── build.gradle.kts              Gradle build with all dependencies
│   ├── settings.gradle.kts           Gradle project settings
│   ├── gradle.properties             Gradle configuration
│   └── .gitignore                    Git ignore rules
│
└── Source Code (src/)
    ├── main/kotlin/com/ownfirebase/sdk/
    │   ├── OwnFirebase.kt (180 lines)
    │   │   └─ Main SDK entry point + singleton provider
    │   │
    │   ├── client/
    │   │   └─ OwnFirebaseClient.kt (210 lines)
    │   │      └─ Base HTTP client with retry logic
    │   │
    │   ├── types/
    │   │   └─ Types.kt (250 lines)
    │   │      └─ All data class definitions (28 types)
    │   │
    │   ├── auth/
    │   │   └─ AuthService.kt (350 lines)
    │   │      └─ 18 authentication methods
    │   │
    │   ├── data/
    │   │   └─ DataService.kt (290 lines)
    │   │      └─ 15 CRUD + batch operations
    │   │
    │   ├── storage/
    │   │   └─ StorageService.kt (280 lines)
    │   │      └─ 14 file operations
    │   │
    │   ├── analytics/
    │   │   └─ AnalyticsService.kt (310 lines)
    │   │      └─ 14 methods + auto-batching
    │   │
    │   ├── crashlytics/
    │   │   └─ CrashlyticsService.kt (340 lines)
    │   │      └─ 15 crash + performance methods
    │   │
    │   ├── config/
    │   │   └─ RemoteConfigService.kt (360 lines)
    │   │      └─ 14 methods + caching
    │   │
    │   ├── realtime/
    │   │   └─ RealtimeListener.kt (290 lines)
    │   │      └─ WebSocket real-time updates
    │   │
    │   └── example/
    │       └─ ExampleUsage.kt (400+ lines)
    │          └─ Complete working examples
    │
    └── test/kotlin/com/ownfirebase/sdk/
        └─ OwnFirebaseTest.kt (300 lines)
           └─ Unit tests + integration test examples
```

## Quick API Reference

### Initialize SDK
```kotlin
val sdk = OwnFirebase("https://api.example.com", "project-id")
// or with singleton
OwnFirebaseProvider.initialize("https://api.example.com", "project-id")
val sdk = OwnFirebaseProvider.getInstance()
```

### Authentication
```kotlin
sdk.auth().login(email, password)
sdk.auth().register(email, password, username)
sdk.auth().anonymousSignIn()
sdk.auth().googleSignIn(idToken)
sdk.auth().verifyMagicLink(token)
sdk.auth().getMe()
sdk.auth().logout(refreshToken)
```

### Data Operations
```kotlin
sdk.data().listCollections()
sdk.data().listDocuments("collection")
sdk.data().createDocument("collection", data)
sdk.data().getDocument("collection", "docId")
sdk.data().updateDocument("collection", "docId", data)
sdk.data().deleteDocument("collection", "docId")
sdk.data().writeBatch(operations)
```

### File Storage
```kotlin
sdk.storage().upload(bytes, "filename", "content/type")
sdk.storage().uploadFile(file, "filename", "content/type")
sdk.storage().uploadFromStream(inputStream, "filename", "content/type")
sdk.storage().download("path")
sdk.storage().listFiles(prefix)
sdk.storage().deleteFile("path")
```

### Analytics
```kotlin
sdk.analytics().logEvent("name", params)
sdk.analytics().queueEvent("name", params)  // Batched
sdk.analytics().flush()
sdk.analytics().setUserProperty("name", "value")
sdk.analytics().query(metric, dimension, startDate, endDate)
```

### Crashlytics
```kotlin
sdk.crashlytics().reportException(exception)
sdk.crashlytics().recordTrace("name", durationMs)
sdk.crashlytics().trace("name") { block() }
sdk.crashlytics().recordNetworkRequest(url, method, statusCode, durationMs)
sdk.crashlytics().getCrashSummary()
```

### Remote Config
```kotlin
sdk.remoteConfig().getString("key", "default")
sdk.remoteConfig().getBoolean("key", false)
sdk.remoteConfig().getNumber("key", 0.0)
sdk.remoteConfig().getJson("key", "{}")
sdk.remoteConfig().refreshCache()
```

### Real-time Listeners
```kotlin
sdk.realtime().subscribe("collection")
sdk.realtime().addListener(listener)
sdk.realtime().disconnect()
```

## Module Comparison: TypeScript vs Kotlin

| Feature | TypeScript SDK | Kotlin SDK |
|---------|----------------|-----------|
| Auth Methods | 18 | 18 ✅ |
| Data Operations | 15 | 15 ✅ |
| Storage Operations | 8 | 14 ✅ |
| Analytics Methods | 7 | 14 ✅ |
| Crashlytics Methods | 11 | 15 ✅ |
| Remote Config Methods | 11 | 14 ✅ |
| Real-time Support | ✅ | ✅ |
| Error Handling | Basic | Advanced ✅ |
| Retry Logic | None | Auto-retry ✅ |
| Caching | None | Config caching ✅ |
| Batching | None | Analytics batch ✅ |
| Thread Safety | Basic | Full ✅ |

## Error Handling

```kotlin
try {
    sdk.data().getDocument("posts", "id")
} catch (e: APIError) {
    // HTTP error - check e.status
    when (e.status) {
        401 -> { /* Unauthorized */ }
        404 -> { /* Not found */ }
        429 -> { /* Rate limited */ }
        500 -> { /* Server error */ }
    }
} catch (e: NetworkException) {
    // Network error (will be auto-retried)
} catch (e: Exception) {
    // Other errors
}
```

## Configuration

### buildconfig Fields
```gradle
android {
    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", "\"http://localhost:8000\"")
            buildConfigField("String", "PROJECT_ID", "\"dev-project\"")
        }
    }
}
```

### Application Setup
```kotlin
class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        OwnFirebaseProvider.initialize(
            baseUrl = BuildConfig.API_BASE_URL,
            projectId = BuildConfig.PROJECT_ID
        )
    }
}
```

## Token Management

```kotlin
// After login
val tokens = sdk.auth().login(email, password)
sdk.setAccessToken(tokens.access)
prefs.putString("access_token", tokens.access)
prefs.putString("refresh_token", tokens.refresh)

// On token expiration (401)
val newTokens = sdk.auth().refreshToken(refreshToken)
sdk.setAccessToken(newTokens["access"].toString())

// On logout
prefs.remove("access_token")
prefs.remove("refresh_token")
sdk.setAccessToken("")
```

## Coroutines Integration

```kotlin
// With lifecycleScope (Android)
lifecycleScope.launch {
    try {
        val docs = sdk.data().listDocuments("posts")
        // Update UI on main thread
        updateUI(docs)
    } catch (e: Exception) {
        showError(e.message)
    }
}

// With async
viewModelScope.launch {
    val docs = async { sdk.data().listDocuments("posts") }
    val result = docs.await()
}
```

## Performance Tips

1. **Batch Analytics Events:** Use `queueEvent()` instead of `logEvent()` for high volume
2. **Cache Remote Config:** Call `refreshCache()` periodically, not on every check
3. **Lazy Initialization:** Services are lazy-loaded, only initialize what you need
4. **Stream Large Uploads:** Use `uploadFromStream()` for files larger than available RAM
5. **Reuse SDK Instance:** Create once, reuse throughout app lifetime

## Common Patterns

### Login with Persistence
```kotlin
// Login
val tokens = sdk.auth().login(email, password)
sdk.setAccessToken(tokens.access)
prefs.edit { putString("access_token", tokens.access) }

// On app start
val token = prefs.getString("access_token")
if (token != null) {
    sdk.setAccessToken(token)
    val user = sdk.auth().getMe()  // Verify token valid
}
```

### Real-time Document Listener
```kotlin
val listener = RealtimeDocumentListener(
    onUpdate = { data ->
        println("Document updated: $data")
        updateUI(data)
    },
    onDelete = {
        println("Document deleted")
        clearUI()
    },
    onError = { error ->
        println("Error: ${error.message}")
    }
)
sdk.realtime().addListener(listener)
sdk.realtime().subscribe("users", "user123")
```

### Exception Handling
```kotlin
class CrashHandler : Thread.UncaughtExceptionHandler {
    override fun uncaughtException(t: Thread, e: Throwable) {
        OwnFirebaseProvider.getInstance().crashlytics()
            .reportException(e)
        defaultHandler?.uncaughtException(t, e)
    }
}
```

## Dependency Versions

```gradle
OkHttp: 4.11.0
Gson: 2.10.1
Kotlin: 1.9.0+
Coroutines: 1.7.1
JVM Target: Java 11+
```

## Links & Resources

- **README.md** - Full API documentation (400+ lines)
- **INTEGRATION.md** - Android setup guide (600+ lines)
- **ExampleUsage.kt** - Working code examples (400+ lines)
- **OwnFirebaseTest.kt** - Unit tests (300+ lines)
- **Build:** `./gradlew build`
- **Tests:** `./gradlew test`
- **Documentation:** `./gradlew dokka`

## Support

**For implementation details:** See IMPLEMENTATION_SUMMARY.md
**For Android setup:** See INTEGRATION.md
**For API docs:** See README.md
**For examples:** See ExampleUsage.kt and OwnFirebaseTest.kt
**For complete checklist:** See CHECKLIST.md

---

**Total Implementation:** 3500+ lines of production-ready code across 20 files with comprehensive documentation.
