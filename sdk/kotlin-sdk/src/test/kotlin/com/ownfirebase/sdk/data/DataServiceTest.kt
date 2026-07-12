package com.ownfirebase.sdk.data

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

/**
 * Unit tests for DataService.
 * Tests all CRUD operations with mocked backend.
 */
class DataServiceTest {
    private lateinit var mockServer: MockWebServer
    private lateinit var dataService: DataService
    private val gson = Gson()

    @Before
    fun setUp() {
        mockServer = MockWebServer()
        mockServer.start()

        val config = OwnFirebaseConfig(
            baseUrl = mockServer.url("").toString().removeSuffix("/"),
            projectId = "test-project",
            accessToken = "test-token"
        )
        dataService = DataService(config)
    }

    @After
    fun tearDown() {
        mockServer.shutdown()
    }

    // ─── Collection Tests ────────────────────────────────────────────────────

    @Test
    fun testListCollections() {
        val mockCollections = listOf(
            DataCollection(id = "coll_1", name = "users", document_count = 100),
            DataCollection(id = "coll_2", name = "posts", document_count = 500),
            DataCollection(id = "coll_3", name = "comments", document_count = 2000)
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockCollections))
        )

        val result = dataService.listCollections()

        assertEquals(3, result.size)
        assertEquals("users", result[0].name)
        assertEquals(100, result[0].document_count)
        assertEquals("posts", result[1].name)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("collections/") == true)
    }

    @Test
    fun testCreateCollection() {
        val mockCollection = DataCollection(
            id = "coll_new",
            name = "products",
            document_count = 0
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockCollection))
        )

        val result = dataService.createCollection("products")

        assertEquals("coll_new", result.id)
        assertEquals("products", result.name)
        assertEquals(0, result.document_count)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("collections/") == true)
    }

    // ─── Document Tests ──────────────────────────────────────────────────────

    @Test
    fun testListDocuments() {
        val mockResponse = PaginatedResponse(
            count = 2,
            next = null,
            previous = null,
            results = listOf(
                DataDocument(
                    id = "doc_1",
                    collection = "users",
                    data = mapOf("name" to "Alice", "age" to 30),
                    created_at = "2024-01-01T00:00:00Z",
                    updated_at = "2024-01-01T00:00:00Z"
                ),
                DataDocument(
                    id = "doc_2",
                    collection = "users",
                    data = mapOf("name" to "Bob", "age" to 25),
                    created_at = "2024-01-02T00:00:00Z",
                    updated_at = "2024-01-02T00:00:00Z"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = dataService.listDocuments("users")

        assertEquals(2, result.count)
        assertEquals("doc_1", result.results[0].id)
        assertEquals("Alice", result.results[0].data["name"])
        assertEquals(30.0, result.results[0].data["age"])
        assertEquals("Bob", result.results[1].data["name"])

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("collections/users/docs") == true)
    }

    @Test
    fun testListDocumentsWithFilters() {
        val mockResponse = PaginatedResponse(
            count = 1,
            next = null,
            previous = null,
            results = listOf(
                DataDocument(
                    id = "doc_1",
                    collection = "users",
                    data = mapOf("name" to "Alice", "age" to 30),
                    created_at = "2024-01-01T00:00:00Z",
                    updated_at = "2024-01-01T00:00:00Z"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val filters = mapOf("age__gte" to "25", "age__lte" to "35")
        val result = dataService.listDocuments("users", filters)

        assertEquals(1, result.count)
        assertEquals("doc_1", result.results[0].id)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("collections/users/docs") == true)
        assertTrue(request.path?.contains("age__gte=25") == true)
    }

    @Test
    fun testGetDocument() {
        val mockDocument = DataDocument(
            id = "doc_1",
            collection = "users",
            data = mapOf("name" to "Alice", "email" to "alice@example.com"),
            created_at = "2024-01-01T00:00:00Z",
            updated_at = "2024-01-01T00:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockDocument))
        )

        val result = dataService.getDocument("users", "doc_1")

        assertEquals("doc_1", result.id)
        assertEquals("users", result.collection)
        assertEquals("Alice", result.data["name"])
        assertEquals("alice@example.com", result.data["email"])

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("collections/users/docs/doc_1") == true)
    }

    @Test
    fun testGetDocumentFromSubcollection() {
        val mockDocument = DataDocument(
            id = "post_1",
            collection = "users/user_123/posts",
            data = mapOf("title" to "My Post", "content" to "Hello World"),
            created_at = "2024-01-01T00:00:00Z",
            updated_at = "2024-01-01T00:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockDocument))
        )

        val result = dataService.getDocument("users/user_123/posts", "post_1")

        assertEquals("post_1", result.id)
        assertEquals("My Post", result.data["title"])

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("users/user_123/posts") == true)
    }

    @Test
    fun testCreateDocument() {
        val newData = mapOf(
            "name" to "Charlie",
            "age" to 28,
            "email" to "charlie@example.com"
        )

        val mockDocument = DataDocument(
            id = "doc_new",
            collection = "users",
            data = newData,
            created_at = "2024-01-03T00:00:00Z",
            updated_at = "2024-01-03T00:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockDocument))
        )

        val result = dataService.createDocument("users", newData)

        assertEquals("doc_new", result.id)
        assertEquals("Charlie", result.data["name"])
        assertEquals(28.0, result.data["age"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("collections/users/docs") == true)
    }

    @Test
    fun testUpdateDocument() {
        val updateData = mapOf(
            "age" to 31
        )

        val mockDocument = DataDocument(
            id = "doc_1",
            collection = "users",
            data = mapOf("name" to "Alice", "age" to 31, "email" to "alice@example.com"),
            created_at = "2024-01-01T00:00:00Z",
            updated_at = "2024-01-03T12:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockDocument))
        )

        val result = dataService.updateDocument("users", "doc_1", updateData)

        assertEquals("doc_1", result.id)
        assertEquals(31.0, result.data["age"])
        assertEquals("Alice", result.data["name"]) // Other fields preserved

        val request = mockServer.takeRequest()
        assertEquals("PATCH", request.method)
        assertTrue(request.path?.contains("collections/users/docs/doc_1") == true)
    }

    @Test
    fun testReplaceDocument() {
        val newData = mapOf(
            "name" to "Alice Updated",
            "age" to 32,
            "email" to "alice.updated@example.com",
            "verified" to true
        )

        val mockDocument = DataDocument(
            id = "doc_1",
            collection = "users",
            data = newData,
            created_at = "2024-01-01T00:00:00Z",
            updated_at = "2024-01-03T13:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockDocument))
        )

        val result = dataService.replaceDocument("users", "doc_1", newData)

        assertEquals("doc_1", result.id)
        assertEquals("Alice Updated", result.data["name"])
        assertEquals(32.0, result.data["age"])
        assertEquals(true, result.data["verified"])

        val request = mockServer.takeRequest()
        assertEquals("PUT", request.method)
        assertTrue(request.path?.contains("collections/users/docs/doc_1") == true)
    }

    @Test
    fun testDeleteDocument() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(204)
        )

        dataService.deleteDocument("users", "doc_1")

        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
        assertTrue(request.path?.contains("collections/users/docs/doc_1") == true)
    }

    // ─── Batch / Transaction Tests ────────────────────────────────────────────

    @Test
    fun testWriteBatch() {
        val operations = listOf(
            WriteBatchOperation(
                op = "set",
                collection = "users",
                doc_id = "user_1",
                data = mapOf("name" to "User1", "active" to true)
            ),
            WriteBatchOperation(
                op = "update",
                collection = "users",
                doc_id = "user_2",
                data = mapOf("active" to false)
            ),
            WriteBatchOperation(
                op = "delete",
                collection = "users",
                doc_id = "user_3"
            )
        )

        val mockResult = WriteBatchResult(
            written = 3,
            errors = emptyList()
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResult))
        )

        val result = dataService.writeBatch(operations)

        assertEquals(3, result.written)
        assertEquals(0, result.errors.size)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("transaction") == true)
    }

    @Test
    fun testWriteBatchWithErrors() {
        val operations = listOf(
            WriteBatchOperation(
                op = "set",
                collection = "users",
                doc_id = "user_1",
                data = mapOf("name" to "User1")
            ),
            WriteBatchOperation(
                op = "delete",
                collection = "nonexistent",
                doc_id = "nonexistent_1"
            )
        )

        val mockResult = WriteBatchResult(
            written = 1,
            errors = listOf(mapOf("index" to 1, "message" to "Collection not found"))
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(207) // Multi-status
                .setBody(gson.toJson(mockResult))
        )

        val result = dataService.writeBatch(operations)

        assertEquals(1, result.written)
        assertEquals(1, result.errors.size)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
    }

    @Test
    fun testBatchBuilder() {
        val batch = DataService.BatchBuilder()
            .set("users", "user_1", mapOf("name" to "User1"))
            .update("users", "user_2", mapOf("active" to true))
            .delete("users", "user_3")
            .build()

        assertEquals(3, batch.size)
        assertEquals("set", batch[0].op)
        assertEquals("update", batch[1].op)
        assertEquals("delete", batch[2].op)
    }

    // ─── Security Rules Tests ────────────────────────────────────────────────

    @Test
    fun testGetRules() {
        val mockRules = mapOf(
            "rules" to """
                allow read: if request.auth != null;
                allow write: if request.auth.uid == resource.data.owner_id;
            """.trimIndent()
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockRules))
        )

        val result = dataService.getRules()

        assertNotNull(result["rules"])
        assertTrue(result["rules"]!!.contains("allow read"))

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("rules") == true)
    }

    @Test
    fun testUpdateRules() {
        val newRules = """
            allow read: if request.auth != null;
            allow write: if request.auth.uid == resource.data.owner_id;
        """.trimIndent()

        val mockResult = mapOf(
            "message" to "Rules updated successfully",
            "version" to "2"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResult))
        )

        val result = dataService.updateRules(newRules)

        assertNotNull(result["message"])
        assertEquals("2", result["version"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("rules") == true)
    }

    @Test
    fun testTestRules() {
        val context = mapOf(
            "auth" to mapOf("uid" to "user_123"),
            "resource" to mapOf("data" to mapOf("owner_id" to "user_123"))
        )

        val mockResult = mapOf(
            "allow" to true,
            "reason" to "User is owner"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResult))
        )

        val result = dataService.testRules(
            "allow write: if request.auth.uid == resource.data.owner_id;",
            context
        )

        assertEquals(true, result["allow"])
        assertEquals("User is owner", result["reason"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("rules/test") == true)
    }
}
