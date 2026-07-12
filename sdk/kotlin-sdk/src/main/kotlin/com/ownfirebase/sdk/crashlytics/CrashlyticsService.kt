package com.ownfirebase.sdk.crashlytics

import com.ownfirebase.sdk.client.OwnFirebaseClient
import com.ownfirebase.sdk.types.*
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.*

/**
 * Crashlytics service for crash reporting, performance monitoring, and diagnostics.
 * Automatically captures crash information, performance traces, and network requests.
 */
class CrashlyticsService(config: OwnFirebaseConfig) : OwnFirebaseClient(config) {

    private val appVersion: String = "1.0.0" // Should be set by the app
    private val platform: String = System.getProperty("os.name") ?: "unknown"

    // ─── Crash Groups ────────────────────────────────────────────────────────

    /**
     * List crash groups with optional filters.
     *
     * @param filters Query filters (e.g., status, app_version)
     * @return Paginated list of crash groups
     */
    fun listCrashGroups(filters: Map<String, String>? = null): PaginatedResponse<CrashGroup> {
        return request(
            "GET",
            projectUrl("crashlytics/groups/"),
            null,
            RequestOptions(query = filters ?: emptyMap())
        )
    }

    /**
     * Get details of a specific crash group.
     *
     * @param id Crash group ID
     * @return Crash group details
     */
    fun getCrashGroup(id: String): CrashGroup {
        return request(
            "GET",
            projectUrl("crashlytics/groups/$id/")
        )
    }

    // ─── Crash Reports ───────────────────────────────────────────────────────

    /**
     * Report a crash.
     *
     * @param exceptionType Type of exception (e.g., "NullPointerException")
     * @param message Error message
     * @param stackTrace Stack trace string
     * @param appVersion App version (optional, uses default if not provided)
     * @param deviceInfo Optional device information
     * @return The recorded crash report
     */
    fun reportCrash(
        exceptionType: String,
        message: String,
        stackTrace: String,
        appVersion: String? = null,
        deviceInfo: Map<String, Any?>? = null
    ): CrashReport {
        return request(
            "POST",
            projectUrl("crashlytics/reports/"),
            mapOf(
                "exception_type" to exceptionType,
                "message" to message,
                "stack_trace" to stackTrace,
                "app_version" to (appVersion ?: this.appVersion),
                "platform" to platform,
                "device_info" to deviceInfo
            ).filterValues { it != null }
        )
    }

    /**
     * Report an exception - convenience method.
     * Automatically extracts exception type, message, and stack trace.
     *
     * @param exception The exception to report
     * @param appVersion Optional app version
     * @param deviceInfo Optional device info
     * @return The recorded crash report
     */
    fun reportException(
        exception: Throwable,
        appVersion: String? = null,
        deviceInfo: Map<String, Any?>? = null
    ): CrashReport {
        return reportCrash(
            exceptionType = exception::class.simpleName ?: "Exception",
            message = exception.message ?: "No message",
            stackTrace = getStackTrace(exception),
            appVersion = appVersion,
            deviceInfo = deviceInfo
        )
    }

    /**
     * List crash reports with optional filters.
     *
     * @param filters Query filters (e.g., status, platform)
     * @return Paginated list of crash reports
     */
    fun listCrashReports(filters: Map<String, String>? = null): PaginatedResponse<CrashReport> {
        return request(
            "GET",
            projectUrl("crashlytics/reports/"),
            null,
            RequestOptions(query = filters ?: emptyMap())
        )
    }

    /**
     * Get crash summary statistics.
     *
     * @return Summary of crashes
     */
    fun getCrashSummary(): CrashSummary {
        return request(
            "GET",
            projectUrl("crashlytics/summary/")
        )
    }

    // ─── Performance Traces ───────────────────────────────────────────────────

    /**
     * Record a performance trace.
     *
     * @param name Trace name (e.g., "api_call", "image_load")
     * @param durationMs Duration in milliseconds
     * @param startedAt ISO 8601 timestamp
     * @param attributes Optional string attributes
     * @param metrics Optional numeric metrics (e.g., bytes_downloaded, cpu_usage)
     * @return The recorded trace
     */
    fun recordTrace(
        name: String,
        durationMs: Long,
        startedAt: String = getCurrentTimestamp(),
        attributes: Map<String, String>? = null,
        metrics: Map<String, Double>? = null
    ): PerformanceTrace {
        return request(
            "POST",
            projectUrl("crashlytics/traces/"),
            mapOf(
                "name" to name,
                "duration_ms" to durationMs,
                "started_at" to startedAt,
                "attributes" to attributes,
                "metrics" to metrics
            ).filterValues { it != null }
        )
    }

    /**
     * Measure execution time of a block and record as trace.
     * Convenience method for performance monitoring.
     *
     * @param name Trace name
     * @param attributes Optional attributes
     * @param block Code block to measure
     * @return Trace result with the return value from block
     */
    fun <T> trace(
        name: String,
        attributes: Map<String, String>? = null,
        block: () -> T
    ): T {
        val startTime = System.currentTimeMillis()
        return try {
            block()
        } finally {
            val duration = System.currentTimeMillis() - startTime
            try {
                recordTrace(name, duration, attributes = attributes)
            } catch (e: Exception) {
                // Telemetry recording must never crash the traced operation.
            }
        }
    }

    /**
     * List performance traces with optional filters.
     *
     * @param filters Query filters
     * @return Paginated list of traces
     */
    fun listTraces(filters: Map<String, String>? = null): PaginatedResponse<PerformanceTrace> {
        return request(
            "GET",
            projectUrl("crashlytics/traces/"),
            null,
            RequestOptions(query = filters ?: emptyMap())
        )
    }

    // ─── Network Requests ────────────────────────────────────────────────────

    /**
     * Record a network request for diagnostics.
     *
     * @param url Request URL
     * @param method HTTP method (GET, POST, etc.)
     * @param statusCode HTTP response status code
     * @param durationMs Request duration in milliseconds
     * @param requestSize Optional request size in bytes
     * @param responseSize Optional response size in bytes
     * @return The recorded network request
     */
    fun recordNetworkRequest(
        url: String,
        method: String,
        statusCode: Int,
        durationMs: Long,
        requestSize: Long? = null,
        responseSize: Long? = null
    ): NetworkRequestRecord {
        return request(
            "POST",
            projectUrl("crashlytics/network/"),
            mapOf(
                "url" to url,
                "method" to method,
                "status_code" to statusCode,
                "duration_ms" to durationMs,
                "request_size" to requestSize,
                "response_size" to responseSize
            ).filterValues { it != null }
        )
    }

    /**
     * List recorded network requests with optional filters.
     *
     * @param filters Query filters
     * @return Paginated list of network requests
     */
    fun listNetworkRequests(filters: Map<String, String>? = null): PaginatedResponse<NetworkRequestRecord> {
        return request(
            "GET",
            projectUrl("crashlytics/network/"),
            null,
            RequestOptions(query = filters ?: emptyMap())
        )
    }

    // ─── Utility Methods ──────────────────────────────────────────────────────

    /**
     * Set the app version for future crash reports.
     *
     * @param version Version string (e.g., "1.2.3")
     */
    fun setAppVersion(version: String) {
        // This would normally update the property, but for the base implementation
        // we just ignore it. Subclasses can override to store this.
    }

    /**
     * Get stack trace as a string.
     */
    private fun getStackTrace(throwable: Throwable): String {
        val stringWriter = StringWriter()
        val printWriter = PrintWriter(stringWriter)
        throwable.printStackTrace(printWriter)
        return stringWriter.toString()
    }

    /**
     * Get current timestamp in ISO 8601 format.
     */
    private fun getCurrentTimestamp(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        return sdf.format(Date())
    }
}
