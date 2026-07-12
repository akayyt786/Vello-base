package com.ownfirebase.sdk.config

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
 * Unit tests for RemoteConfigService.
 * Tests feature flags, configuration parameters, and A/B testing conditions.
 */
class RemoteConfigServiceTest {
    private lateinit var mockServer: MockWebServer
    private lateinit var remoteConfigService: RemoteConfigService
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
        remoteConfigService = RemoteConfigService(config)
    }

    @After
    fun tearDown() {
        mockServer.shutdown()
    }

    @Test
    fun testListParameters() {
        val mockParameters = listOf(
            RemoteConfigParameter(
                id = "param_1",
                key = "feature_new_ui",
                default_value = "false",
                description = "Enable new UI redesign",
                value_type = "boolean"
            ),
            RemoteConfigParameter(
                id = "param_2",
                key = "max_upload_size",
                default_value = "10485760",
                description = "Maximum file upload size in bytes",
                value_type = "number"
            ),
            RemoteConfigParameter(
                id = "param_3",
                key = "api_endpoint",
                default_value = "https://api.example.com",
                description = "API endpoint URL",
                value_type = "string"
            )
        )
        // listParameters() returns a PaginatedResponse<RemoteConfigParameter>, not a bare list.
        val mockPage = PaginatedResponse(
            count = mockParameters.size,
            next = null,
            previous = null,
            results = mockParameters
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockPage))
        )

        val result = remoteConfigService.listParameters()

        assertEquals(3, result.results.size)
        assertEquals("feature_new_ui", result.results[0].key)
        assertEquals("boolean", result.results[0].value_type)
        assertEquals("false", result.results[0].default_value)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
    }

    @Test
    fun testGetParameter() {
        val mockParameter = RemoteConfigParameter(
            id = "param_1",
            key = "feature_new_ui",
            default_value = "false",
            description = "Enable new UI redesign",
            value_type = "boolean"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockParameter))
        )

        val result = remoteConfigService.getParameter("feature_new_ui")

        assertEquals("param_1", result.id)
        assertEquals("feature_new_ui", result.key)
        assertEquals("false", result.default_value)
        assertEquals("boolean", result.value_type)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
    }

    @Test
    fun testCreateParameter() {
        val mockParameter = RemoteConfigParameter(
            id = "param_new",
            key = "feature_beta",
            default_value = "true",
            description = "Beta feature flag",
            value_type = "boolean"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockParameter))
        )

        val result = remoteConfigService.createParameter(
            key = "feature_beta",
            defaultValue = "true",
            description = "Beta feature flag",
            valueType = "boolean"
        )

        assertEquals("param_new", result.id)
        assertEquals("feature_beta", result.key)
        assertEquals("true", result.default_value)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
    }

    @Test
    fun testUpdateParameter() {
        val mockParameter = RemoteConfigParameter(
            id = "param_1",
            key = "feature_new_ui",
            default_value = "true",
            description = "Enable new UI redesign (updated)",
            value_type = "boolean"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockParameter))
        )

        val result = remoteConfigService.updateParameter(
            id = "param_1",
            key = "feature_new_ui",
            defaultValue = "true",
            description = "Enable new UI redesign (updated)"
        )

        assertEquals("param_1", result.id)
        assertEquals("true", result.default_value)

        val request = mockServer.takeRequest()
        assertEquals("PATCH", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
    }

    @Test
    fun testDeleteParameter() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(204)
        )

        remoteConfigService.deleteParameter("feature_beta")

        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
    }

    @Test
    fun testListConditions() {
        val mockConditions = listOf(
            ConfigCondition(
                id = "cond_1",
                name = "user_in_us",
                expression = "user_country == 'US'",
                value = "true"
            ),
            ConfigCondition(
                id = "cond_2",
                name = "user_premium",
                expression = "user_tier == 'premium'",
                value = "true"
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockConditions))
        )

        // Conditions live under a specific parameter, so a configId is required.
        val result = remoteConfigService.listConditions(configId = "param_1")

        assertEquals(2, result.size)
        assertEquals("user_in_us", result[0].name)
        assertEquals("user_country == 'US'", result[0].expression)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        // Real route is config/parameters/{configId}/conditions/, not config/conditions.
        assertTrue(request.path?.contains("config/parameters") == true)
        assertTrue(request.path?.contains("conditions") == true)
    }

    @Test
    fun testCreateCondition() {
        val mockCondition = ConfigCondition(
            id = "cond_new",
            name = "beta_testers",
            expression = "user_id IN beta_users_list",
            value = "true"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setBody(gson.toJson(mockCondition))
        )

        val result = remoteConfigService.createCondition(
            configId = "param_1",
            name = "beta_testers",
            expression = "user_id IN beta_users_list",
            value = "true"
        )

        assertEquals("cond_new", result.id)
        assertEquals("beta_testers", result.name)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
        assertTrue(request.path?.contains("conditions") == true)
    }

    @Test
    fun testGetCondition() {
        // The real service has no single-condition getter — conditions are only
        // retrievable via listConditions(configId). The closest equivalent to
        // "get a condition by id" is fetching the list and finding it there.
        val mockConditions = listOf(
            ConfigCondition(
                id = "cond_1",
                name = "user_in_us",
                expression = "user_country == 'US'",
                value = "true"
            ),
            ConfigCondition(
                id = "cond_2",
                name = "user_premium",
                expression = "user_tier == 'premium'",
                value = "true"
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockConditions))
        )

        val conditions = remoteConfigService.listConditions(configId = "param_1")
        val result = conditions.find { it.id == "cond_1" }

        assertNotNull(result)
        assertEquals("cond_1", result.id)
        assertEquals("user_in_us", result.name)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
        assertTrue(request.path?.contains("conditions") == true)
    }

    @Test
    fun testUpdateCondition() {
        val mockCondition = ConfigCondition(
            id = "cond_1",
            name = "user_in_us",
            expression = "user_country == 'US' AND user_active == true",
            value = "true"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockCondition))
        )

        val result = remoteConfigService.updateCondition(
            configId = "param_1",
            conditionId = "cond_1",
            expression = "user_country == 'US' AND user_active == true"
        )

        assertEquals("cond_1", result.id)
        assertEquals("user_country == 'US' AND user_active == true", result.expression)

        val request = mockServer.takeRequest()
        assertEquals("PATCH", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
        assertTrue(request.path?.contains("conditions") == true)
        assertTrue(request.path?.contains("cond_1") == true)
    }

    @Test
    fun testDeleteCondition() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(204)
        )

        remoteConfigService.deleteCondition(configId = "param_1", conditionId = "cond_1")

        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
        assertTrue(request.path?.contains("conditions") == true)
        assertTrue(request.path?.contains("cond_1") == true)
    }

    @Test
    fun testGetConfigValues() {
        // There is no per-user config resolution endpoint (getConfigForUser) on the
        // real service — condition evaluation against a user context isn't exposed
        // client-side. The closest real equivalent is the typed getter helpers
        // (getBoolean/getNumber/etc.) which resolve a parameter's value from the
        // parameter list, which is what a client actually uses to read config values.
        val mockParameters = listOf(
            RemoteConfigParameter(
                id = "param_1",
                key = "feature_new_ui",
                default_value = "true",
                description = "Enable new UI redesign",
                value_type = "boolean"
            ),
            RemoteConfigParameter(
                id = "param_2",
                key = "max_upload_size",
                default_value = "20971520",
                description = "Maximum file upload size in bytes",
                value_type = "number"
            )
        )
        val mockPage = PaginatedResponse(count = mockParameters.size, results = mockParameters)

        mockServer.enqueue(MockResponse().setResponseCode(200).setBody(gson.toJson(mockPage)))
        mockServer.enqueue(MockResponse().setResponseCode(200).setBody(gson.toJson(mockPage)))

        val featureEnabled = remoteConfigService.getBoolean("feature_new_ui", false)
        val maxUploadSize = remoteConfigService.getNumber("max_upload_size", 0.0)

        assertTrue(featureEnabled)
        assertEquals(20971520.0, maxUploadSize)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
    }

    @Test
    fun testRefreshCache() {
        // There is no publish/versioning endpoint (publishConfig) on the real
        // service. The closest real equivalent — the operation a client actually
        // performs to pick up newly published config — is refreshCache(), which
        // re-fetches all parameters and repopulates the local cache.
        val mockParameters = listOf(
            RemoteConfigParameter(
                id = "param_1",
                key = "feature_new_ui",
                default_value = "true",
                description = "Enable new UI redesign",
                value_type = "boolean"
            )
        )
        val mockPage = PaginatedResponse(count = mockParameters.size, results = mockParameters)

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockPage))
        )

        remoteConfigService.refreshCache()

        // getParameter should now be served from the cache populated by refreshCache(),
        // without issuing a second network request.
        val cached = remoteConfigService.getParameter("param_1")
        assertEquals("true", cached.default_value)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
        // Only the refreshCache() call should have hit the network.
        assertEquals(1, mockServer.requestCount)
    }

    @Test
    fun testParametersTotalCount() {
        // There is no config-version endpoint (getConfigVersion) on the real
        // service. The closest real equivalent for "how many parameters exist"
        // metadata is the `count` field on the paginated parameters response,
        // which can differ from the number of results on the current page.
        val mockParameters = listOf(
            RemoteConfigParameter(
                id = "param_1",
                key = "feature_new_ui",
                default_value = "true",
                description = "Enable new UI redesign",
                value_type = "boolean"
            ),
            RemoteConfigParameter(
                id = "param_2",
                key = "max_upload_size",
                default_value = "20971520",
                description = "Maximum file upload size in bytes",
                value_type = "number"
            )
        )
        val mockPage = PaginatedResponse(
            count = 10,
            next = "https://example.com/api/projects/test-project/config/parameters/?page=2",
            previous = null,
            results = mockParameters
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockPage))
        )

        val result = remoteConfigService.listParameters()

        assertEquals(10, result.count)
        assertEquals(2, result.results.size)
        assertNotNull(result.next)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("config/parameters") == true)
    }
}
