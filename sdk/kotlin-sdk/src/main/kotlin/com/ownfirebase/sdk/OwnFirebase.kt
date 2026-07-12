package com.ownfirebase.sdk

import com.ownfirebase.sdk.analytics.AnalyticsService
import com.ownfirebase.sdk.auth.AuthService
import com.ownfirebase.sdk.config.RemoteConfigService
import com.ownfirebase.sdk.crashlytics.CrashlyticsService
import com.ownfirebase.sdk.data.DataService
import com.ownfirebase.sdk.realtime.RealtimeListener
import com.ownfirebase.sdk.storage.StorageService
import com.ownfirebase.sdk.types.OwnFirebaseConfig

/**
 * Main OwnFirebase SDK class.
 * Provides unified access to all OwnFirebase services: Auth, Data, Storage, Analytics, etc.
 *
 * Example usage:
 * ```kotlin
 * val sdk = OwnFirebase(
 *     baseUrl = "https://api.example.com",
 *     projectId = "my-project",
 *     accessToken = "..."
 * )
 *
 * // Use services
 * val user = sdk.auth().getMe()
 * val docs = sdk.data().listDocuments("users")
 * sdk.analytics().logEvent("page_view")
 * ```
 */
class OwnFirebase(
    baseUrl: String,
    projectId: String? = null,
    accessToken: String? = null
) {
    private val config = OwnFirebaseConfig(
        baseUrl = baseUrl,
        projectId = projectId,
        accessToken = accessToken
    )

    private val authService: AuthService by lazy { AuthService(config) }
    private val dataService: DataService by lazy { DataService(config) }
    private val storageService: StorageService by lazy { StorageService(config) }
    private val analyticsService: AnalyticsService by lazy { AnalyticsService(config) }
    private val crashlyticsService: CrashlyticsService by lazy { CrashlyticsService(config) }
    private val remoteConfigService: RemoteConfigService by lazy { RemoteConfigService(config) }
    private val realtimeListener: RealtimeListener by lazy {
        RealtimeListener(config.baseUrl, config.projectId, config.accessToken)
    }

    // ─── Service Accessors ────────────────────────────────────────────────────

    /**
     * Get the authentication service.
     * Use for login, signup, MFA, social auth, etc.
     */
    fun auth(): AuthService = authService

    /**
     * Get the data service.
     * Use for CRUD operations on collections and documents.
     */
    fun data(): DataService = dataService

    /**
     * Get the storage service.
     * Use for file uploads and downloads.
     */
    fun storage(): StorageService = storageService

    /**
     * Get the analytics service.
     * Use for event tracking and analytics queries.
     */
    fun analytics(): AnalyticsService = analyticsService

    /**
     * Get the crashlytics service.
     * Use for crash reporting and performance monitoring.
     */
    fun crashlytics(): CrashlyticsService = crashlyticsService

    /**
     * Get the remote config service.
     * Use for feature flags and remote configuration.
     */
    fun remoteConfig(): RemoteConfigService = remoteConfigService

    /**
     * Get the real-time listener.
     * Use for listening to real-time updates on collections and documents.
     */
    fun realtime(): RealtimeListener = realtimeListener

    // ─── Token Management ────────────────────────────────────────────────────

    /**
     * Set the access token for authenticated requests.
     * Call this after login or when token is refreshed.
     *
     * @param token JWT access token
     */
    fun setAccessToken(token: String) {
        authService.setAccessToken(token)
        dataService.setAccessToken(token)
        storageService.setAccessToken(token)
        analyticsService.setAccessToken(token)
        crashlyticsService.setAccessToken(token)
        remoteConfigService.setAccessToken(token)
    }

    /**
     * Get the current access token.
     */
    fun getAccessToken(): String? = authService.getAccessToken()

    /**
     * Set the project ID.
     * Required for most operations.
     *
     * @param projectId Project ID
     */
    fun setProjectId(projectId: String) {
        authService.setProjectId(projectId)
        dataService.setProjectId(projectId)
        storageService.setProjectId(projectId)
        analyticsService.setProjectId(projectId)
        crashlyticsService.setProjectId(projectId)
        remoteConfigService.setProjectId(projectId)
    }

    /**
     * Get the current project ID.
     */
    fun getProjectId(): String? = authService.getProjectId()

    // ─── Lifecycle ───────────────────────────────────────────────────────────

    /**
     * Clean up resources (close connections, flush analytics, etc).
     * Call this when the app is shutting down.
     */
    fun shutdown() {
        analyticsService.stopBatcher()
        realtimeListener.disconnect()
    }
}

/**
 * Create an OwnFirebase SDK instance with the given configuration.
 */
fun createOwnFirebase(
    baseUrl: String,
    projectId: String? = null,
    accessToken: String? = null
): OwnFirebase {
    return OwnFirebase(baseUrl, projectId, accessToken)
}

/**
 * Singleton holder for a global OwnFirebase instance (optional).
 */
object OwnFirebaseProvider {
    private var instance: OwnFirebase? = null

    fun initialize(
        baseUrl: String,
        projectId: String? = null,
        accessToken: String? = null
    ) {
        instance = OwnFirebase(baseUrl, projectId, accessToken)
    }

    fun getInstance(): OwnFirebase {
        return instance ?: throw IllegalStateException(
            "OwnFirebase not initialized. Call OwnFirebaseProvider.initialize() first."
        )
    }

    fun shutdown() {
        instance?.shutdown()
        instance = null
    }
}
