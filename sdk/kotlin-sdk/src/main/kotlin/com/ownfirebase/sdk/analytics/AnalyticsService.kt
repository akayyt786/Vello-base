package com.ownfirebase.sdk.analytics

import com.ownfirebase.sdk.client.OwnFirebaseClient
import com.ownfirebase.sdk.types.*
import java.util.concurrent.BlockingQueue
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import kotlin.concurrent.thread

/**
 * Analytics service for tracking events, user properties, and performing queries.
 * Supports batching and automatic flushing for performance.
 */
class AnalyticsService(config: OwnFirebaseConfig) : OwnFirebaseClient(config) {

    private val eventQueue: BlockingQueue<AnalyticsEventPayload> = LinkedBlockingQueue()
    private var batcherThread: Thread? = null
    private var isRunning = false
    private val batchSize = 100
    private val flushIntervalMs = 30000L // 30 seconds

    // ─── Event Tracking ───────────────────────────────────────────────────────

    /**
     * Log an analytics event.
     *
     * @param name Event name
     * @param params Optional event parameters
     * @param userId Optional user ID
     * @param sessionId Optional session ID
     * @return The recorded event
     */
    fun logEvent(
        name: String,
        params: Map<String, Any?>? = null,
        userId: String? = null,
        sessionId: String? = null
    ): AnalyticsEvent {
        return request(
            "POST",
            projectUrl("analytics/events/"),
            mapOf(
                "name" to name,
                "params" to (params ?: emptyMap()),
                "user_id" to userId,
                "session_id" to sessionId
            ).filterValues { it != null }
        )
    }

    /**
     * Queue an event for batch sending (more efficient than logEvent for high volumes).
     * Events are automatically batched and sent every 30 seconds or when batch reaches 100 events.
     *
     * @param name Event name
     * @param params Optional event parameters
     * @param userId Optional user ID
     * @param sessionId Optional session ID
     */
    fun queueEvent(
        name: String,
        params: Map<String, Any?>? = null,
        userId: String? = null,
        sessionId: String? = null
    ) {
        ensureBatcherRunning()
        eventQueue.offer(AnalyticsEventPayload(name, params, userId, sessionId))
    }

    /**
     * List events with optional filters.
     *
     * @param filters Query filters
     * @return Paginated list of events
     */
    fun listEvents(filters: Map<String, String>? = null): PaginatedResponse<AnalyticsEvent> {
        return request(
            "GET",
            projectUrl("analytics/events/"),
            null,
            RequestOptions(query = filters ?: emptyMap())
        )
    }

    // ─── User Properties ──────────────────────────────────────────────────────

    /**
     * Set a user property.
     *
     * @param name Property name
     * @param value Property value
     * @return The set property
     */
    fun setUserProperty(name: String, value: String): UserProperty {
        return request(
            "POST",
            projectUrl("analytics/user-properties/"),
            mapOf("name" to name, "value" to value)
        )
    }

    /**
     * List all user properties.
     *
     * @return Paginated list of user properties
     */
    fun listUserProperties(): PaginatedResponse<UserProperty> {
        return request(
            "GET",
            projectUrl("analytics/user-properties/")
        )
    }

    // ─── Conversion Events ────────────────────────────────────────────────────

    /**
     * List conversion events.
     *
     * @return Paginated list of conversion events
     */
    fun listConversionEvents(): PaginatedResponse<Map<String, String>> {
        return request(
            "GET",
            projectUrl("analytics/conversion-events/")
        )
    }

    /**
     * Mark an event as a conversion event.
     *
     * @param name Conversion event name
     * @return The created conversion event
     */
    fun markConversionEvent(name: String): Map<String, String> {
        return request(
            "POST",
            projectUrl("analytics/conversion-events/"),
            mapOf("name" to name)
        )
    }

    // ─── Queries ──────────────────────────────────────────────────────────────

    /**
     * Query analytics data.
     * Retrieve aggregated metrics with optional dimensions and filters.
     *
     * @param metric Metric name (e.g., "event_count", "user_count")
     * @param dimension Optional dimension to group by (e.g., "event_name", "country")
     * @param startDate Optional start date (YYYY-MM-DD)
     * @param endDate Optional end date (YYYY-MM-DD)
     * @param filters Optional query filters
     * @return Query results with rows
     */
    fun query(
        metric: String,
        dimension: String? = null,
        startDate: String? = null,
        endDate: String? = null,
        filters: Map<String, String>? = null
    ): AnalyticsQueryResult {
        return request(
            "POST",
            projectUrl("analytics/query/"),
            mapOf(
                "metric" to metric,
                "dimension" to dimension,
                "start_date" to startDate,
                "end_date" to endDate,
                "filters" to filters
            ).filterValues { it != null }
        )
    }

    // ─── Batch Operations ────────────────────────────────────────────────────

    /**
     * Flush all queued events to the server.
     */
    fun flush() {
        val batch = mutableListOf<AnalyticsEventPayload>()
        while (eventQueue.poll() != null) {
            eventQueue.poll()?.let { batch.add(it) }
            if (batch.size >= batchSize) break
        }

        if (batch.isNotEmpty()) {
            sendBatch(batch)
        }
    }

    /**
     * Stop the batch processor and flush remaining events.
     */
    fun stopBatcher() {
        isRunning = false
        flush()
        batcherThread?.join(5000)
        batcherThread = null
    }

    // ─── Internal ────────────────────────────────────────────────────────────

    private fun ensureBatcherRunning() {
        if (isRunning) return
        isRunning = true

        batcherThread = thread(isDaemon = true) {
            var lastFlush = System.currentTimeMillis()

            while (isRunning) {
                val now = System.currentTimeMillis()
                val timeSinceLastFlush = now - lastFlush

                val batch = mutableListOf<AnalyticsEventPayload>()

                // Try to get up to batchSize events with a short timeout
                val timeout = (flushIntervalMs - timeSinceLastFlush).coerceAtLeast(1)
                for (i in 0 until batchSize) {
                    val event = eventQueue.poll(timeout, TimeUnit.MILLISECONDS)
                    if (event != null) {
                        batch.add(event)
                    } else {
                        break
                    }
                }

                if (batch.isNotEmpty() && (batch.size >= batchSize || now - lastFlush >= flushIntervalMs)) {
                    sendBatch(batch)
                    lastFlush = System.currentTimeMillis()
                }

                Thread.sleep(1000) // Check every second
            }
        }
    }

    private fun sendBatch(batch: List<AnalyticsEventPayload>) {
        try {
            val payloads = batch.map {
                mapOf(
                    "name" to it.name,
                    "params" to (it.params ?: emptyMap()),
                    "user_id" to it.userId,
                    "session_id" to it.sessionId
                ).filterValues { v -> v != null }
            }

            request<Unit>(
                "POST",
                projectUrl("analytics/events/batch/"),
                mapOf("events" to payloads)
            )
        } catch (e: Exception) {
            System.err.println("Failed to send analytics batch: ${e.message}")
        }
    }

    data class AnalyticsEventPayload(
        val name: String,
        val params: Map<String, Any?>? = null,
        val userId: String? = null,
        val sessionId: String? = null
    )
}
