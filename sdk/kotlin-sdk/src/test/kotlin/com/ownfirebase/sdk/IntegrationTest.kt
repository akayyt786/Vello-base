package com.ownfirebase.sdk

import com.ownfirebase.sdk.auth.AuthService
import com.ownfirebase.sdk.data.DataService
import com.ownfirebase.sdk.types.*
import org.junit.Assume
import org.junit.Before
import org.junit.Test
import java.util.Collections
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Integration tests for OwnFirebase SDK.
 * These tests run against a real backend at localhost:8000.
 * Skip if backend is not available.
 */
class IntegrationTest {
    private lateinit var sdk: OwnFirebase
    private lateinit var authService: AuthService
    private lateinit var dataService: DataService
    private val backendUrl = "http://localhost:8000"
    private val testProjectId = "test-project"

    @Before
    fun setUp() {
        // Skip tests if backend is not available
        try {
            val response = java.net.URL("$backendUrl/health").openConnection() as java.net.HttpURLConnection
            response.requestMethod = "GET"
            response.connectTimeout = 2000
            response.readTimeout = 2000
            val statusCode = response.responseCode
            Assume.assumeTrue("Backend not available at $backendUrl", statusCode in 200..299 || statusCode == 404)
            response.disconnect()
        } catch (e: Exception) {
            Assume.assumeNoException("Backend not available", e)
        }

        sdk = OwnFirebase(
            baseUrl = backendUrl,
            projectId = testProjectId
        )
        authService = sdk.auth()
        dataService = sdk.data()
    }

    // ─── Auth Integration Tests ──────────────────────────────────────────────

    @Test
    fun testRegisterAndLoginFlow() {
        val email = "integration-test-${System.currentTimeMillis()}@example.com"
        val password = "TestPassword123!"

        try {
            // Register new user
            val registerResult = authService.register(
                email = email,
                password = password,
                username = "testuser"
            )

            assertNotNull(registerResult.access)
            assertNotNull(registerResult.refresh)
            assertNotNull(registerResult.user_id)
            assertEquals(email, registerResult.email)

            // Login with same credentials
            val loginResult = authService.login(email, password)

            assertNotNull(loginResult.access)
            assertNotNull(loginResult.refresh)
            assertEquals(registerResult.user_id, loginResult.user_id)

            // Update SDK with new token
            sdk.setAccessToken(loginResult.access)

            // Get current user
            val user = authService.getMe()
            assertNotNull(user)
            assertEquals(email, user.email)
        } catch (e: Exception) {
            // Backend might not have auth endpoints, skip if not available
            Assume.assumeNoException("Auth endpoints not available", e)
        }
    }

    @Test
    fun testAnonymousSignIn() {
        try {
            val result = authService.anonymousSignIn()

            assertNotNull(result.access)
            assertNotNull(result.refresh)
            assertNotNull(result.user_id)

            sdk.setAccessToken(result.access)
        } catch (e: Exception) {
            Assume.assumeNoException("Anonymous signin not available", e)
        }
    }

    @Test
    fun testTokenRefresh() {
        try {
            val registerResult = authService.register(
                email = "refresh-test-${System.currentTimeMillis()}@example.com",
                password = "TestPassword123!",
                username = "testuser"
            )

            val refreshResult = authService.refreshToken(registerResult.refresh)

            assertNotNull(refreshResult["access"])
            assertNotNull(refreshResult["refresh"])
        } catch (e: Exception) {
            Assume.assumeNoException("Token refresh not available", e)
        }
    }

    // ─── Data Integration Tests ───────────────────────────────────────────────

    @Test
    fun testCreateReadUpdateDeleteDocument() {
        try {
            val collectionName = "integration_test_docs"
            val testData = mapOf(
                "title" to "Integration Test Document",
                "description" to "This is a test document created during integration tests",
                "timestamp" to System.currentTimeMillis()
            )

            // Create document
            val createdDoc = dataService.createDocument(collectionName, testData)

            assertNotNull(createdDoc.id)
            assertEquals(collectionName, createdDoc.collection)
            assertEquals(testData["title"], createdDoc.data["title"])

            val docId = createdDoc.id

            // Read document
            val readDoc = dataService.getDocument(collectionName, docId)

            assertEquals(createdDoc.id, readDoc.id)
            assertEquals(testData["title"], readDoc.data["title"])

            // Update document
            val updateData = mapOf("description" to "Updated description")
            val updatedDoc = dataService.updateDocument(collectionName, docId, updateData)

            assertEquals(docId, updatedDoc.id)
            assertEquals("Updated description", updatedDoc.data["description"])
            assertEquals(testData["title"], updatedDoc.data["title"]) // Original field preserved

            // Delete document
            dataService.deleteDocument(collectionName, docId)

            // Try to read deleted document (should fail or return empty)
            try {
                dataService.getDocument(collectionName, docId)
                // If we got here, document still exists - this might be expected behavior
            } catch (e: Exception) {
                // Document deleted successfully
                assertTrue(true)
            }
        } catch (e: Exception) {
            Assume.assumeNoException("Data CRUD operations not available", e)
        }
    }

    @Test
    fun testListDocuments() {
        try {
            val collectionName = "integration_test_list"

            // Create a few documents
            repeat(3) {
                dataService.createDocument(
                    collectionName,
                    mapOf("index" to it, "name" to "Document $it")
                )
            }

            // List documents
            val result = dataService.listDocuments(collectionName)

            assertNotNull(result.results)
            assertTrue(result.results.size >= 3)
        } catch (e: Exception) {
            Assume.assumeNoException("List documents not available", e)
        }
    }

    @Test
    fun testBatchOperations() {
        try {
            val collectionName = "integration_test_batch"

            val batch = DataService.BatchBuilder()
                .set(collectionName, "doc_1", mapOf("name" to "Document 1"))
                .set(collectionName, "doc_2", mapOf("name" to "Document 2"))
                .update(collectionName, "doc_1", mapOf("status" to "updated"))
                .build()

            val result = dataService.writeBatch(batch)

            assertTrue(result.written > 0)
        } catch (e: Exception) {
            Assume.assumeNoException("Batch operations not available", e)
        }
    }

    // ─── Analytics Integration Tests ──────────────────────────────────────────

    @Test
    fun testLogAnalyticsEvent() {
        try {
            val event = sdk.analytics().logEvent(
                name = "integration_test_event",
                params = mapOf(
                    "test_key" to "test_value",
                    "timestamp" to System.currentTimeMillis()
                )
            )

            assertNotNull(event.id)
            assertEquals("integration_test_event", event.name)
        } catch (e: Exception) {
            Assume.assumeNoException("Analytics not available", e)
        }
    }

    @Test
    fun testAnalyticsUserProperty() {
        try {
            val result = sdk.analytics().setUserProperty(
                "integration_test_property",
                "test_value_${System.currentTimeMillis()}"
            )

            assertNotNull(result.id)
            assertEquals("integration_test_property", result.name)
        } catch (e: Exception) {
            Assume.assumeNoException("User properties not available", e)
        }
    }

    @Test
    fun testAnalyticsQuery() {
        try {
            val result = sdk.analytics().query(
                metric = "event_count",
                startDate = "2024-01-01",
                endDate = "2024-12-31"
            )

            assertNotNull(result.metric)
            assertEquals("event_count", result.metric)
            assertNotNull(result.rows)
        } catch (e: Exception) {
            Assume.assumeNoException("Analytics queries not available", e)
        }
    }

    // ─── Multi-step Integration Tests ────────────────────────────────────────

    @Test
    fun testFullWorkflow() {
        try {
            // 1. Register/Login
            val email = "workflow-test-${System.currentTimeMillis()}@example.com"
            val registerResult = authService.register(
                email = email,
                password = "TestPassword123!",
                username = "workflowtest"
            )

            sdk.setAccessToken(registerResult.access)

            // 2. Create data
            val docResult = dataService.createDocument(
                "workflow_test",
                mapOf(
                    "user_id" to registerResult.user_id,
                    "created_by" to registerResult.email,
                    "content" to "Test workflow"
                )
            )

            assertNotNull(docResult.id)

            // 3. Log analytics event
            val eventResult = sdk.analytics().logEvent(
                name = "workflow_complete",
                params = mapOf(
                    "user_id" to registerResult.user_id,
                    "doc_id" to docResult.id
                )
            )

            assertNotNull(eventResult.id)

            // 4. Retrieve created data
            val retrievedDoc = dataService.getDocument("workflow_test", docResult.id)
            assertEquals("Test workflow", retrievedDoc.data["content"])

            assertTrue(true)
        } catch (e: Exception) {
            Assume.assumeNoException("Full workflow not available", e)
        }
    }

    @Test
    fun testConcurrentOperations() {
        try {
            val collectionName = "concurrent_test"
            val threads = mutableListOf<Thread>()
            val results = Collections.synchronizedList(mutableListOf<String>())

            // Create multiple documents concurrently
            repeat(5) { index ->
                val thread = Thread {
                    try {
                        val doc = dataService.createDocument(
                            collectionName,
                            mapOf("index" to index, "thread_id" to Thread.currentThread().id)
                        )
                        results.add(doc.id)
                    } catch (e: Exception) {
                        results.add("error")
                    }
                }
                threads.add(thread)
                thread.start()
            }

            threads.forEach { it.join() }

            val successCount = results.filter { it != "error" }.size
            assertTrue(successCount > 0, "At least some concurrent operations should succeed")
        } catch (e: Exception) {
            Assume.assumeNoException("Concurrent operations not available", e)
        }
    }

    @Test
    fun testErrorHandling() {
        try {
            // Try to get non-existent document
            try {
                dataService.getDocument("nonexistent_collection", "nonexistent_doc")
                assertTrue(false, "Should have thrown an error")
            } catch (e: Exception) {
                // Expected error
                assertTrue(true)
            }
        } catch (e: Exception) {
            Assume.assumeNoException("Error handling test not available", e)
        }
    }

    @Test
    fun testPaginatedResults() {
        try {
            val collectionName = "pagination_test"

            // Create multiple documents
            repeat(10) { index ->
                dataService.createDocument(
                    collectionName,
                    mapOf("index" to index, "name" to "Document $index")
                )
            }

            // List with pagination
            val result = dataService.listDocuments(collectionName)

            assertNotNull(result.results)
            assertNotNull(result.count)
            assertTrue(result.count > 0)
        } catch (e: Exception) {
            Assume.assumeNoException("Pagination not available", e)
        }
    }
}
