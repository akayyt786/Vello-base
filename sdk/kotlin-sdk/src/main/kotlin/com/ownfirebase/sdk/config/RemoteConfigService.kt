package com.ownfirebase.sdk.config

import com.ownfirebase.sdk.client.OwnFirebaseClient
import com.ownfirebase.sdk.types.*
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

/**
 * Remote Config service for managing feature flags and configuration parameters.
 * Supports caching, periodic refresh, and dynamic value updates.
 */
class RemoteConfigService(config: OwnFirebaseConfig) : OwnFirebaseClient(config) {

    private val cache = ConcurrentHashMap<String, CachedValue>()
    private val cacheTtlMs = TimeUnit.HOURS.toMillis(1) // 1 hour default TTL

    data class CachedValue(
        val value: RemoteConfigParameter,
        val cachedAt: Long = System.currentTimeMillis()
    ) {
        fun isExpired(ttlMs: Long = 3600000): Boolean {
            return System.currentTimeMillis() - cachedAt > ttlMs
        }
    }

    // ─── Parameters ───────────────────────────────────────────────────────────

    /**
     * List all remote config parameters.
     *
     * @return Paginated list of parameters
     */
    fun listParameters(): PaginatedResponse<RemoteConfigParameter> {
        return request(
            "GET",
            projectUrl("config/parameters/")
        )
    }

    /**
     * Get a specific parameter with optional caching.
     *
     * @param id Parameter ID
     * @param useCache Whether to use cache (default true)
     * @return Parameter details
     */
    fun getParameter(id: String, useCache: Boolean = true): RemoteConfigParameter {
        if (useCache) {
            cache[id]?.let {
                if (!it.isExpired(cacheTtlMs)) {
                    return it.value
                } else {
                    cache.remove(id)
                }
            }
        }

        val parameter = request<RemoteConfigParameter>(
            "GET",
            projectUrl("config/parameters/$id/")
        )

        if (useCache) {
            cache[id] = CachedValue(parameter)
        }

        return parameter
    }

    /**
     * Create a new config parameter.
     *
     * @param key Parameter key
     * @param defaultValue Default value
     * @param description Description
     * @param valueType Value type (string, boolean, number, json)
     * @return Created parameter
     */
    fun createParameter(
        key: String,
        defaultValue: String,
        description: String = "",
        valueType: String = "string"
    ): RemoteConfigParameter {
        val parameter = RemoteConfigParameter(
            id = "", // Will be assigned by server
            key = key,
            default_value = defaultValue,
            description = description,
            value_type = valueType
        )

        return request(
            "POST",
            projectUrl("config/parameters/"),
            parameter
        )
    }

    /**
     * Update an existing parameter.
     *
     * @param id Parameter ID
     * @param key New key (optional)
     * @param defaultValue New default value (optional)
     * @param description New description (optional)
     * @param valueType New value type (optional)
     * @return Updated parameter
     */
    fun updateParameter(
        id: String,
        key: String? = null,
        defaultValue: String? = null,
        description: String? = null,
        valueType: String? = null
    ): RemoteConfigParameter {
        val updates = mapOf(
            "key" to key,
            "default_value" to defaultValue,
            "description" to description,
            "value_type" to valueType
        ).filterValues { it != null }

        val parameter = request<RemoteConfigParameter>(
            "PATCH",
            projectUrl("config/parameters/$id/"),
            updates
        )

        // Invalidate cache
        cache.remove(id)

        return parameter
    }

    /**
     * Delete a parameter.
     *
     * @param id Parameter ID
     */
    fun deleteParameter(id: String) {
        request<Unit>(
            "DELETE",
            projectUrl("config/parameters/$id/")
        )
        cache.remove(id)
    }

    // ─── Conditions ───────────────────────────────────────────────────────────

    /**
     * List conditions for a parameter.
     *
     * @param configId Parameter ID
     * @return List of conditions
     */
    fun listConditions(configId: String): List<ConfigCondition> {
        return request(
            "GET",
            projectUrl("config/parameters/$configId/conditions/")
        )
    }

    /**
     * Create a condition for a parameter.
     * Conditions determine when different values apply (e.g., based on user, app version, etc.).
     *
     * @param configId Parameter ID
     * @param name Condition name
     * @param expression Condition expression
     * @param value Value to use when condition is true
     * @return Created condition
     */
    fun createCondition(
        configId: String,
        name: String,
        expression: String,
        value: String
    ): ConfigCondition {
        return request(
            "POST",
            projectUrl("config/parameters/$configId/conditions/"),
            mapOf(
                "name" to name,
                "expression" to expression,
                "value" to value
            )
        )
    }

    /**
     * Update a condition.
     *
     * @param configId Parameter ID
     * @param conditionId Condition ID
     * @param name New name (optional)
     * @param expression New expression (optional)
     * @param value New value (optional)
     * @return Updated condition
     */
    fun updateCondition(
        configId: String,
        conditionId: String,
        name: String? = null,
        expression: String? = null,
        value: String? = null
    ): ConfigCondition {
        val updates = mapOf(
            "name" to name,
            "expression" to expression,
            "value" to value
        ).filterValues { it != null }

        val condition = request<ConfigCondition>(
            "PATCH",
            projectUrl("config/parameters/$configId/conditions/$conditionId/"),
            updates
        )

        // Invalidate cache
        cache.remove(configId)

        return condition
    }

    /**
     * Delete a condition.
     *
     * @param configId Parameter ID
     * @param conditionId Condition ID
     */
    fun deleteCondition(configId: String, conditionId: String) {
        request<Unit>(
            "DELETE",
            projectUrl("config/parameters/$configId/conditions/$conditionId/")
        )
        cache.remove(configId)
    }

    // ─── Caching & Refresh ────────────────────────────────────────────────────

    /**
     * Force refresh the cache by fetching all parameters.
     */
    fun refreshCache() {
        try {
            val params = listParameters()
            cache.clear()
            params.results.forEach { param ->
                cache[param.id] = CachedValue(param)
            }
        } catch (e: Exception) {
            System.err.println("Failed to refresh remote config cache: ${e.message}")
        }
    }

    /**
     * Clear the local cache.
     */
    fun clearCache() {
        cache.clear()
    }

    /**
     * Get a parameter value with type conversion.
     * Returns default value if parameter not found.
     *
     * @param key Parameter key
     * @param defaultValue Default value to return if not found
     * @return Parameter value or default
     */
    fun getString(key: String, defaultValue: String = ""): String {
        return try {
            val params = listParameters()
            params.results.find { it.key == key }?.default_value ?: defaultValue
        } catch (e: Exception) {
            defaultValue
        }
    }

    /**
     * Get a boolean parameter value.
     *
     * @param key Parameter key
     * @param defaultValue Default value
     * @return Boolean value
     */
    fun getBoolean(key: String, defaultValue: Boolean = false): Boolean {
        return try {
            val value = getString(key, defaultValue.toString())
            value.equals("true", ignoreCase = true)
        } catch (e: Exception) {
            defaultValue
        }
    }

    /**
     * Get a numeric parameter value.
     *
     * @param key Parameter key
     * @param defaultValue Default value
     * @return Number value
     */
    fun getNumber(key: String, defaultValue: Double = 0.0): Double {
        return try {
            getString(key, defaultValue.toString()).toDoubleOrNull() ?: defaultValue
        } catch (e: Exception) {
            defaultValue
        }
    }

    /**
     * Get a JSON parameter value.
     *
     * @param key Parameter key
     * @param defaultValue Default value
     * @return JSON string
     */
    fun getJson(key: String, defaultValue: String = "{}"): String {
        return try {
            getString(key, defaultValue)
        } catch (e: Exception) {
            defaultValue
        }
    }
}
