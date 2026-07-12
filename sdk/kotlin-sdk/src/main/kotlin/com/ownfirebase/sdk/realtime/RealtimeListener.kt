package com.ownfirebase.sdk.realtime

import com.google.gson.Gson
import com.google.gson.JsonElement
import com.ownfirebase.sdk.types.APIError
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.TimeUnit

/**
 * Real-time listener using WebSocket for live updates on collections and documents.
 * Supports subscribing to collection changes, document updates, and realtime queries.
 */
class RealtimeListener(
    private val baseUrl: String,
    private val projectId: String?,
    private val accessToken: String?
) {

    private val httpClient = OkHttpClient.Builder()
        .pingInterval(30, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val listeners = CopyOnWriteArrayList<RealtimeEventListener>()
    private val gson = Gson()
    private var messageId = 0

    interface RealtimeEventListener {
        fun onEvent(event: RealtimeEvent)
        fun onError(error: Throwable)
        fun onConnected()
        fun onDisconnected()
    }

    data class RealtimeEvent(
        val type: String, // "update", "delete", "create", "change"
        val collection: String,
        val docId: String? = null,
        val data: Map<String, Any?>? = null,
        val timestamp: Long = System.currentTimeMillis()
    )

    /**
     * Connect to the WebSocket endpoint for real-time updates.
     *
     * @param listener Event listener
     */
    fun connect(listener: RealtimeEventListener) {
        listeners.add(listener)
        if (webSocket != null) {
            listener.onConnected()
            return
        }

        val url = buildWebSocketUrl()
        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer ${accessToken ?: ""}")
            .build()

        webSocket = httpClient.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
                listeners.forEach { it.onConnected() }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                handleMessage(bytes.utf8())
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                listeners.forEach { it.onDisconnected() }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
                listeners.forEach { it.onError(t) }
            }
        })
    }

    /**
     * Subscribe to changes on a collection.
     *
     * @param collection Collection name or path
     * @param docId Optional specific document ID to watch
     */
    fun subscribe(collection: String, docId: String? = null) {
        val message = mapOf(
            "type" to "subscribe",
            "id" to (++messageId),
            "collection" to collection,
            "docId" to docId
        ).filterValues { it != null }

        sendMessage(message)
    }

    /**
     * Unsubscribe from a collection.
     *
     * @param collection Collection name
     */
    fun unsubscribe(collection: String) {
        val message = mapOf(
            "type" to "unsubscribe",
            "id" to (++messageId),
            "collection" to collection
        )

        sendMessage(message)
    }

    /**
     * Disconnect from the WebSocket.
     */
    fun disconnect() {
        webSocket?.close(1000, "Client disconnecting")
        webSocket = null
    }

    /**
     * Add a listener for real-time events.
     *
     * @param listener Event listener to add
     */
    fun addListener(listener: RealtimeEventListener) {
        listeners.add(listener)
        connect(listener)
    }

    /**
     * Remove a listener.
     *
     * @param listener Listener to remove
     */
    fun removeListener(listener: RealtimeEventListener) {
        listeners.remove(listener)
        if (listeners.isEmpty()) {
            disconnect()
        }
    }

    // ─── Internal ─────────────────────────────────────────────────────────────

    private fun buildWebSocketUrl(): String {
        val cleanUrl = baseUrl.removeSuffix("/").removePrefix("http://").removePrefix("https://")
        val wsUrl = if (baseUrl.contains("https")) "wss://" else "ws://"
        val pid = projectId ?: throw IllegalStateException("projectId required for realtime")
        return "$wsUrl$cleanUrl/ws/v1/projects/$pid/listen/"
    }

    private fun sendMessage(message: Map<String, Any?>) {
        val json = gson.toJson(message)
        webSocket?.send(json)
    }

    private fun handleMessage(text: String) {
        try {
            val json = gson.fromJson(text, JsonElement::class.java)
            val obj = json.asJsonObject

            val type = obj.get("type")?.asString ?: return
            val collection = obj.get("collection")?.asString ?: return
            val docId = obj.get("docId")?.asString

            val dataElement = obj.get("data")
            val data = if (dataElement != null && dataElement.isJsonObject) {
                gson.fromJson(dataElement, Map::class.java) as? Map<String, Any?>
            } else {
                null
            }

            val event = RealtimeEvent(
                type = type,
                collection = collection,
                docId = docId,
                data = data
            )

            listeners.forEach { it.onEvent(event) }
        } catch (e: Exception) {
            listeners.forEach { it.onError(e) }
        }
    }
}

/**
 * Convenience class for real-time document listener.
 */
class RealtimeDocumentListener(
    private val onUpdate: (data: Map<String, Any?>?) -> Unit = {},
    private val onDelete: () -> Unit = {},
    private val onError: (error: Throwable) -> Unit = {}
) : RealtimeListener.RealtimeEventListener {

    override fun onEvent(event: RealtimeListener.RealtimeEvent) {
        when (event.type) {
            "update", "create", "change" -> onUpdate(event.data)
            "delete" -> onDelete()
        }
    }

    override fun onError(error: Throwable) {
        this.onError.invoke(error)
    }

    override fun onConnected() {}
    override fun onDisconnected() {}
}

/**
 * Convenience class for real-time collection listener.
 */
class RealtimeCollectionListener(
    private val onAdd: (docId: String, data: Map<String, Any?>?) -> Unit = { _, _ -> },
    private val onModify: (docId: String, data: Map<String, Any?>?) -> Unit = { _, _ -> },
    private val onRemove: (docId: String) -> Unit = {},
    private val onError: (error: Throwable) -> Unit = {}
) : RealtimeListener.RealtimeEventListener {

    override fun onEvent(event: RealtimeListener.RealtimeEvent) {
        val docId = event.docId ?: return
        when (event.type) {
            "create" -> onAdd(docId, event.data)
            "update", "change" -> onModify(docId, event.data)
            "delete" -> onRemove(docId)
        }
    }

    override fun onError(error: Throwable) {
        this.onError.invoke(error)
    }

    override fun onConnected() {}
    override fun onDisconnected() {}
}
