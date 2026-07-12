package com.ownfirebase.sdk.analytics

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
 * Unit tests for AnalyticsService.
 * Tests event logging, batching, user properties, and queries.
 */
class AnalyticsServiceTest {
    private lateinit var mockServer: MockWebServer
    private lateinit var analyticsService: AnalyticsService
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
        analyticsService = AnalyticsService(config)
    }

    @After
    fun tearDown() {
        analyticsService.stopBatcher()
        mockServer.shutdown()
    }

    // ─── Event Tracking Tests ────────────────────────────────────────────────

    @Test
    fun testLogEvent() {
        val mockEvent = AnalyticsEvent(
            id = "event_1",
            name = "page_view",
            params = mapOf("page" to "/home", "referrer" to "/login"),
            timestamp = "2024-01-01T12:00:00Z",
            user_id = "user_123",
            session_id = "session_456"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockEvent))
        )

        val result = analyticsService.logEvent(
            name = "page_view",
            params = mapOf("page" to "/home", "referrer" to "/login"),
            userId = "user_123",
            sessionId = "session_456"
        )

        assertEquals("event_1", result.id)
        assertEquals("page_view", result.name)
        assertEquals("/home", result.params["page"])
        assertEquals("user_123", result.user_id)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("analytics/events") == true)
    }

    @Test
    fun testLogEventWithoutOptionalParams() {
        val mockEvent = AnalyticsEvent(
            id = "event_2",
            name = "app_launch",
            params = emptyMap(),
            timestamp = "2024-01-01T12:05:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockEvent))
        )

        val result = analyticsService.logEvent(name = "app_launch")

        assertEquals("event_2", result.id)
        assertEquals("app_launch", result.name)
        assertEquals(0, result.params.size)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
    }

    @Test
    fun testQueueEvent() {
        // Queue event should be buffered locally
        analyticsService.queueEvent(
            name = "button_click",
            params = mapOf("button_id" to "submit_btn"),
            userId = "user_123"
        )

        // Wait a bit for async processing
        Thread.sleep(100)

        // No immediate request should be made (batching)
        assertEquals(0, mockServer.requestCount)
    }

    @Test
    fun testQueueMultipleEventsAndFlush() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("{}")
        )

        // Queue multiple events
        for (i in 1..5) {
            analyticsService.queueEvent(
                name = "event_$i",
                params = mapOf("index" to i.toString()),
                userId = "user_123"
            )
        }

        // Force flush
        analyticsService.flush()

        // Check that batch request was made
        assertTrue(mockServer.requestCount >= 1)
        val requests = (0 until mockServer.requestCount).map { mockServer.takeRequest() }
        val batchRequest = requests.last()
        assertEquals("POST", batchRequest.method)
        assertTrue(batchRequest.path?.contains("analytics/events/batch") == true)
    }

    @Test
    fun testListEvents() {
        val mockResponse = PaginatedResponse(
            count = 3,
            next = null,
            previous = null,
            results = listOf(
                AnalyticsEvent(
                    id = "event_1",
                    name = "page_view",
                    params = mapOf("page" to "/home"),
                    timestamp = "2024-01-01T12:00:00Z"
                ),
                AnalyticsEvent(
                    id = "event_2",
                    name = "page_view",
                    params = mapOf("page" to "/products"),
                    timestamp = "2024-01-01T12:05:00Z"
                ),
                AnalyticsEvent(
                    id = "event_3",
                    name = "button_click",
                    params = mapOf("button_id" to "add_cart"),
                    timestamp = "2024-01-01T12:10:00Z"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = analyticsService.listEvents()

        assertEquals(3, result.count)
        assertEquals("page_view", result.results[0].name)
        assertEquals("button_click", result.results[2].name)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("analytics/events") == true)
    }

    @Test
    fun testListEventsWithFilters() {
        val mockResponse = PaginatedResponse(
            count = 1,
            next = null,
            previous = null,
            results = listOf(
                AnalyticsEvent(
                    id = "event_1",
                    name = "page_view",
                    params = mapOf("page" to "/home"),
                    timestamp = "2024-01-01T12:00:00Z",
                    user_id = "user_123"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val filters = mapOf("name" to "page_view", "user_id" to "user_123")
        val result = analyticsService.listEvents(filters)

        assertEquals(1, result.count)
        assertEquals("user_123", result.results[0].user_id)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("name=page_view") == true)
    }

    // ─── User Properties Tests ───────────────────────────────────────────────

    @Test
    fun testSetUserProperty() {
        val mockProperty = UserProperty(
            id = "prop_1",
            name = "subscription_tier",
            value = "premium",
            user_id = "user_123"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockProperty))
        )

        val result = analyticsService.setUserProperty("subscription_tier", "premium")

        assertEquals("prop_1", result.id)
        assertEquals("subscription_tier", result.name)
        assertEquals("premium", result.value)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("analytics/user-properties") == true)
    }

    @Test
    fun testListUserProperties() {
        val mockResponse = PaginatedResponse(
            count = 3,
            next = null,
            previous = null,
            results = listOf(
                UserProperty(
                    id = "prop_1",
                    name = "subscription_tier",
                    value = "premium",
                    user_id = "user_123"
                ),
                UserProperty(
                    id = "prop_2",
                    name = "country",
                    value = "US",
                    user_id = "user_123"
                ),
                UserProperty(
                    id = "prop_3",
                    name = "language",
                    value = "en",
                    user_id = "user_123"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = analyticsService.listUserProperties()

        assertEquals(3, result.count)
        assertEquals("subscription_tier", result.results[0].name)
        assertEquals("premium", result.results[0].value)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("analytics/user-properties") == true)
    }

    // ─── Conversion Events Tests ─────────────────────────────────────────────

    @Test
    fun testMarkConversionEvent() {
        val mockResult = mapOf(
            "message" to "Conversion event marked",
            "name" to "purchase"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockResult))
        )

        val result = analyticsService.markConversionEvent("purchase")

        assertNotNull(result["message"])
        assertEquals("purchase", result["name"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("analytics/conversion-events") == true)
    }

    @Test
    fun testListConversionEvents() {
        val mockResponse = PaginatedResponse(
            count = 2,
            next = null,
            previous = null,
            results = listOf(
                mapOf("name" to "purchase", "created_at" to "2024-01-01T00:00:00Z"),
                mapOf("name" to "signup", "created_at" to "2024-01-02T00:00:00Z")
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = analyticsService.listConversionEvents()

        assertEquals(2, result.count)
        assertEquals("purchase", result.results[0]["name"])
        assertEquals("signup", result.results[1]["name"])

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("analytics/conversion-events") == true)
    }

    // ─── Query Tests ──────────────────────────────────────────────────────────

    @Test
    fun testQueryEventCount() {
        val mockResult = AnalyticsQueryResult(
            metric = "event_count",
            dimension = null,
            rows = listOf(
                AnalyticsRow(
                    dimension_value = null,
                    metric_value = 1500.0,
                    date = "2024-01-01"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResult))
        )

        val result = analyticsService.query(
            metric = "event_count",
            startDate = "2024-01-01",
            endDate = "2024-01-01"
        )

        assertEquals("event_count", result.metric)
        assertEquals(1500.0, result.rows[0].metric_value)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("analytics/query") == true)
    }

    @Test
    fun testQueryByDimension() {
        val mockResult = AnalyticsQueryResult(
            metric = "event_count",
            dimension = "event_name",
            rows = listOf(
                AnalyticsRow(
                    dimension_value = "page_view",
                    metric_value = 1000.0,
                    date = "2024-01-01"
                ),
                AnalyticsRow(
                    dimension_value = "button_click",
                    metric_value = 500.0,
                    date = "2024-01-01"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResult))
        )

        val result = analyticsService.query(
            metric = "event_count",
            dimension = "event_name",
            startDate = "2024-01-01",
            endDate = "2024-01-01"
        )

        assertEquals("event_name", result.dimension)
        assertEquals(2, result.rows.size)
        assertEquals("page_view", result.rows[0].dimension_value)
        assertEquals(1000.0, result.rows[0].metric_value)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
    }

    @Test
    fun testQueryWithDateRange() {
        val mockResult = AnalyticsQueryResult(
            metric = "user_count",
            dimension = null,
            rows = listOf(
                AnalyticsRow(
                    dimension_value = null,
                    metric_value = 100.0,
                    date = "2024-01-01"
                ),
                AnalyticsRow(
                    dimension_value = null,
                    metric_value = 120.0,
                    date = "2024-01-02"
                ),
                AnalyticsRow(
                    dimension_value = null,
                    metric_value = 150.0,
                    date = "2024-01-03"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResult))
        )

        val result = analyticsService.query(
            metric = "user_count",
            startDate = "2024-01-01",
            endDate = "2024-01-03"
        )

        assertEquals(3, result.rows.size)
        assertEquals(100.0, result.rows[0].metric_value)
        assertEquals(150.0, result.rows[2].metric_value)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
    }

    @Test
    fun testQueryWithFilters() {
        val mockResult = AnalyticsQueryResult(
            metric = "event_count",
            dimension = null,
            rows = listOf(
                AnalyticsRow(
                    dimension_value = null,
                    metric_value = 500.0,
                    date = "2024-01-01"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResult))
        )

        val filters = mapOf("event_name" to "page_view", "country" to "US")
        val result = analyticsService.query(
            metric = "event_count",
            filters = filters
        )

        assertEquals(1, result.rows.size)
        assertEquals(500.0, result.rows[0].metric_value)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
    }

    // ─── Batch Operations Tests ───────────────────────────────────────────────

    @Test
    fun testFlushEmptyBatch() {
        // Flush with no events should not make any requests
        analyticsService.flush()
        assertEquals(0, mockServer.requestCount)
    }

    @Test
    fun testStopBatcher() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("{}")
        )

        analyticsService.queueEvent("test_event", mapOf("key" to "value"))
        Thread.sleep(50)

        analyticsService.stopBatcher()

        // After stopping, batcher thread should be stopped
        Thread.sleep(100)
        // Batcher should have flushed any remaining events
    }
}
