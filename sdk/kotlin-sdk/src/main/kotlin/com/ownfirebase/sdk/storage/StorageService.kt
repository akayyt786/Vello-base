package com.ownfirebase.sdk.storage

import com.ownfirebase.sdk.client.OwnFirebaseClient
import com.ownfirebase.sdk.types.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.File
import java.io.InputStream

/**
 * Storage service for file upload/download with presigned URLs.
 * Supports direct browser/client uploads via MinIO/S3.
 */
class StorageService(config: OwnFirebaseConfig) : OwnFirebaseClient(config) {

    /**
     * Request a presigned upload URL from MinIO/S3 for direct client upload.
     *
     * @param filename The filename for the upload
     * @param contentType MIME type (e.g., "image/png")
     * @param path Optional path prefix (e.g., "avatars/", "documents/")
     * @return Upload URL and object key
     */
    fun getUploadUrl(
        filename: String,
        contentType: String,
        path: String? = null
    ): StorageUploadUrl {
        return request(
            "POST",
            projectUrl("storage/upload-url/"),
            mapOf(
                "filename" to filename,
                "content_type" to contentType,
                "path" to path
            ).filterValues { it != null }
        )
    }

    /**
     * Confirm a direct upload after the client has PUT to the presigned URL.
     *
     * @param objectKey The object key returned from getUploadUrl
     * @return The created storage object
     */
    fun confirmUpload(objectKey: String): StorageObject {
        return request(
            "POST",
            projectUrl("storage/confirm/"),
            mapOf("object_key" to objectKey)
        )
    }

    /**
     * List files in storage with optional prefix filter.
     *
     * @param prefix Optional path prefix to filter results
     * @return Paginated list of storage objects
     */
    fun listFiles(prefix: String? = null): PaginatedResponse<StorageObject> {
        val query = if (prefix != null) mapOf("prefix" to prefix) else emptyMap()
        return request(
            "GET",
            projectUrl("storage/files/"),
            null,
            RequestOptions(query = query)
        )
    }

    /**
     * Get a specific file's metadata.
     *
     * @param path File path
     * @return Storage object metadata
     */
    fun getFile(path: String): StorageObject {
        return request(
            "GET",
            projectUrl("storage/files/$path/")
        )
    }

    /**
     * Delete a file from storage.
     *
     * @param path File path
     */
    fun deleteFile(path: String) {
        request<Unit>(
            "DELETE",
            projectUrl("storage/files/$path/")
        )
    }

    /**
     * Upload a file directly (high-level helper).
     * This method:
     * 1. Requests an upload URL
     * 2. PUTs the file to the presigned URL
     * 3. Confirms the upload
     *
     * @param file File bytes to upload
     * @param filename Name for the file
     * @param contentType MIME type
     * @param path Optional path prefix
     * @return The created storage object
     */
    fun upload(
        file: ByteArray,
        filename: String,
        contentType: String,
        path: String? = null
    ): StorageObject {
        val uploadUrl = getUploadUrl(filename, contentType, path)
        uploadToPresignedUrl(uploadUrl.upload_url, file, contentType)
        return confirmUpload(uploadUrl.object_key)
    }

    /**
     * Upload a file from an input stream (high-level helper).
     *
     * @param inputStream Input stream to read from
     * @param filename Name for the file
     * @param contentType MIME type
     * @param path Optional path prefix
     * @return The created storage object
     */
    fun uploadFromStream(
        inputStream: InputStream,
        filename: String,
        contentType: String,
        path: String? = null
    ): StorageObject {
        val file = inputStream.readBytes()
        return upload(file, filename, contentType, path)
    }

    /**
     * Upload a file from disk (high-level helper).
     *
     * @param file File to upload
     * @param filename Name for the file (defaults to file's name)
     * @param contentType MIME type
     * @param path Optional path prefix
     * @return The created storage object
     */
    fun uploadFile(
        file: File,
        filename: String? = null,
        contentType: String,
        path: String? = null
    ): StorageObject {
        val name = filename ?: file.name
        val bytes = file.readBytes()
        return upload(bytes, name, contentType, path)
    }

    /**
     * Download a file's bytes.
     *
     * @param path File path in storage
     * @return File bytes
     */
    fun download(path: String): ByteArray {
        val request = Request.Builder()
            .url(projectUrl("storage/download/$path/"))
            .addHeader("Authorization", "Bearer ${accessToken ?: ""}")
            .get()
            .build()

        val response = httpClient.newCall(request).execute()
        if (!response.isSuccessful) {
            throw APIError(
                status = response.code,
                message = response.message,
                detail = response.body?.string()
            )
        }

        return response.body?.bytes() ?: ByteArray(0)
    }

    /**
     * Get a direct download URL for a file.
     * Note: This may not work for private files without auth.
     *
     * @param path File path
     * @return Download URL
     */
    fun getDownloadUrl(path: String): String {
        return projectUrl("storage/download/$path/")
    }

    // ─── Internal ──────────────────────────────────────────────────────────────

    private fun uploadToPresignedUrl(
        uploadUrl: String,
        file: ByteArray,
        contentType: String
    ) {
        val mediaType = contentType.toMediaTypeOrNull()
        val requestBody = file.toRequestBody(mediaType)

        val request = Request.Builder()
            .url(uploadUrl)
            .put(requestBody)
            .addHeader("Content-Type", contentType)
            .build()

        val response = httpClient.newCall(request).execute()
        if (!response.isSuccessful) {
            throw APIError(
                status = response.code,
                message = "Upload to presigned URL failed: ${response.statusText}",
                detail = response.body?.string()
            )
        }
    }

    private val Response.statusText: String
        get() = when (code) {
            200 -> "OK"
            201 -> "Created"
            204 -> "No Content"
            400 -> "Bad Request"
            401 -> "Unauthorized"
            403 -> "Forbidden"
            404 -> "Not Found"
            500 -> "Internal Server Error"
            else -> "HTTP $code"
        }
}
