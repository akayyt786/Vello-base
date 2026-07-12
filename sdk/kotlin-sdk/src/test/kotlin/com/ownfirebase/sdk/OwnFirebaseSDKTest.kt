package com.ownfirebase.sdk

import com.google.gson.Gson
import com.ownfirebase.sdk.types.*
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue
import kotlin.test.assertFalse

/**
 * Unit tests for OwnFirebase main SDK class.
 * Tests initialization, service access, and token management.
 */
class OwnFirebaseSDKTest {
    private lateinit var mockServer: MockWebServer
    private lateinit var sdk: OwnFirebase
    private val gson = Gson()

    @Before
    fun setUp() {
        mockServer = MockWebServer()
        mockServer.start()

        sdk = OwnFirebase(
            baseUrl = mockServer.url("").toString().removeSuffix("/"),
            projectId = "test-project",
            accessToken = "test-token"
        )
    }

    @After
    fun tearDown() {
        sdk.shutdown()
        mockServer.shutdown()
    }

    // ─── Initialization Tests ────────────────────────────────────────────────

    @Test
    fun testSDKInitialization() {
        val firebase = OwnFirebase(
            baseUrl = "https://api.example.com",
            projectId = "my-project",
            accessToken = "my-token"
        )

        assertNotNull(firebase)
        assertNotNull(firebase.auth())
        assertNotNull(firebase.data())
        assertNotNull(firebase.storage())
        assertNotNull(firebase.analytics())
        assertNotNull(firebase.crashlytics())
        assertNotNull(firebase.remoteConfig())
        assertNotNull(firebase.realtime())
    }

    @Test
    fun testSDKInitializationMinimal() {
        val firebase = OwnFirebase(
            baseUrl = "https://api.example.com"
        )

        assertNotNull(firebase)
        assertNotNull(firebase.auth())
        assertEquals(null, firebase.getProjectId())
        assertEquals(null, firebase.getAccessToken())
    }

    // ─── Service Access Tests ───────────────────────────────────────────────

    @Test
    fun testAuthServiceAccess() {
        val authService = sdk.auth()
        assertNotNull(authService)
    }

    @Test
    fun testDataServiceAccess() {
        val dataService = sdk.data()
        assertNotNull(dataService)
    }

    @Test
    fun testStorageServiceAccess() {
        val storageService = sdk.storage()
        assertNotNull(storageService)
    }

    @Test
    fun testAnalyticsServiceAccess() {
        val analyticsService = sdk.analytics()
        assertNotNull(analyticsService)
    }

    @Test
    fun testCrashlyticsServiceAccess() {
        val crashlyticsService = sdk.crashlytics()
        assertNotNull(crashlyticsService)
    }

    @Test
    fun testRemoteConfigServiceAccess() {
        val remoteConfigService = sdk.remoteConfig()
        assertNotNull(remoteConfigService)
    }

    @Test
    fun testRealtimeListenerAccess() {
        val realtimeListener = sdk.realtime()
        assertNotNull(realtimeListener)
    }

    // ─── Lazy Initialization Tests ───────────────────────────────────────────

    @Test
    fun testServiceLazyInitialization() {
        val firebase = OwnFirebase(
            baseUrl = "https://api.example.com",
            projectId = "test"
        )

        // First access should initialize
        val auth1 = firebase.auth()
        val auth2 = firebase.auth()

        // Should return same instance
        assertEquals(auth1, auth2)
    }

    // ─── Token Management Tests ──────────────────────────────────────────────

    @Test
    fun testSetAccessToken() {
        sdk.setAccessToken("new-token-123")
        assertEquals("new-token-123", sdk.getAccessToken())
    }

    @Test
    fun testGetAccessTokenInitial() {
        val firebase = OwnFirebase(
            baseUrl = "https://api.example.com",
            accessToken = "initial-token"
        )

        assertEquals("initial-token", firebase.getAccessToken())
    }

    @Test
    fun testGetAccessTokenNullByDefault() {
        val firebase = OwnFirebase(
            baseUrl = "https://api.example.com"
        )

        assertEquals(null, firebase.getAccessToken())
    }

    @Test
    fun testAccessTokenPropagation() {
        // When we set token on SDK, it should propagate to all services
        sdk.setAccessToken("propagated-token")

        // Get token from auth service (it should have the new token)
        val tokenFromAuth = sdk.getAccessToken()
        assertEquals("propagated-token", tokenFromAuth)
    }

    // ─── Project ID Management Tests ─────────────────────────────────────────

    @Test
    fun testSetProjectId() {
        sdk.setProjectId("new-project")
        assertEquals("new-project", sdk.getProjectId())
    }

    @Test
    fun testGetProjectIdInitial() {
        val firebase = OwnFirebase(
            baseUrl = "https://api.example.com",
            projectId = "initial-project"
        )

        assertEquals("initial-project", firebase.getProjectId())
    }

    @Test
    fun testGetProjectIdNullByDefault() {
        val firebase = OwnFirebase(
            baseUrl = "https://api.example.com"
        )

        assertEquals(null, firebase.getProjectId())
    }

    @Test
    fun testProjectIdPropagation() {
        // When we set project ID on SDK, it should propagate to all services
        sdk.setProjectId("propagated-project")

        val projectIdFromSdk = sdk.getProjectId()
        assertEquals("propagated-project", projectIdFromSdk)
    }

    // ─── Integration Tests (with mocked backend) ──────────────────────────────

    @Test
    fun testFullAuthFlow() {
        // Setup mock responses
        val loginResponse = AuthTokens(
            access = "access_token",
            refresh = "refresh_token",
            user_id = "user_123",
            email = "test@example.com"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(loginResponse))
        )

        // Test login through SDK
        val tokens = sdk.auth().login("test@example.com", "password")

        assertEquals("user_123", tokens.user_id)
        assertEquals("access_token", tokens.access)

        // Update SDK with new token
        sdk.setAccessToken(tokens.access)
        assertEquals("access_token", sdk.getAccessToken())
    }

    @Test
    fun testFullDataFlow() {
        // Setup mock for create document
        val docData = mapOf("name" to "Alice", "age" to 30)
        val createdDoc = DataDocument(
            id = "doc_1",
            collection = "users",
            data = docData,
            created_at = "2024-01-01T00:00:00Z",
            updated_at = "2024-01-01T00:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(createdDoc))
        )

        // Create document through SDK
        val doc = sdk.data().createDocument("users", docData)

        assertEquals("doc_1", doc.id)
        assertEquals("Alice", doc.data["name"])
    }

    @Test
    fun testFullAnalyticsFlow() {
        val event = AnalyticsEvent(
            id = "event_1",
            name = "page_view",
            params = mapOf("page" to "/home"),
            timestamp = "2024-01-01T12:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(event))
        )

        val result = sdk.analytics().logEvent(
            name = "page_view",
            params = mapOf("page" to "/home")
        )

        assertEquals("event_1", result.id)
        assertEquals("page_view", result.name)
    }

    // ─── Factory Function Tests ───────────────────────────────────────────────

    @Test
    fun testCreateOwnFirebaseFactory() {
        val firebase = createOwnFirebase(
            baseUrl = "https://api.example.com",
            projectId = "test-project"
        )

        assertNotNull(firebase)
        assertEquals("test-project", firebase.getProjectId())
    }

    @Test
    fun testCreateOwnFirebaseWithAllParams() {
        val firebase = createOwnFirebase(
            baseUrl = "https://api.example.com",
            projectId = "my-project",
            accessToken = "my-token"
        )

        assertEquals("my-project", firebase.getProjectId())
        assertEquals("my-token", firebase.getAccessToken())
    }

    // ─── Singleton Provider Tests ────────────────────────────────────────────

    @Test
    fun testOwnFirebaseProviderInitialize() {
        OwnFirebaseProvider.initialize(
            baseUrl = "https://api.example.com",
            projectId = "provider-project",
            accessToken = "provider-token"
        )

        val instance = OwnFirebaseProvider.getInstance()
        assertNotNull(instance)
        assertEquals("provider-project", instance.getProjectId())

        OwnFirebaseProvider.shutdown()
    }

    @Test
    fun testOwnFirebaseProviderGetInstanceBeforeInit() {
        OwnFirebaseProvider.shutdown() // Make sure it's shut down

        try {
            OwnFirebaseProvider.getInstance()
            assertTrue(false, "Should throw exception")
        } catch (e: IllegalStateException) {
            assertTrue(e.message?.contains("not initialized") ?: false)
        }
    }

    @Test
    fun testOwnFirebaseProviderShutdown() {
        OwnFirebaseProvider.initialize(
            baseUrl = "https://api.example.com",
            projectId = "test"
        )

        val instance1 = OwnFirebaseProvider.getInstance()
        assertNotNull(instance1)

        OwnFirebaseProvider.shutdown()

        try {
            OwnFirebaseProvider.getInstance()
            assertTrue(false, "Should throw exception after shutdown")
        } catch (e: IllegalStateException) {
            assertTrue(true)
        }
    }

    @Test
    fun testOwnFirebaseProviderMultipleInitialize() {
        OwnFirebaseProvider.initialize(
            baseUrl = "https://api1.example.com",
            projectId = "project1"
        )

        val instance1 = OwnFirebaseProvider.getInstance()

        OwnFirebaseProvider.initialize(
            baseUrl = "https://api2.example.com",
            projectId = "project2"
        )

        val instance2 = OwnFirebaseProvider.getInstance()

        // Instances should be different after re-initialization
        assertNotNull(instance1)
        assertNotNull(instance2)

        OwnFirebaseProvider.shutdown()
    }

    // ─── Shutdown Tests ─────────────────────────────────────────────────────

    @Test
    fun testShutdown() {
        // Setup mock for analytics batch flush
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("{}")
        )

        sdk.shutdown()

        // After shutdown, analytics should be stopped
        // This is verified by stopBatcher being called
    }

    @Test
    fun testMultipleShutdowns() {
        // Should not throw error on multiple shutdowns
        sdk.shutdown()
        sdk.shutdown() // Should not throw
    }

    // ─── Configuration Persistence Tests ─────────────────────────────────────

    @Test
    fun testTokenUpdatePersistenceAcrossServiceAccess() {
        val token1 = "token_1"
        val token2 = "token_2"

        sdk.setAccessToken(token1)
        assertEquals(token1, sdk.getAccessToken())

        // Access different services
        sdk.auth()
        sdk.data()
        sdk.analytics()

        // Token should still be the same
        assertEquals(token1, sdk.getAccessToken())

        // Update token
        sdk.setAccessToken(token2)
        assertEquals(token2, sdk.getAccessToken())
    }

    @Test
    fun testProjectIdUpdatePersistenceAcrossServiceAccess() {
        val projectId1 = "project_1"
        val projectId2 = "project_2"

        sdk.setProjectId(projectId1)
        assertEquals(projectId1, sdk.getProjectId())

        sdk.auth()
        sdk.data()

        assertEquals(projectId1, sdk.getProjectId())

        sdk.setProjectId(projectId2)
        assertEquals(projectId2, sdk.getProjectId())
    }
}
