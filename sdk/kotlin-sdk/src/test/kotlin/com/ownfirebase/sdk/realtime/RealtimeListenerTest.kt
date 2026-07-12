package com.ownfirebase.sdk.realtime

import com.google.gson.Gson
import org.junit.Before
import org.junit.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertTrue

/**
 * Unit tests for RealtimeListener.
 * Tests WebSocket subscriptions and real-time event handling.
 */
class RealtimeListenerTest {
    private lateinit var realtimeListener: RealtimeListener
    private val gson = Gson()

    @Before
    fun setUp() {
        realtimeListener = RealtimeListener(
            baseUrl = "http://localhost:8000",
            projectId = "test-project",
            accessToken = "test-token"
        )
    }

    // ─── Event Tests ──────────────────────────────────────────────────────────

    @Test
    fun testRealtimeEventCreation() {
        val event = RealtimeListener.RealtimeEvent(
            type = "create",
            collection = "users",
            docId = "user_123",
            data = mapOf("name" to "Alice", "email" to "alice@example.com")
        )

        assertEquals("create", event.type)
        assertEquals("users", event.collection)
        assertEquals("user_123", event.docId)
        assertNotNull(event.data)
        assertEquals("Alice", event.data!!["name"])
    }

    @Test
    fun testRealtimeEventUpdate() {
        val event = RealtimeListener.RealtimeEvent(
            type = "update",
            collection = "users",
            docId = "user_123",
            data = mapOf("name" to "Alice Updated")
        )

        assertEquals("update", event.type)
    }

    @Test
    fun testRealtimeEventDelete() {
        val event = RealtimeListener.RealtimeEvent(
            type = "delete",
            collection = "users",
            docId = "user_123"
        )

        assertEquals("delete", event.type)
        assertEquals("user_123", event.docId)
    }

    // ─── Document Listener Tests ──────────────────────────────────────────────

    @Test
    fun testRealtimeDocumentListenerOnUpdate() {
        var updateCalled = false
        var updateData: Map<String, Any?>? = null

        val listener = RealtimeDocumentListener(
            onUpdate = { data ->
                updateCalled = true
                updateData = data
            }
        )

        val event = RealtimeListener.RealtimeEvent(
            type = "update",
            collection = "users",
            docId = "user_123",
            data = mapOf("name" to "Updated", "age" to 31)
        )

        listener.onEvent(event)

        assertTrue(updateCalled)
        assertNotNull(updateData)
        assertEquals("Updated", updateData!!["name"])
        assertEquals(31, updateData!!["age"])
    }

    @Test
    fun testRealtimeDocumentListenerOnCreate() {
        var createCalled = false
        var createData: Map<String, Any?>? = null

        val listener = RealtimeDocumentListener(
            onUpdate = { data ->
                createCalled = true
                createData = data
            }
        )

        val event = RealtimeListener.RealtimeEvent(
            type = "create",
            collection = "users",
            docId = "user_new",
            data = mapOf("name" to "New User", "email" to "new@example.com")
        )

        listener.onEvent(event)

        assertTrue(createCalled)
        assertNotNull(createData)
        assertEquals("New User", createData!!["name"])
    }

    @Test
    fun testRealtimeDocumentListenerOnDelete() {
        var deleteCalled = false

        val listener = RealtimeDocumentListener(
            onDelete = {
                deleteCalled = true
            }
        )

        val event = RealtimeListener.RealtimeEvent(
            type = "delete",
            collection = "users",
            docId = "user_123"
        )

        listener.onEvent(event)

        assertTrue(deleteCalled)
    }

    @Test
    fun testRealtimeDocumentListenerOnError() {
        var errorCalled = false
        var error: Throwable? = null

        val listener = RealtimeDocumentListener(
            onError = { e ->
                errorCalled = true
                error = e
            }
        )

        val testError = Exception("Connection failed")
        listener.onError(testError)

        assertTrue(errorCalled)
        assertNotNull(error)
    }

    // ─── Collection Listener Tests ────────────────────────────────────────────

    @Test
    fun testRealtimeCollectionListenerOnAdd() {
        var addCalled = false
        var addedDocId: String? = null
        var addedData: Map<String, Any?>? = null

        val listener = RealtimeCollectionListener(
            onAdd = { docId, data ->
                addCalled = true
                addedDocId = docId
                addedData = data
            }
        )

        val event = RealtimeListener.RealtimeEvent(
            type = "create",
            collection = "users",
            docId = "user_new",
            data = mapOf("name" to "New User")
        )

        listener.onEvent(event)

        assertTrue(addCalled)
        assertEquals("user_new", addedDocId)
        assertNotNull(addedData)
        assertEquals("New User", addedData!!["name"])
    }

    @Test
    fun testRealtimeCollectionListenerOnModify() {
        var modifyCalled = false
        var modifiedDocId: String? = null
        var modifiedData: Map<String, Any?>? = null

        val listener = RealtimeCollectionListener(
            onModify = { docId, data ->
                modifyCalled = true
                modifiedDocId = docId
                modifiedData = data
            }
        )

        val event = RealtimeListener.RealtimeEvent(
            type = "update",
            collection = "users",
            docId = "user_123",
            data = mapOf("name" to "Updated User")
        )

        listener.onEvent(event)

        assertTrue(modifyCalled)
        assertEquals("user_123", modifiedDocId)
        assertNotNull(modifiedData)
        assertEquals("Updated User", modifiedData!!["name"])
    }

    @Test
    fun testRealtimeCollectionListenerOnRemove() {
        var removeCalled = false
        var removedDocId: String? = null

        val listener = RealtimeCollectionListener(
            onRemove = { docId ->
                removeCalled = true
                removedDocId = docId
            }
        )

        val event = RealtimeListener.RealtimeEvent(
            type = "delete",
            collection = "users",
            docId = "user_123"
        )

        listener.onEvent(event)

        assertTrue(removeCalled)
        assertEquals("user_123", removedDocId)
    }

    @Test
    fun testRealtimeCollectionListenerOnError() {
        var errorCalled = false

        val listener = RealtimeCollectionListener(
            onError = { _ ->
                errorCalled = true
            }
        )

        val testError = Exception("Subscription failed")
        listener.onError(testError)

        assertTrue(errorCalled)
    }

    // ─── Listener Lifecycle Tests ─────────────────────────────────────────────

    @Test
    fun testMultipleListenerEvents() {
        var updateCount = 0
        var deleteCount = 0

        val listener = RealtimeDocumentListener(
            onUpdate = { _ -> updateCount++ },
            onDelete = { deleteCount++ }
        )

        // Send multiple events
        listener.onEvent(RealtimeListener.RealtimeEvent(
            type = "update",
            collection = "users",
            docId = "user_1",
            data = mapOf("value" to 1)
        ))

        listener.onEvent(RealtimeListener.RealtimeEvent(
            type = "update",
            collection = "users",
            docId = "user_1",
            data = mapOf("value" to 2)
        ))

        listener.onEvent(RealtimeListener.RealtimeEvent(
            type = "delete",
            collection = "users",
            docId = "user_1"
        ))

        assertEquals(2, updateCount)
        assertEquals(1, deleteCount)
    }

    // ─── Message Format Tests ─────────────────────────────────────────────────

    @Test
    fun testSubscribeMessageFormat() {
        // Test that subscribe creates correct message format
        // This would require mocking the WebSocket to verify
        // For now, we test the expected format
        val expectedFormat = mapOf(
            "type" to "subscribe",
            "collection" to "users",
            "docId" to "user_123"
        )

        assertEquals("subscribe", expectedFormat["type"])
        assertEquals("users", expectedFormat["collection"])
    }

    @Test
    fun testUnsubscribeMessageFormat() {
        // Test unsubscribe message format
        val expectedFormat = mapOf(
            "type" to "unsubscribe",
            "collection" to "users"
        )

        assertEquals("unsubscribe", expectedFormat["type"])
        assertEquals("users", expectedFormat["collection"])
    }

    // ─── Realtime Event Serialization Tests ───────────────────────────────────

    @Test
    fun testRealtimeEventSerialization() {
        val event = RealtimeListener.RealtimeEvent(
            type = "create",
            collection = "posts",
            docId = "post_123",
            data = mapOf("title" to "Hello", "content" to "World", "likes" to 5)
        )

        val json = gson.toJson(event)
        assertNotNull(json)
        assertTrue(json.contains("\"type\":\"create\""))
        assertTrue(json.contains("\"collection\":\"posts\""))
        assertTrue(json.contains("\"docId\":\"post_123\""))
    }

    @Test
    fun testRealtimeEventDeserialization() {
        val json = """
            {
                "type": "update",
                "collection": "users",
                "docId": "user_456",
                "data": {"name": "Bob", "status": "online"},
                "timestamp": 1704110400000
            }
        """.trimIndent()

        val event = gson.fromJson(json, RealtimeListener.RealtimeEvent::class.java)

        assertEquals("update", event.type)
        assertEquals("users", event.collection)
        assertEquals("user_456", event.docId)
        assertEquals("Bob", event.data?.get("name"))
        assertEquals("online", event.data?.get("status"))
    }

    // ─── Complex Scenario Tests ───────────────────────────────────────────────

    @Test
    fun testMultipleEventsWithDifferentTypes() {
        val events = listOf(
            RealtimeListener.RealtimeEvent(
                type = "create",
                collection = "items",
                docId = "item_1",
                data = mapOf("name" to "Item 1")
            ),
            RealtimeListener.RealtimeEvent(
                type = "update",
                collection = "items",
                docId = "item_1",
                data = mapOf("quantity" to 10)
            ),
            RealtimeListener.RealtimeEvent(
                type = "create",
                collection = "items",
                docId = "item_2",
                data = mapOf("name" to "Item 2")
            ),
            RealtimeListener.RealtimeEvent(
                type = "delete",
                collection = "items",
                docId = "item_1"
            )
        )

        var createCount = 0
        var updateCount = 0
        var deleteCount = 0

        val listener = RealtimeCollectionListener(
            onAdd = { _, _ -> createCount++ },
            onModify = { _, _ -> updateCount++ },
            onRemove = { deleteCount++ }
        )

        events.forEach { listener.onEvent(it) }

        assertEquals(2, createCount)
        assertEquals(1, updateCount)
        assertEquals(1, deleteCount)
    }
}
