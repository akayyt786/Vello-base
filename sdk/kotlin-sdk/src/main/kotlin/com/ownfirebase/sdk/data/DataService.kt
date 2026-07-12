package com.ownfirebase.sdk.data

import com.ownfirebase.sdk.client.OwnFirebaseClient
import com.ownfirebase.sdk.types.*

/**
 * Data service for CRUD operations on collections and documents.
 * Supports collections, subcollections, queries, and batch operations.
 */
class DataService(config: OwnFirebaseConfig) : OwnFirebaseClient(config) {

    // ─── Collections ──────────────────────────────────────────────────────────

    /**
     * List all collections in the project.
     */
    fun listCollections(): List<DataCollection> {
        return request(
            "GET",
            projectUrl("collections/")
        )
    }

    /**
     * Create a new collection.
     */
    fun createCollection(name: String): DataCollection {
        return request(
            "POST",
            projectUrl("collections/"),
            mapOf("name" to name)
        )
    }

    // ─── Documents ────────────────────────────────────────────────────────────

    /**
     * List documents in a collection.
     * Collection supports subcollection paths using forward slashes (e.g., "users/uid/posts").
     *
     * @param collection Collection name or path
     * @param filters Optional query filters
     * @return Paginated response with documents
     */
    fun listDocuments(
        collection: String,
        filters: Map<String, String>? = null
    ): PaginatedResponse<DataDocument> {
        return request(
            "GET",
            projectUrl("collections/$collection/docs/"),
            null,
            RequestOptions(query = filters ?: emptyMap())
        )
    }

    /**
     * Get a single document.
     *
     * @param collection Collection name or path
     * @param docId Document ID
     * @return The document
     */
    fun getDocument(collection: String, docId: String): DataDocument {
        return request(
            "GET",
            projectUrl("collections/$collection/docs/$docId/")
        )
    }

    /**
     * Create a new document in a collection.
     *
     * @param collection Collection name or path
     * @param data Document data
     * @return The created document
     */
    fun createDocument(
        collection: String,
        data: Map<String, Any?>
    ): DataDocument {
        return request(
            "POST",
            projectUrl("collections/$collection/docs/"),
            mapOf("data" to data)
        )
    }

    /**
     * Update specific fields in a document (PATCH - partial update).
     *
     * @param collection Collection name or path
     * @param docId Document ID
     * @param data Fields to update
     * @return The updated document
     */
    fun updateDocument(
        collection: String,
        docId: String,
        data: Map<String, Any?>
    ): DataDocument {
        return request(
            "PATCH",
            projectUrl("collections/$collection/docs/$docId/"),
            mapOf("data" to data)
        )
    }

    /**
     * Replace an entire document (PUT - full replace).
     *
     * @param collection Collection name or path
     * @param docId Document ID
     * @param data Full document data
     * @return The replaced document
     */
    fun replaceDocument(
        collection: String,
        docId: String,
        data: Map<String, Any?>
    ): DataDocument {
        return request(
            "PUT",
            projectUrl("collections/$collection/docs/$docId/"),
            mapOf("data" to data)
        )
    }

    /**
     * Delete a document.
     *
     * @param collection Collection name or path
     * @param docId Document ID
     */
    fun deleteDocument(collection: String, docId: String) {
        request<Unit>(
            "DELETE",
            projectUrl("collections/$collection/docs/$docId/")
        )
    }

    // ─── Batch / Transactions ────────────────────────────────────────────────

    /**
     * Execute multiple write operations in a batch/transaction.
     * All operations succeed or all fail together.
     *
     * @param operations List of batch operations
     * @return Result with number written and errors
     */
    fun writeBatch(operations: List<WriteBatchOperation>): WriteBatchResult {
        return request(
            "POST",
            projectUrl("transaction/"),
            mapOf("operations" to operations)
        )
    }

    // ─── Security Rules ──────────────────────────────────────────────────────

    /**
     * Get current security rules.
     */
    fun getRules(): Map<String, String> {
        return request(
            "GET",
            "$baseUrl/api/v1/rules/"
        )
    }

    /**
     * Update security rules.
     *
     * @param rules New security rules as string
     * @return Updated rules
     */
    fun updateRules(rules: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/rules/",
            mapOf("rules" to rules)
        )
    }

    /**
     * Test a security rule against a context.
     *
     * @param rule The rule to test
     * @param context Context to evaluate against
     * @return Whether the rule allows access and optional reason
     */
    fun testRules(
        rule: String,
        context: Map<String, Any?>
    ): Map<String, Any?> {
        return request(
            "POST",
            "$baseUrl/api/v1/rules/test/",
            mapOf(
                "rule" to rule,
                "context" to context
            )
        )
    }

    // ─── Helper for batch operations ──────────────────────────────────────────

    /**
     * Builder for batch operations - convenience method.
     */
    class BatchBuilder {
        private val operations = mutableListOf<WriteBatchOperation>()

        fun set(collection: String, docId: String, data: Map<String, Any?>): BatchBuilder {
            operations.add(WriteBatchOperation(
                op = "set",
                collection = collection,
                doc_id = docId,
                data = data
            ))
            return this
        }

        fun update(collection: String, docId: String, data: Map<String, Any?>): BatchBuilder {
            operations.add(WriteBatchOperation(
                op = "update",
                collection = collection,
                doc_id = docId,
                data = data
            ))
            return this
        }

        fun delete(collection: String, docId: String): BatchBuilder {
            operations.add(WriteBatchOperation(
                op = "delete",
                collection = collection,
                doc_id = docId
            ))
            return this
        }

        fun build(): List<WriteBatchOperation> = operations
    }
}
