package com.ownfirebase.sdk.storage

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
 * Unit tests for StorageService.
 * Tests file uploads, downloads, and storage operations.
 */
class StorageServiceTest {
    private lateinit var mockServer: MockWebServer
    private lateinit var storageService: StorageService
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
        storageService = StorageService(config)
    }

    @After
    fun tearDown() {
        mockServer.shutdown()
    }

    @Test
    fun testGetUploadUrl() {
        val mockResponse = StorageUploadUrl(
            upload_url = "https://storage.example.com/upload?token=xyz",
            object_key = "uploads/file_123.txt",
            expires_at = "2024-01-01T13:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = storageService.getUploadUrl(
            filename = "file_123.txt",
            contentType = "text/plain",
            path = "uploads"
        )

        assertNotNull(result.upload_url)
        assertEquals("uploads/file_123.txt", result.object_key)
        assertNotNull(result.expires_at)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("storage/upload-url") == true)
    }

    @Test
    fun testListFiles() {
        val mockObjects = listOf(
            StorageObject(
                id = "obj_1",
                name = "file1.txt",
                size = 1024L,
                content_type = "text/plain",
                url = "https://storage.example.com/file1.txt",
                created_at = "2024-01-01T00:00:00Z"
            ),
            StorageObject(
                id = "obj_2",
                name = "file2.pdf",
                size = 2048L,
                content_type = "application/pdf",
                url = "https://storage.example.com/file2.pdf",
                created_at = "2024-01-02T00:00:00Z"
            )
        )
        val mockPage = PaginatedResponse(
            count = mockObjects.size,
            next = null,
            previous = null,
            results = mockObjects
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockPage))
        )

        val result = storageService.listFiles("uploads")

        assertEquals(2, result.results.size)
        assertEquals("file1.txt", result.results[0].name)
        assertEquals(1024L, result.results[0].size)
        assertEquals("file2.pdf", result.results[1].name)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("storage/files") == true)
    }

    @Test
    fun testGetFile() {
        val mockObject = StorageObject(
            id = "obj_1",
            name = "document.pdf",
            size = 5242880L, // 5MB
            content_type = "application/pdf",
            url = "https://storage.example.com/document.pdf",
            created_at = "2024-01-01T00:00:00Z"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockObject))
        )

        val result = storageService.getFile("uploads/document.pdf")

        assertEquals("obj_1", result.id)
        assertEquals("document.pdf", result.name)
        assertEquals(5242880L, result.size)
        assertEquals("application/pdf", result.content_type)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("storage/files") == true)
    }

    @Test
    fun testDeleteFile() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(204)
        )

        storageService.deleteFile("uploads/old_file.txt")

        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
        assertTrue(request.path?.contains("storage/files") == true)
    }

    @Test
    fun testGetDownloadUrl() {
        val url = storageService.getDownloadUrl("uploads/document.pdf")

        assertNotNull(url)
        assertTrue(url.contains("document.pdf"))
    }
}
