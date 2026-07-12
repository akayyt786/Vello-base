package com.ownfirebase.sdk.auth

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
 * Unit tests for AuthService.
 * Tests all authentication flows with mocked backend.
 */
class AuthServiceTest {
    private lateinit var mockServer: MockWebServer
    private lateinit var authService: AuthService
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
        authService = AuthService(config)
    }

    @After
    fun tearDown() {
        mockServer.shutdown()
    }

    // ─── Basic Auth Tests ─────────────────────────────────────────────────────

    @Test
    fun testRegisterNewUser() {
        val mockResponse = AuthTokens(
            access = "access_token_123",
            refresh = "refresh_token_123",
            user_id = "user_123",
            email = "test@example.com"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.register(
            email = "test@example.com",
            password = "password123",
            username = "testuser"
        )

        assertEquals("access_token_123", result.access)
        assertEquals("refresh_token_123", result.refresh)
        assertEquals("user_123", result.user_id)
        assertEquals("test@example.com", result.email)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("auth/register") == true)
    }

    @Test
    fun testLoginUser() {
        val mockResponse = AuthTokens(
            access = "access_token_456",
            refresh = "refresh_token_456",
            user_id = "user_456",
            email = "user@example.com"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.login(
            email = "user@example.com",
            password = "password456"
        )

        assertEquals("access_token_456", result.access)
        assertEquals("user_456", result.user_id)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("auth/login") == true)
    }

    @Test
    fun testRefreshToken() {
        val mockResponse = mapOf(
            "access" to "new_access_token_789",
            "refresh" to "refresh_token_789"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.refreshToken("old_refresh_token")

        assertEquals("new_access_token_789", result["access"])
        assertEquals("refresh_token_789", result["refresh"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("auth/refresh") == true)
    }

    @Test
    fun testLogout() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("{}")
        )

        authService.logout("refresh_token")

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("auth/logout") == true)
    }

    @Test
    fun testGetMe() {
        val mockUser = User(
            id = "user_789",
            email = "me@example.com",
            username = "meuser",
            first_name = "Test",
            last_name = "User",
            is_active = true
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockUser))
        )

        val result = authService.getMe()

        assertEquals("user_789", result.id)
        assertEquals("me@example.com", result.email)
        assertEquals("meuser", result.username)
        assertTrue(result.is_active)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("auth/me") == true)
    }

    @Test
    fun testAnonymousSignIn() {
        val mockResponse = AuthTokens(
            access = "anon_access_token",
            refresh = "anon_refresh_token",
            user_id = "anon_user_123"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.anonymousSignIn()

        assertNotNull(result.access)
        assertNotNull(result.refresh)
        assertNotNull(result.user_id)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("anonymous-signin") == true)
    }

    @Test
    fun testSetCustomClaims() {
        val mockResponse = mapOf(
            "message" to "Claims set successfully",
            "claims_count" to "2"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val claims = mapOf("role" to "admin", "department" to "engineering")
        val result = authService.setCustomClaims(claims)

        assertNotNull(result)
        assertEquals("Claims set successfully", result["message"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("set-custom-claims") == true)
    }

    // ─── Social Auth Tests ────────────────────────────────────────────────────

    @Test
    fun testGoogleSignIn() {
        val mockResponse = AuthTokens(
            access = "google_access_token",
            refresh = "google_refresh_token",
            user_id = "google_user_123",
            email = "user@gmail.com"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.googleSignIn("google_id_token_123")

        assertNotNull(result.access)
        assertEquals("google_user_123", result.user_id)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("social/google") == true)
    }

    @Test
    fun testGithubSignIn() {
        val mockResponse = AuthTokens(
            access = "github_access_token",
            refresh = "github_refresh_token",
            user_id = "github_user_456",
            email = "user@github.com"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.githubSignIn("github_access_token_456")

        assertNotNull(result.access)
        assertEquals("github_user_456", result.user_id)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("social/github") == true)
    }

    @Test
    fun testListLinkedAccounts() {
        val mockAccounts = listOf(
            LinkedSocialAccount(
                id = "account_1",
                provider = "google",
                provider_uid = "google_123",
                email = "user@gmail.com",
                linked_at = "2024-01-01T00:00:00Z"
            ),
            LinkedSocialAccount(
                id = "account_2",
                provider = "github",
                provider_uid = "github_456",
                email = "user@github.com",
                linked_at = "2024-01-02T00:00:00Z"
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockAccounts))
        )

        val result = authService.listLinkedAccounts()

        assertEquals(2, result.size)
        assertEquals("google", result[0].provider)
        assertEquals("github", result[1].provider)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("social/linked") == true)
    }

    @Test
    fun testUnlinkSocialAccount() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(204)
        )

        authService.unlinkSocialAccount("account_1")

        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
        assertTrue(request.path?.contains("social/linked") == true)
    }

    // ─── Phone / OTP Tests ────────────────────────────────────────────────────

    @Test
    fun testSendPhoneOTP() {
        val mockResponse = mapOf(
            "request_id" to "otp_request_123",
            "expires_in" to "600"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.sendPhoneOTP("+1234567890")

        assertNotNull(result["request_id"])
        assertEquals("600", result["expires_in"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("phone/send-otp") == true)
    }

    @Test
    fun testVerifyPhoneOTP() {
        val mockResponse = AuthTokens(
            access = "phone_access_token",
            refresh = "phone_refresh_token",
            user_id = "phone_user_123"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.verifyPhoneOTP("+1234567890", "123456")

        assertNotNull(result.access)
        assertNotNull(result.refresh)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("phone/verify-otp") == true)
    }

    // ─── MFA Tests ────────────────────────────────────────────────────────────

    @Test
    fun testEnrollTOTP() {
        val mockResponse = mapOf(
            "secret" to "JBSWY3DPEBLW64TMMQ======",
            "qr_code_url" to "https://example.com/qr.png"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.enrollTOTP()

        assertNotNull(result["secret"])
        assertNotNull(result["qr_code_url"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("mfa/enroll/totp") == true)
    }

    @Test
    fun testConfirmTOTP() {
        val mockResponse = mapOf(
            "message" to "TOTP confirmed",
            "backup_codes" to "code1,code2,code3"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.confirmTOTP("123456")

        assertNotNull(result["message"])
        assertNotNull(result["backup_codes"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("mfa/confirm/totp") == true)
    }

    @Test
    fun testVerifyTOTP() {
        val mockResponse = AuthTokens(
            access = "mfa_access_token",
            refresh = "mfa_refresh_token",
            user_id = "mfa_user_123"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.verifyTOTP("654321")

        assertNotNull(result.access)
        assertNotNull(result.refresh)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("mfa/verify/totp") == true)
    }

    @Test
    fun testEnrollSMS() {
        val mockResponse = mapOf(
            "device_id" to "sms_device_123",
            "message" to "SMS enrollment initiated"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.enrollSMS("+1234567890")

        assertNotNull(result["device_id"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("mfa/enroll/sms") == true)
    }

    @Test
    fun testConfirmSMS() {
        val mockResponse = mapOf(
            "message" to "SMS device confirmed"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.confirmSMS("sms_device_123", "123456")

        assertNotNull(result["message"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("mfa/confirm/sms") == true)
    }

    @Test
    fun testVerifySMS() {
        val mockResponse = AuthTokens(
            access = "sms_access_token",
            refresh = "sms_refresh_token",
            user_id = "sms_user_123"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.verifySMS("sms_device_123", "654321")

        assertNotNull(result.access)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("mfa/verify/sms") == true)
    }

    @Test
    fun testListMFADevices() {
        val mockDevices = listOf(
            MFADevice(
                id = "device_1",
                type = "totp",
                name = "Authenticator App",
                confirmed = true,
                created_at = "2024-01-01T00:00:00Z"
            ),
            MFADevice(
                id = "device_2",
                type = "sms",
                name = "+1234567890",
                confirmed = true,
                created_at = "2024-01-02T00:00:00Z"
            )
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockDevices))
        )

        val result = authService.listMFADevices()

        assertEquals(2, result.size)
        assertEquals("totp", result[0].type)
        assertEquals("sms", result[1].type)

        val request = mockServer.takeRequest()
        assertEquals("GET", request.method)
        assertTrue(request.path?.contains("mfa/devices") == true)
    }

    @Test
    fun testDeleteMFADevice() {
        mockServer.enqueue(
            MockResponse()
                .setResponseCode(204)
        )

        authService.deleteMFADevice("device_1")

        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
        assertTrue(request.path?.contains("mfa/devices") == true)
    }

    // ─── Magic Link Tests ─────────────────────────────────────────────────────

    @Test
    fun testSendMagicLink() {
        val mockResponse = mapOf(
            "message" to "Magic link sent",
            "expires_in" to "3600"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.sendMagicLink("user@example.com")

        assertNotNull(result["message"])
        assertEquals("3600", result["expires_in"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("magic-link/send") == true)
    }

    @Test
    fun testVerifyMagicLink() {
        val mockResponse = AuthTokens(
            access = "magic_access_token",
            refresh = "magic_refresh_token",
            user_id = "magic_user_123",
            email = "user@example.com"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.verifyMagicLink("magic_link_token_123")

        assertNotNull(result.access)
        assertEquals("magic_user_123", result.user_id)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("magic-link/verify") == true)
    }

    // ─── Account Management Tests ─────────────────────────────────────────────

    @Test
    fun testUpgradeAnonymous() {
        val mockResponse = AuthTokens(
            access = "upgraded_access_token",
            refresh = "upgraded_refresh_token",
            user_id = "upgraded_user_123",
            email = "upgraded@example.com"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.upgradeAnonymous(
            email = "upgraded@example.com",
            password = "newpassword123",
            password2 = "newpassword123"
        )

        assertNotNull(result.access)
        assertEquals("upgraded_user_123", result.user_id)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("upgrade") == true)
    }

    @Test
    fun testSetPassword() {
        val mockResponse = mapOf(
            "message" to "Password changed successfully"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.setPassword(
            newPassword = "newpass456",
            newPassword2 = "newpass456",
            currentPassword = "oldpass456"
        )

        assertNotNull(result["message"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("set-password") == true)
    }

    @Test
    fun testLinkEmail() {
        val mockResponse = mapOf(
            "message" to "Email linked successfully"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.linkEmail("newemail@example.com", "password789")

        assertNotNull(result["message"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("link-email") == true)
    }

    @Test
    fun testVerifyEmailChange() {
        val mockResponse = mapOf(
            "message" to "Email verified"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.verifyEmailChange("email_change_token_123")

        assertNotNull(result["message"])

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("verify-email-change") == true)
    }

    @Test
    fun testIssueCustomToken() {
        val mockResponse = CustomToken(
            custom_token = "custom_token_xyz_789"
        )

        mockServer.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody(gson.toJson(mockResponse))
        )

        val result = authService.issueCustomToken(
            userId = "user_789",
            claims = mapOf("role" to "admin")
        )

        assertNotNull(result.custom_token)
        assertEquals("custom_token_xyz_789", result.custom_token)

        val request = mockServer.takeRequest()
        assertEquals("POST", request.method)
        assertTrue(request.path?.contains("auth/custom-token") == true)
    }
}
