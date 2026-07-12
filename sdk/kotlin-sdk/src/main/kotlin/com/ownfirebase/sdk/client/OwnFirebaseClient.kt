package com.ownfirebase.sdk.client

import com.google.gson.Gson
import com.google.gson.JsonElement
import com.google.gson.reflect.TypeToken
import com.ownfirebase.sdk.types.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Base client for OwnFirebase SDK.
 * Handles HTTP requests, JWT token management, and error handling.
 */
open class OwnFirebaseClient(
    protected val config: OwnFirebaseConfig
) {
    protected val baseUrl: String = config.baseUrl.removeSuffix("/")

    @get:JvmName("projectIdKt")
    @set:JvmName("projectIdKt")
    protected var projectId: String? = config.projectId

    @get:JvmName("accessTokenKt")
    @set:JvmName("accessTokenKt")
    protected var accessToken: String? = config.accessToken

    protected val httpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    @PublishedApi
    internal val gson = Gson()

    // ─── Token Management ─────────────────────────────────────────────────────

    fun setAccessToken(token: String) {
        this.accessToken = token
    }

    fun getAccessToken(): String? = accessToken

    fun setProjectId(id: String) {
        this.projectId = id
    }

    fun getProjectId(): String? = projectId

    // ─── URL Builders ─────────────────────────────────────────────────────────

    protected fun projectUrl(path: String): String {
        val id = projectId ?: throw IllegalStateException("projectId is required for this operation")
        return "$baseUrl/api/projects/$id/${path.removePrefix("/")}"
    }

    // ─── HTTP Requests ────────────────────────────────────────────────────────

    /**
     * Makes an HTTP request with automatic retry on network failures.
     * @param method HTTP method (GET, POST, PATCH, PUT, DELETE)
     * @param url Full URL
     * @param body Request body (will be JSON-serialized)
     * @param options Additional options (noAuth, query params)
     * @return Response parsed as T
     */
    protected inline fun <reified T> request(
        method: String,
        url: String,
        body: Any? = null,
        options: RequestOptions = RequestOptions()
    ): T {
        var lastException: Exception? = null
        val maxRetries = 3

        for (attempt in 0 until maxRetries) {
            try {
                val response = makeRequest(method, url, body, options)
                return handleResponse(response)
            } catch (e: Exception) {
                lastException = e
                if (attempt < maxRetries - 1) {
                    if (shouldRetry(e, attempt)) {
                        Thread.sleep((1000L * (attempt + 1))) // Exponential backoff
                    } else {
                        throw e
                    }
                }
            }
        }

        throw lastException ?: Exception("Request failed after $maxRetries attempts")
    }

    @PublishedApi
    internal fun makeRequest(
        method: String,
        url: String,
        body: Any?,
        options: RequestOptions
    ): Response {
        var fullUrl = url
        if (options.query.isNotEmpty()) {
            val params = options.query.entries.joinToString("&") { (k, v) ->
                "${urlEncode(k)}=${urlEncode(v)}"
            }
            fullUrl += "?$params"
        }

        val requestBuilder = Request.Builder().url(fullUrl)
        val jsonMediaType = "application/json".toMediaType()

        when {
            method.equals("GET", ignoreCase = true) -> requestBuilder.get()
            method.equals("POST", ignoreCase = true) -> {
                val jsonBody = (if (body != null) gson.toJson(body) else "{}").toRequestBody(jsonMediaType)
                requestBuilder.post(jsonBody)
            }
            method.equals("PATCH", ignoreCase = true) -> {
                val jsonBody = (if (body != null) gson.toJson(body) else "{}").toRequestBody(jsonMediaType)
                requestBuilder.patch(jsonBody)
            }
            method.equals("PUT", ignoreCase = true) -> {
                val jsonBody = (if (body != null) gson.toJson(body) else "{}").toRequestBody(jsonMediaType)
                requestBuilder.put(jsonBody)
            }
            method.equals("DELETE", ignoreCase = true) -> requestBuilder.delete()
        }

        // Add headers
        requestBuilder.addHeader("Content-Type", "application/json")

        if (!options.noAuth && accessToken != null) {
            requestBuilder.addHeader("Authorization", "Bearer $accessToken")
        }

        val request = requestBuilder.build()
        return httpClient.newCall(request).execute()
    }

    @PublishedApi
    internal inline fun <reified T> handleResponse(response: Response): T {
        if (!response.isSuccessful) {
            val body = response.body?.string() ?: ""
            val detail = try {
                gson.fromJson<JsonElement>(body, JsonElement::class.java)
            } catch (e: Exception) {
                body
            }
            throw APIError(
                status = response.code,
                message = response.message,
                detail = detail
            )
        }

        return when (response.code) {
            204 -> Unit as T // No content
            else -> {
                val body = response.body?.string() ?: return Unit as T
                // Use TypeToken instead of T::class.java so nested generic types
                // (e.g. PaginatedResponse<X>, List<X>) deserialize their type
                // parameter correctly instead of erasing elements to LinkedTreeMap.
                gson.fromJson(body, object : TypeToken<T>() {}.type)
            }
        }
    }

    @PublishedApi
    internal fun shouldRetry(e: Exception, attempt: Int): Boolean {
        return when (e) {
            is IOException -> attempt < 2 // Retry network errors max 2 times
            is APIError -> {
                // Retry on 5xx errors and 429 (rate limit)
                e.status >= 500 || e.status == 429
            }
            else -> false
        }
    }

    private fun urlEncode(value: String): String {
        return java.net.URLEncoder.encode(value, "UTF-8")
    }

    data class RequestOptions(
        val noAuth: Boolean = false,
        val query: Map<String, String> = emptyMap()
    )

    // ─── Utility ──────────────────────────────────────────────────────────────

    protected fun close() {
        httpClient.connectionPool.evictAll()
        httpClient.dispatcher.executorService.shutdown()
    }
}
