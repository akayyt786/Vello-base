# Kotlin SDK Integration Guide

This guide explains how to integrate the OwnFirebase Kotlin SDK into your Android or Kotlin application.

## Table of Contents

1. [Installation](#installation)
2. [Basic Setup](#basic-setup)
3. [Authentication Flow](#authentication-flow)
4. [Real-time Updates](#real-time-updates)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Installation

### Gradle (Android/Kotlin)

Add to your `build.gradle` or `build.gradle.kts`:

```gradle
dependencies {
    // OwnFirebase SDK
    implementation 'com.ownfirebase:kotlin-sdk:1.0.0'
    
    // Or if you prefer to build locally
    implementation project(':kotlin-sdk')
}
```

### Maven

```xml
<dependency>
    <groupId>com.ownfirebase</groupId>
    <artifactId>kotlin-sdk</artifactId>
    <version>1.0.0</version>
</dependency>
```

## Basic Setup

### Android Application Setup

Create an Application class to initialize the SDK:

```kotlin
import android.app.Application
import android.content.SharedPreferences
import androidx.preference.PreferenceManager
import com.ownfirebase.sdk.OwnFirebaseProvider

class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        
        // Initialize SDK with your base URL and project ID
        OwnFirebaseProvider.initialize(
            baseUrl = BuildConfig.API_BASE_URL,
            projectId = BuildConfig.PROJECT_ID
        )
        
        // Restore saved access token if available
        val prefs = PreferenceManager.getDefaultSharedPreferences(this)
        val accessToken = prefs.getString("access_token", null)
        if (accessToken != null) {
            OwnFirebaseProvider.getInstance().setAccessToken(accessToken)
        }
    }
    
    override fun onTerminate() {
        OwnFirebaseProvider.shutdown()
        super.onTerminate()
    }
}
```

Register the Application class in `AndroidManifest.xml`:

```xml
<application
    android:name=".MyApplication"
    ...>
</application>
```

### Configuration via BuildConfig

Create `build.gradle.kts`:

```kotlin
android {
    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", "\"http://localhost:8000\"")
            buildConfigField("String", "PROJECT_ID", "\"dev-project\"")
        }
        release {
            buildConfigField("String", "API_BASE_URL", "\"https://api.example.com\"")
            buildConfigField("String", "PROJECT_ID", "\"prod-project\"")
        }
    }
}
```

## Authentication Flow

### Login

```kotlin
import com.ownfirebase.sdk.OwnFirebaseProvider
import com.ownfirebase.sdk.types.APIError
import android.content.SharedPreferences
import androidx.preference.PreferenceManager

class LoginActivity : AppCompatActivity() {
    private val sdk = OwnFirebaseProvider.getInstance()
    private lateinit var prefs: SharedPreferences
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        prefs = PreferenceManager.getDefaultSharedPreferences(this)
    }
    
    private fun handleLogin(email: String, password: String) {
        lifecycleScope.launch {
            try {
                val tokens = sdk.auth().login(email, password)
                
                // Save tokens
                sdk.setAccessToken(tokens.access)
                prefs.edit {
                    putString("access_token", tokens.access)
                    putString("refresh_token", tokens.refresh)
                    putString("user_id", tokens.user_id)
                }
                
                // Navigate to home
                startActivity(Intent(this@LoginActivity, HomeActivity::class.java))
                finish()
                
            } catch (e: APIError) {
                when (e.status) {
                    401 -> showError("Invalid email or password")
                    429 -> showError("Too many login attempts. Please try again later.")
                    else -> showError("Login failed: ${e.message}")
                }
            } catch (e: Exception) {
                showError("Network error: ${e.message}")
            }
        }
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}
```

### Registration

```kotlin
private fun handleSignup(email: String, password: String, username: String) {
    lifecycleScope.launch {
        try {
            val tokens = sdk.auth().register(email, password, username)
            
            // Save tokens and proceed
            sdk.setAccessToken(tokens.access)
            prefs.edit {
                putString("access_token", tokens.access)
                putString("refresh_token", tokens.refresh)
            }
            
            navigateToHome()
            
        } catch (e: APIError) {
            showError("Signup failed: ${e.message}")
        }
    }
}
```

### Token Refresh

```kotlin
private suspend fun getValidAccessToken(): String {
    val currentToken = sdk.getAccessToken()
    if (currentToken != null) {
        // TODO: Check if token is about to expire
        return currentToken
    }
    
    // Refresh token
    val refreshToken = prefs.getString("refresh_token", null)
        ?: throw IllegalStateException("No refresh token available")
    
    try {
        val result = sdk.auth().refreshToken(refreshToken)
        val newAccessToken = result["access"] as String
        
        sdk.setAccessToken(newAccessToken)
        prefs.edit {
            putString("access_token", newAccessToken)
        }
        
        return newAccessToken
    } catch (e: APIError) {
        // Refresh failed, user needs to login again
        logoutUser()
        throw e
    }
}

private fun logoutUser() {
    prefs.edit {
        remove("access_token")
        remove("refresh_token")
        remove("user_id")
    }
    
    val intent = Intent(this, LoginActivity::class.java)
    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
    startActivity(intent)
}
```

## Real-time Updates

### Collection Listener

```kotlin
import com.ownfirebase.sdk.realtime.RealtimeCollectionListener

class PostsFragment : Fragment() {
    private val sdk = OwnFirebaseProvider.getInstance()
    private var collectionListener: RealtimeCollectionListener? = null
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // Create listener
        collectionListener = RealtimeCollectionListener(
            onAdd = { docId, data ->
                Log.d("Posts", "Document added: $docId")
                updateUI()
            },
            onModify = { docId, data ->
                Log.d("Posts", "Document modified: $docId")
                updateUI()
            },
            onRemove = { docId ->
                Log.d("Posts", "Document removed: $docId")
                updateUI()
            },
            onError = { error ->
                Log.e("Posts", "Real-time error: ${error.message}")
                showError("Connection lost")
            }
        )
        
        // Subscribe
        sdk.realtime().addListener(collectionListener!!)
        sdk.realtime().subscribe("posts")
    }
    
    override fun onDestroyView() {
        collectionListener?.let {
            sdk.realtime().removeListener(it)
        }
        super.onDestroyView()
    }
    
    private fun updateUI() {
        // Reload posts from server or update from cache
    }
}
```

## Error Handling

### Global Error Handler

```kotlin
import com.ownfirebase.sdk.types.APIError
import com.ownfirebase.sdk.types.NetworkException

class ErrorHandler {
    fun handle(exception: Exception, context: Context) {
        when (exception) {
            is APIError -> handleAPIError(exception, context)
            is NetworkException -> handleNetworkError(exception, context)
            else -> handleGenericError(exception, context)
        }
    }
    
    private fun handleAPIError(error: APIError, context: Context) {
        val message = when (error.status) {
            400 -> "Invalid request: ${error.detail}"
            401 -> "Unauthorized. Please login again."
            403 -> "You don't have permission for this action."
            404 -> "Resource not found."
            429 -> "Too many requests. Please try again later."
            500 -> "Server error. Please try again later."
            else -> "Error: ${error.message}"
        }
        
        Toast.makeText(context, message, Toast.LENGTH_LONG).show()
        
        if (error.status == 401) {
            // Clear tokens and redirect to login
            PreferenceManager.getDefaultSharedPreferences(context).edit {
                remove("access_token")
                remove("refresh_token")
            }
        }
    }
    
    private fun handleNetworkError(error: NetworkException, context: Context) {
        Toast.makeText(
            context,
            "Network error: ${error.message}",
            Toast.LENGTH_LONG
        ).show()
    }
    
    private fun handleGenericError(error: Exception, context: Context) {
        Toast.makeText(
            context,
            "An error occurred: ${error.message}",
            Toast.LENGTH_LONG
        ).show()
    }
}
```

## Best Practices

### 1. Use Coroutines

Always make SDK calls from a coroutine to avoid blocking the UI thread:

```kotlin
lifecycleScope.launch {
    try {
        val docs = sdk.data().listDocuments("posts")
        // Update UI on main thread
        updatePostsList(docs.results)
    } catch (e: Exception) {
        showError(e.message)
    }
}
```

### 2. Token Management

Implement automatic token refresh:

```kotlin
class TokenInterceptor(private val sdk: OwnFirebase) {
    fun intercept(request: Request): Request {
        val token = sdk.getAccessToken() ?: return request
        
        return request.newBuilder()
            .addHeader("Authorization", "Bearer $token")
            .build()
    }
}
```

### 3. Analytics Setup

Track user interactions throughout the app:

```kotlin
class AnalyticsHelper(private val sdk: OwnFirebase) {
    fun trackScreenView(screenName: String) {
        sdk.analytics().queueEvent(
            "screen_view",
            mapOf("screen_name" to screenName)
        )
    }
    
    fun trackButtonClick(buttonName: String) {
        sdk.analytics().queueEvent(
            "button_click",
            mapOf("button_name" to buttonName)
        )
    }
    
    fun trackPurchase(amount: Double, currency: String) {
        sdk.analytics().logEvent(
            "purchase",
            mapOf(
                "amount" to amount,
                "currency" to currency
            )
        )
    }
}

// Usage in Activities/Fragments
class HomeActivity : AppCompatActivity() {
    private val analytics = AnalyticsHelper(OwnFirebaseProvider.getInstance())
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        analytics.trackScreenView("home")
    }
}
```

### 4. Crash Reporting

Automatically report exceptions:

```kotlin
class CrashHandler : Thread.UncaughtExceptionHandler {
    override fun uncaughtException(t: Thread, e: Throwable) {
        OwnFirebaseProvider.getInstance().crashlytics().reportException(e)
        // Default handler
        defaultHandler?.uncaughtException(t, e)
    }
    
    companion object {
        private var defaultHandler: Thread.UncaughtExceptionHandler? = null
        
        fun init(sdk: OwnFirebase) {
            defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
            Thread.setDefaultUncaughtExceptionHandler(CrashHandler())
        }
    }
}

// In Application
class MyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        val sdk = OwnFirebaseProvider.getInstance()
        CrashHandler.init(sdk)
    }
}
```

### 5. Remote Config for Feature Flags

```kotlin
class FeatureFlags {
    private val config = OwnFirebaseProvider.getInstance().remoteConfig()
    
    fun isNewDesignEnabled(): Boolean {
        return config.getBoolean("new_design_enabled", false)
    }
    
    fun getMaxUploadSize(): Long {
        return config.getNumber("max_upload_size_mb", 10.0).toLong() * 1024 * 1024
    }
    
    fun refreshFlags() {
        config.refreshCache()
    }
}

// Usage
class MainActivity : AppCompatActivity() {
    private val features = FeatureFlags()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        if (features.isNewDesignEnabled()) {
            setContentView(R.layout.activity_main_new)
        } else {
            setContentView(R.layout.activity_main_old)
        }
    }
}
```

## Troubleshooting

### Issue: 401 Unauthorized on every request

**Solution:** Check that you're setting the access token after login:

```kotlin
val tokens = sdk.auth().login(email, password)
sdk.setAccessToken(tokens.access)  // Don't forget this!
```

### Issue: WebSocket connection fails

**Solution:** Check that WebSocket is allowed in your network configuration. For Android:

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.INTERNET" />
```

### Issue: Slow analytics events

**Solution:** Use `queueEvent()` for batch operations instead of individual `logEvent()` calls:

```kotlin
// ❌ Slow
for (i in 1..100) {
    sdk.analytics().logEvent("event", mapOf("index" to i))
}

// ✅ Fast
for (i in 1..100) {
    sdk.analytics().queueEvent("event", mapOf("index" to i))
}
sdk.analytics().flush()
```

### Issue: OutOfMemory with large file uploads

**Solution:** Stream the upload for large files:

```kotlin
val inputStream = FileInputStream(file)
val uploaded = sdk.storage().uploadFromStream(
    inputStream,
    filename = file.name,
    contentType = "application/octet-stream"
)
```

### Issue: Session expires during app use

**Solution:** Implement token refresh on 401 errors:

```kotlin
try {
    sdk.data().listDocuments("posts")
} catch (e: APIError) {
    if (e.status == 401) {
        val newToken = sdk.auth().refreshToken(refreshToken)["access"].toString()
        sdk.setAccessToken(newToken)
        // Retry
        sdk.data().listDocuments("posts")
    }
}
```

## Support

For issues or questions:
1. Check the README.md for API documentation
2. Review ExampleUsage.kt for code examples
3. Check backend API documentation at `/api/v1/docs/`
4. Open an issue on GitHub
