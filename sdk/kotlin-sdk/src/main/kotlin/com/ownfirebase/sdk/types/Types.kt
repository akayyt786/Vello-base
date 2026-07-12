package com.ownfirebase.sdk.types

// ─── Configuration ───────────────────────────────────────────────────────────
data class OwnFirebaseConfig(
    val baseUrl: String,
    val projectId: String? = null,
    val accessToken: String? = null
)

// ─── Auth ────────────────────────────────────────────────────────────────────
data class AuthTokens(
    val access: String,
    val refresh: String,
    val user_id: String,
    val email: String? = null
)

data class User(
    val id: String,
    val email: String,
    val username: String,
    val first_name: String,
    val last_name: String,
    val is_active: Boolean
)

data class MFADevice(
    val id: String,
    val type: String, // "totp" or "sms"
    val name: String,
    val confirmed: Boolean,
    val created_at: String
)

data class LinkedSocialAccount(
    val id: String,
    val provider: String,
    val provider_uid: String,
    val email: String? = null,
    val linked_at: String
)

data class CustomToken(
    val custom_token: String
)

// ─── Data ────────────────────────────────────────────────────────────────────
data class DataDocument(
    val id: String,
    val collection: String,
    val data: Map<String, Any?>,
    val created_at: String,
    val updated_at: String
)

data class DataCollection(
    val id: String,
    val name: String,
    val document_count: Int
)

data class WriteBatchOperation(
    val op: String, // "set", "update", or "delete"
    val collection: String,
    val doc_id: String? = null,
    val data: Map<String, Any?>? = null
)

data class WriteBatchResult(
    val written: Int,
    val errors: List<Any> = emptyList()
)

data class PaginatedResponse<T>(
    val count: Int,
    val next: String? = null,
    val previous: String? = null,
    val results: List<T>
)

// ─── Storage ─────────────────────────────────────────────────────────────────
data class StorageObject(
    val id: String,
    val name: String,
    val size: Long,
    val content_type: String,
    val url: String,
    val created_at: String
)

data class StorageUploadUrl(
    val file_id: String,
    val upload_url: String,
    val method: String,
    val expires_in: Int,
    val path: String,
    val bucket: String
)

// ─── Analytics ───────────────────────────────────────────────────────────────
data class AnalyticsEvent(
    val id: String,
    val name: String,
    val params: Map<String, Any?>,
    val timestamp: String,
    val user_id: String? = null,
    val session_id: String? = null
)

data class UserProperty(
    val id: String,
    val name: String,
    val value: String,
    val user_id: String
)

data class AnalyticsQueryParams(
    val metric: String,
    val dimension: String? = null,
    val start_date: String? = null,
    val end_date: String? = null,
    val filters: Map<String, String>? = null
)

data class AnalyticsQueryResult(
    val metric: String,
    val dimension: String? = null,
    val rows: List<AnalyticsRow>
)

data class AnalyticsRow(
    val dimension_value: String? = null,
    val metric_value: Double,
    val date: String? = null
)

// ─── Crashlytics ─────────────────────────────────────────────────────────────
data class CrashReport(
    val id: String,
    val exception_type: String,
    val message: String,
    val stack_trace: String,
    val occurred_at: String,
    val app_version: String,
    val platform: String
)

data class CrashGroup(
    val id: String,
    val exception_type: String,
    val message_summary: String,
    val occurrence_count: Int,
    val affected_users: Int,
    val first_seen: String,
    val last_seen: String,
    val status: String // "open", "resolved", "ignored"
)

data class PerformanceTrace(
    val id: String,
    val name: String,
    val duration_ms: Long,
    val started_at: String,
    val attributes: Map<String, String>? = null,
    val metrics: Map<String, Double>? = null
)

data class NetworkRequestRecord(
    val id: String,
    val url: String,
    val method: String,
    val status_code: Int,
    val duration_ms: Long,
    val request_size: Long? = null,
    val response_size: Long? = null,
    val timestamp: String
)

data class CrashSummary(
    val total_crashes: Int,
    val crash_free_users_percentage: Double,
    val affected_users: Int,
    val open_issues: Int
)

// ─── Remote Config ───────────────────────────────────────────────────────────
data class RemoteConfigParameter(
    val id: String,
    val key: String,
    val default_value: String,
    val description: String,
    val value_type: String // "string", "boolean", "number", "json"
)

data class ConfigCondition(
    val id: String,
    val name: String,
    val expression: String,
    val value: String
)

// ─── Error Handling ──────────────────────────────────────────────────────────
data class APIError(
    val status: Int,
    override val message: String,
    val detail: Any? = null
) : Exception("HTTP $status: $message")

class NetworkException(message: String, cause: Throwable? = null) : Exception(message, cause)

class ValidationException(message: String) : Exception(message)

class TokenExpiredException(message: String = "Access token expired") : Exception(message)
