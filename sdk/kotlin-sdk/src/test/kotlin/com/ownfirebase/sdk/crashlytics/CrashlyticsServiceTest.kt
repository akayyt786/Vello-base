package com.ownfirebase.sdk.crashlytics

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
 * Unit tests for CrashlyticsService.
 * Tests crash reporting, performance monitoring, and analytics.
 */
class CrashlyticsServiceTest {
    private lateinit var mockServer: MockWebServer
    private lateinit var crashlyticsService: CrashlyticsService
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
        crashlyticsService = CrashlyticsService(config)
    }

    @After
    fun tearDown() {
        mockServer.shutdown()
    }

    @Test
    fun testReportCrash() {
        val mockResponse = CrashReport(
            id = "crash_1",
            exception_type = "NullPointerException",
            message = "Null pointer on line 42",
            stack_trace = "at com.example.MyClass.method(MyClass.kt:42)",
            occurred_at = "2024-01-01T12:00:00Z",
            app_version = "1.0.0",
            platform = "android"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockResponse))
        )

        val result = crashlyticsService.reportCrash(
            exceptionType = "NullPointerException",
            message = "Null pointer on line 42",
            stackTrace = "at com.example.MyClass.method(MyClass.kt:42)",
            appVersion = "1.0.0"
        )

        assertEquals("crash_1", result.id)
        assertEquals("NullPointerException", result.exception_type)
        assertEquals("Null pointer on line 42", result.message)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("crashlytics/reports") == true)
    }

    @Test
    fun testListCrashGroups() {
        val mockResponse = PaginatedResponse(
            count = 2,
            next = null,
            previous = null,
            results = listOf(
                CrashGroup(
                    id = "group_1",
                    exception_type = "NullPointerException",
                    message_summary = "Null pointer on line 42",
                    occurrence_count = 150,
                    affected_users = 45,
                    first_seen = "2024-01-01T00:00:00Z",
                    last_seen = "2024-01-03T12:00:00Z",
                    status = "open"
                ),
                CrashGroup(
                    id = "group_2",
                    exception_type = "OutOfMemoryError",
                    message_summary = "Java heap space",
                    occurrence_count = 87,
                    affected_users = 23,
                    first_seen = "2024-01-02T00:00:00Z",
                    last_seen = "2024-01-03T10:00:00Z",
                    status = "open"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = crashlyticsService.listCrashGroups()

        assertEquals(2, result.count)
        assertEquals("NullPointerException", result.results[0].exception_type)
        assertEquals(150, result.results[0].occurrence_count)
        assertEquals(45, result.results[0].affected_users)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("crashlytics/groups") == true)
    }

    @Test
    fun testGetCrashGroup() {
        val mockGroup = CrashGroup(
            id = "group_1",
            exception_type = "NullPointerException",
            message_summary = "Null pointer on line 42",
            occurrence_count = 200,
            affected_users = 60,
            first_seen = "2024-01-01T00:00:00Z",
            last_seen = "2024-01-04T00:00:00Z",
            status = "open"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockGroup))
        )

        val result = crashlyticsService.getCrashGroup("group_1")

        assertEquals("group_1", result.id)
        assertEquals("NullPointerException", result.exception_type)
        assertEquals(200, result.occurrence_count)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("crashlytics/groups/group_1") == true)
    }

    @Test
    fun testRecordTrace() {
        val mockTrace = PerformanceTrace(
            id = "trace_1",
            name = "login_flow",
            duration_ms = 1250,
            started_at = "2024-01-01T12:00:00Z",
            attributes = mapOf("user_id" to "user_123"),
            metrics = mapOf("http_calls" to 3.0, "db_queries" to 2.0)
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockTrace))
        )

        val result = crashlyticsService.recordTrace(
            name = "login_flow",
            durationMs = 1250,
            attributes = mapOf("user_id" to "user_123"),
            metrics = mapOf("http_calls" to 3.0, "db_queries" to 2.0)
        )

        assertEquals("trace_1", result.id)
        assertEquals("login_flow", result.name)
        assertEquals(1250L, result.duration_ms)
        assertEquals("user_123", result.attributes?.get("user_id"))

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("crashlytics/traces") == true)
    }

    @Test
    fun testListTraces() {
        val mockResponse = PaginatedResponse(
            count = 2,
            next = null,
            previous = null,
            results = listOf(
                PerformanceTrace(
                    id = "trace_1",
                    name = "login_flow",
                    duration_ms = 1250,
                    started_at = "2024-01-01T12:00:00Z"
                ),
                PerformanceTrace(
                    id = "trace_2",
                    name = "data_load",
                    duration_ms = 850,
                    started_at = "2024-01-01T12:05:00Z"
                )
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = crashlyticsService.listTraces()

        assertEquals(2, result.count)
        assertEquals("login_flow", result.results[0].name)
        assertEquals(1250L, result.results[0].duration_ms)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("crashlytics/traces") == true)
    }

    @Test
    fun testRecordNetworkRequest() {
        val mockRecord = NetworkRequestRecord(
            id = "req_1",
            url = "https://api.example.com/users",
            method = "GET",
            status_code = 200,
            duration_ms = 245,
            request_size = 156,
            response_size = 1024,
            timestamp = "2024-01-01T12:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockRecord))
        )

        val result = crashlyticsService.recordNetworkRequest(
            url = "https://api.example.com/users",
            method = "GET",
            statusCode = 200,
            durationMs = 245,
            requestSize = 156,
            responseSize = 1024
        )

        assertEquals("req_1", result.id)
        assertEquals("https://api.example.com/users", result.url)
        assertEquals(200, result.status_code)
        assertEquals(245L, result.duration_ms)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("crashlytics/network") == true)
    }

    @Test
    fun testGetCrashSummary() {
        val mockSummary = CrashSummary(
            total_crashes = 1500,
            crash_free_users_percentage = 87.5,
            affected_users = 120,
            open_issues = 12
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockSummary))
        )

        val result = crashlyticsService.getCrashSummary()

        assertEquals(1500, result.total_crashes)
        assertEquals(87.5, result.crash_free_users_percentage)
        assertEquals(120, result.affected_users)
        assertEquals(12, result.open_issues)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("crashlytics/summary") == true)
    }
}
