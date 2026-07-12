package com.ownfirebase.sdk.example

import com.ownfirebase.sdk.OwnFirebase
import com.ownfirebase.sdk.realtime.RealtimeCollectionListener
import com.ownfirebase.sdk.types.APIError
import com.ownfirebase.sdk.types.WriteBatchOperation
import java.io.File

/**
 * Example usage of the OwnFirebase Kotlin SDK.
 * Demonstrates all major features and best practices.
 */
fun main() {
    // ─── Initialize SDK ───────────────────────────────────────────────────────

    val sdk = OwnFirebase(
        baseUrl = "https://api.example.com",
        projectId = "my-project"
    )

    try {
        // ─── Authentication ───────────────────────────────────────────────────

        // User login
        println("=== Authentication ===")
        try {
            val tokens = sdk.auth().login(
                email = "user@example.com",
                password = "password123"
            )

            println("Login successful!")
            println("Access Token: ${tokens.access.take(10)}...")
            println("User ID: ${tokens.user_id}")

            // Set the access token for future requests
            sdk.setAccessToken(tokens.access)

            // Get current user
            val user = sdk.auth().getMe()
            println("Current user: ${user.email}")
        } catch (e: APIError) {
            println("Login failed: ${e.message}")
            return
        }

        // ─── Data Operations ──────────────────────────────────────────────────

        println("\n=== Data Operations ===")

        // Create a document
        val newPost = sdk.data().createDocument(
            collection = "posts",
            data = mapOf(
                "title" to "Kotlin SDK Tutorial",
                "content" to "Learn how to use OwnFirebase",
                "tags" to listOf("kotlin", "firebase", "tutorial"),
                "published" to true
            )
        )
        println("Created document: ${newPost.id}")

        // Read a document
        val post = sdk.data().getDocument("posts", newPost.id)
        println("Retrieved document: ${post.data}")

        // Update a document
        val updated = sdk.data().updateDocument(
            collection = "posts",
            docId = newPost.id,
            data = mapOf("view_count" to 42)
        )
        println("Updated document: ${updated.data}")

        // List documents
        val posts = sdk.data().listDocuments(
            collection = "posts",
            filters = mapOf("published" to "true")
        )
        println("Found ${posts.count} posts")
        posts.results.forEach { doc ->
            println("  - ${doc.data["title"]}")
        }

        // Batch operations
        val batchOps = listOf(
            WriteBatchOperation(
                op = "set",
                collection = "posts",
                doc_id = "post1",
                data = mapOf("title" to "Post 1")
            ),
            WriteBatchOperation(
                op = "update",
                collection = "posts",
                doc_id = newPost.id,
                data = mapOf("featured" to true)
            )
        )
        val batchResult = sdk.data().writeBatch(batchOps)
        println("Batch write: ${batchResult.written} operations successful")

        // ─── File Storage ────────────────────────────────────────────────────

        println("\n=== File Storage ===")

        // Upload a file
        val fileContent = "Hello, OwnFirebase!".toByteArray()
        val uploadedFile = sdk.storage().upload(
            file = fileContent,
            filename = "greeting.txt",
            contentType = "text/plain",
            path = "documents/"
        )
        println("Uploaded file: ${uploadedFile.name} (${uploadedFile.size} bytes)")

        // List files
        val files = sdk.storage().listFiles(prefix = "documents/")
        println("Files in documents/: ${files.results.size}")
        files.results.forEach { file ->
            println("  - ${file.name} (${file.size} bytes)")
        }

        // Download file
        val downloadedContent = sdk.storage().download(uploadedFile.url)
        println("Downloaded: ${downloadedContent.size} bytes")

        // ─── Analytics ────────────────────────────────────────────────────────

        println("\n=== Analytics ===")

        // Log events
        sdk.analytics().logEvent(
            name = "tutorial_started",
            params = mapOf(
                "language" to "kotlin",
                "difficulty" to "beginner"
            )
        )
        println("Event logged: tutorial_started")

        // Queue events for batch
        for (i in 1..5) {
            sdk.analytics().queueEvent(
                name = "page_view",
                params = mapOf("page" to "tutorial_step_$i")
            )
        }

        // Set user property
        sdk.analytics().setUserProperty("subscription_level", "premium")

        // Query analytics
        val analyticsResult = sdk.analytics().query(
            metric = "event_count",
            dimension = "event_name",
            startDate = "2024-01-01"
        )
        println("Analytics query result: ${analyticsResult.rows.size} rows")

        // ─── Crashlytics ──────────────────────────────────────────────────────

        println("\n=== Crashlytics ===")

        // Record a crash
        try {
            throw IllegalArgumentException("Example exception for testing")
        } catch (e: Exception) {
            val crash = sdk.crashlytics().reportException(
                exception = e,
                deviceInfo = mapOf(
                    "device" to "test-device",
                    "os" to "Android 14"
                )
            )
            println("Crash reported: ${crash.id}")
        }

        // Performance tracing
        val result = sdk.crashlytics().trace("data_fetch") {
            Thread.sleep(100) // Simulate work
            "data"
        }
        println("Trace recorded for 'data_fetch'")

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
        println("Crash summary: ${summary.total_crashes} total crashes")

        // ─── Remote Config ────────────────────────────────────────────────────

        println("\n=== Remote Config ===")

        // Get config values
        val featureEnabled = sdk.remoteConfig().getBoolean("new_feature_enabled", false)
        println("New feature enabled: $featureEnabled")

        val maxRetries = sdk.remoteConfig().getNumber("max_retries", 3.0)
        println("Max retries: $maxRetries")

        val apiEndpoint = sdk.remoteConfig().getString("api_endpoint", "https://api.example.com")
        println("API endpoint: $apiEndpoint")

        // Refresh config cache
        sdk.remoteConfig().refreshCache()
        println("Config cache refreshed")

        // ─── Real-time Listeners ──────────────────────────────────────────────

        println("\n=== Real-time Listeners ===")

        // Create a collection listener
        val collectionListener = RealtimeCollectionListener(
            onAdd = { docId, data ->
                println("Document added: $docId")
                data?.forEach { (k, v) -> println("  $k: $v") }
            },
            onModify = { docId, data ->
                println("Document modified: $docId")
            },
            onRemove = { docId ->
                println("Document removed: $docId")
            },
            onError = { error ->
                println("Real-time error: ${error.message}")
            }
        )

        // Subscribe to collection
        sdk.realtime().addListener(collectionListener)
        sdk.realtime().subscribe("posts")
        println("Subscribed to 'posts' collection")

        // Keep listener running for a bit
        Thread.sleep(2000)

        // ─── Error Handling ───────────────────────────────────────────────────

        println("\n=== Error Handling ===")

        try {
            sdk.data().getDocument("posts", "nonexistent-id")
        } catch (e: APIError) {
            println("API Error: ${e.status} - ${e.message}")
            println("Detail: ${e.detail}")
        } catch (e: Exception) {
            println("Unexpected error: ${e.message}")
        }

        // ─── Cleanup ──────────────────────────────────────────────────────────

        println("\n=== Cleanup ===")
        sdk.realtime().disconnect()
        sdk.analytics().flush()
        sdk.shutdown()
        println("SDK cleaned up")

    } finally {
        // Always clean up
        sdk.shutdown()
    }
}

/**
 * Example of handling token refresh.
 */
fun exampleTokenRefresh(sdk: OwnFirebase) {
    try {
        sdk.data().listDocuments("posts")
    } catch (e: APIError) {
        if (e.status == 401) {
            println("Token expired, refreshing...")

            // Get refresh token (would be stored from login)
            val refreshToken = "stored_refresh_token"

            try {
                val newTokens = sdk.auth().refreshToken(refreshToken)
                sdk.setAccessToken(newTokens["access"].toString())
                println("Token refreshed successfully")

                // Retry the operation
                sdk.data().listDocuments("posts")
            } catch (e: APIError) {
                println("Token refresh failed: ${e.message}")
                // Redirect to login
            }
        } else {
            throw e
        }
    }
}

/**
 * Example of batch event tracking.
 */
fun exampleBatchAnalytics(sdk: OwnFirebase) {
    println("Queuing events for batch...")

    for (i in 1..100) {
        sdk.analytics().queueEvent(
            name = "user_action",
            params = mapOf(
                "action_id" to i,
                "timestamp" to System.currentTimeMillis()
            )
        )
    }

    println("Events queued, will be sent automatically")
    // Events are sent automatically when batch reaches 100 or 30 seconds pass
}

/**
 * Example of setting up custom auth with MFA.
 */
fun exampleMFASetup(sdk: OwnFirebase) {
    // User logs in
    val tokens = sdk.auth().login("user@example.com", "password")
    sdk.setAccessToken(tokens.access)

    // Enroll in TOTP
    val totpSetup = sdk.auth().enrollTOTP()
    println("TOTP URI: ${totpSetup["totp_uri"]}")
    println("Secret: ${totpSetup["secret"]}")

    // Confirm enrollment with TOTP code from authenticator app
    val confirmResult = sdk.auth().confirmTOTP("123456")
    println("TOTP confirmed")

    // At next login, user would verify TOTP:
    // val tokens = sdk.auth().login("user@example.com", "password")
    // val totpTokens = sdk.auth().verifyTOTP("654321") // TOTP code from app
}
