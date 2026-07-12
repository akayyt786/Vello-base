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
import kotlin.test.assertFalse

/**
 * Advanced auth flow tests.
 * Tests complex authentication scenarios and edge cases.
 */
class AdvancedAuthFlowTest {
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

    // ─── MFA Flow Tests ──────────────────────────────────────────────────────

    @Test
    fun testTOTPEnrollmentFlow() {
        // Step 1: Enroll TOTP
        val enrollResponse = mapOf(
            "device_id" to "totp_device_123",
            "secret" to "JBSWY3DPEBLW64TMMQ======",
            "qr_code_url" to "https://example.com/qr.png"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(enrollResponse)))

        val enrollResult = authService.enrollTOTP()
        assertNotNull(enrollResult["secret"])
        val deviceId = enrollResult["device_id"]!!

        // Step 2: Confirm TOTP
        val confirmResponse = mapOf(
            "message" to "TOTP confirmed",
            "backup_codes" to "code1,code2,code3"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(confirmResponse)))

        val confirmResult = authService.confirmTOTP(deviceId, "123456")
        assertNotNull(confirmResult["backup_codes"])

        // Step 3: Later, verify TOTP during login
        val verifyResponse = AuthTokens(
            access = "access_token",
            refresh = "refresh_token",
            user_id = "user_123"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(verifyResponse)))

        val verifyResult = authService.verifyTOTP(deviceId, "654321")
        assertNotNull(verifyResult.access)
    }

    @Test
    fun testSMSMFAFlow() {
        // Step 1: Enroll SMS
        val enrollResponse = mapOf(
            "device_id" to "sms_device_123",
            "message" to "SMS enrollment initiated"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(enrollResponse)))

        val enrollResult = authService.enrollSMS("+1234567890")
        val deviceId = enrollResult["device_id"]
        assertNotNull(deviceId)

        // Step 2: Confirm SMS
        val confirmResponse = mapOf(
            "message" to "SMS device confirmed"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(confirmResponse)))

        val confirmResult = authService.confirmSMS(deviceId!!, "123456")
        assertNotNull(confirmResult["message"])

        // Step 3: Send SMS code
        val sendResponse = mapOf(
            "request_id" to "sms_request_123"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(sendResponse)))

        val sendResult = authService.sendSMSCode(deviceId)
        assertNotNull(sendResult["request_id"])

        // Step 4: Verify SMS during login
        val verifyResponse = AuthTokens(
            access = "access_token",
            refresh = "refresh_token",
            user_id = "user_123"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(verifyResponse)))

        val verifyResult = authService.verifySMS(deviceId, "654321")
        assertNotNull(verifyResult.access)
    }

    @Test
    fun testMultipleMFADevices() {
        // Enroll multiple MFA devices
        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(mapOf("device_id" to "totp_1"))))
        authService.enrollTOTP()

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(mapOf("device_id" to "sms_1"))))
        authService.enrollSMS("+1234567890")

        // List all MFA devices
        val mockDevices = listOf(
            MFADevice(
                id = "totp_1",
                type = "totp",
                name = "Authenticator App",
                confirmed = true,
                created_at = "2024-01-01T00:00:00Z"
            ),
            MFADevice(
                id = "sms_1",
                type = "sms",
                name = "+1234567890",
                confirmed = true,
                created_at = "2024-01-01T00:00:00Z"
            )
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(mockDevices)))

        val devices = authService.listMFADevices()
        assertEquals(2, devices.size)

        // Delete one device
        mockServer.enqueue(MockResponse()
            .setResponseCode(204))
        authService.deleteMFADevice("sms_1")

        // Drain the enrollTOTP, enrollSMS, and listMFADevices requests before
        // checking the deleteMFADevice request (takeRequest() is FIFO).
        repeat(3) { mockServer.takeRequest() }
        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
    }

    // ─── Social Auth + Account Linking Flow ──────────────────────────────────

    @Test
    fun testSocialAuthAndLinking() {
        // Step 1: Sign in with Google
        val googleSignInResponse = AuthTokens(
            access = "google_access",
            refresh = "google_refresh",
            user_id = "user_123",
            email = "user@gmail.com"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(googleSignInResponse)))

        val googleResult = authService.googleSignIn("google_id_token")
        assertEquals("user_123", googleResult.user_id)

        // Step 2: Link GitHub account (githubSignIn returns AuthTokens, same as any social sign-in)
        val linkResponse = AuthTokens(
            access = "github_access",
            refresh = "github_refresh",
            user_id = "user_123",
            email = "user@github.com"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(linkResponse)))

        val linkedResult = authService.githubSignIn("github_access_token")
        assertNotNull(linkedResult.access)

        // Step 3: List linked accounts
        val linkedAccounts = listOf(
            LinkedSocialAccount(
                id = "google_1",
                provider = "google",
                provider_uid = "google_123",
                email = "user@gmail.com",
                linked_at = "2024-01-01T00:00:00Z"
            ),
            LinkedSocialAccount(
                id = "github_1",
                provider = "github",
                provider_uid = "github_456",
                email = "user@github.com",
                linked_at = "2024-01-02T00:00:00Z"
            )
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(linkedAccounts)))

        val accounts = authService.listLinkedAccounts()
        assertEquals(2, accounts.size)
        assertEquals("google", accounts[0].provider)
        assertEquals("github", accounts[1].provider)

        // Step 4: Unlink one account
        mockServer.enqueue(MockResponse()
            .setResponseCode(204))

        authService.unlinkSocialAccount("github_1")

        // Drain the googleSignIn, githubSignIn, and listLinkedAccounts requests
        // before checking the unlinkSocialAccount request (takeRequest() is FIFO).
        repeat(3) { mockServer.takeRequest() }
        val request = mockServer.takeRequest()
        assertEquals("DELETE", request.method)
    }

    // ─── Passwordless Flow Tests ──────────────────────────────────────────────

    @Test
    fun testPasswordlessPhoneOTPFlow() {
        // Step 1: Send OTP
        val sendOTPResponse = mapOf(
            "request_id" to "otp_request_123",
            "expires_in" to "600"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(sendOTPResponse)))

        val sendResult = authService.sendPhoneOTP("+1234567890")
        assertNotNull(sendResult["request_id"])

        // Step 2: Verify OTP and sign in
        val verifyResponse = AuthTokens(
            access = "access_token",
            refresh = "refresh_token",
            user_id = "user_123"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(verifyResponse)))

        val verifyResult = authService.verifyPhoneOTP("+1234567890", "123456")
        assertNotNull(verifyResult.access)
        assertEquals("user_123", verifyResult.user_id)
    }

    @Test
    fun testMagicLinkFlow() {
        // Step 1: Send magic link
        val sendResponse = mapOf(
            "message" to "Magic link sent",
            "expires_in" to "3600"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(sendResponse)))

        val sendResult = authService.sendMagicLink("user@example.com")
        assertNotNull(sendResult["message"])

        // Step 2: User clicks link and verifies
        val verifyResponse = AuthTokens(
            access = "access_token",
            refresh = "refresh_token",
            user_id = "user_123",
            email = "user@example.com"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(verifyResponse)))

        val verifyResult = authService.verifyMagicLink("magic_link_token_123")
        assertNotNull(verifyResult.access)
        assertEquals("user@example.com", verifyResult.email)
    }

    // ─── Anonymous + Account Upgrade Flow ────────────────────────────────────

    @Test
    fun testAnonymousToAuthenticatedUpgrade() {
        // Step 1: Sign in anonymously
        val anonResponse = AuthTokens(
            access = "anon_access",
            refresh = "anon_refresh",
            user_id = "anon_user_123"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(anonResponse)))

        val anonResult = authService.anonymousSignIn()
        assertEquals("anon_user_123", anonResult.user_id)

        // Step 2: User decides to create account - upgrade anonymous
        val upgradeResponse = AuthTokens(
            access = "upgraded_access",
            refresh = "upgraded_refresh",
            user_id = "anon_user_123", // Same user ID
            email = "user@example.com"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(upgradeResponse)))

        val upgradeResult = authService.upgradeAnonymous(
            email = "user@example.com",
            password = "SecurePassword123!",
            password2 = "SecurePassword123!"
        )

        assertEquals("anon_user_123", upgradeResult.user_id)
        assertEquals("user@example.com", upgradeResult.email)
    }

    // ─── Account Management Flow Tests ───────────────────────────────────────

    @Test
    fun testPasswordChangeFlow() {
        // Step 1: Set new password
        val setPasswordResponse = mapOf(
            "message" to "Password changed successfully"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(setPasswordResponse)))

        val result = authService.setPassword(
            newPassword = "NewPassword123!",
            newPassword2 = "NewPassword123!",
            currentPassword = "OldPassword123!"
        )

        assertNotNull(result["message"])

        // Step 2: Login with new password
        val loginResponse = AuthTokens(
            access = "new_access",
            refresh = "new_refresh",
            user_id = "user_123",
            email = "user@example.com"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(loginResponse)))

        val loginResult = authService.login("user@example.com", "NewPassword123!")
        assertNotNull(loginResult.access)
    }

    @Test
    fun testEmailLinkingAndChange() {
        // Step 1: Link new email (while having current email)
        val linkResponse = mapOf(
            "message" to "Email linked successfully",
            "verification_required" to "true"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(linkResponse)))

        val linkResult = authService.linkEmail("newemail@example.com", "password123")
        assertEquals("true", linkResult["verification_required"])

        // Step 2: Verify email change token (from email link)
        val verifyResponse = mapOf(
            "message" to "Email verified",
            "new_email" to "newemail@example.com"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(verifyResponse)))

        val verifyResult = authService.verifyEmailChange("email_change_token_123")
        assertEquals("newemail@example.com", verifyResult["new_email"])
    }

    // ─── Custom Claims & Authorization ───────────────────────────────────────

    @Test
    fun testCustomClaimsFlow() {
        // Set custom claims for authorization
        val claimsResponse = mapOf(
            "message" to "Claims set successfully",
            "claims_count" to "3"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(claimsResponse)))

        val claims = mapOf(
            "role" to "admin",
            "department" to "engineering",
            "permissions" to listOf("read", "write", "delete")
        )

        val result = authService.setCustomClaims(claims)
        assertEquals("3", result["claims_count"])

        // Get current user with claims
        val userResponse = User(
            id = "user_123",
            email = "admin@example.com",
            username = "adminuser",
            first_name = "Admin",
            last_name = "User",
            is_active = true
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(userResponse)))

        val user = authService.getMe()
        assertNotNull(user)
    }

    // ─── Token Management Flow ───────────────────────────────────────────────

    @Test
    fun testTokenRefreshAndRotation() {
        // Initial login
        val loginResponse = AuthTokens(
            access = "access_v1",
            refresh = "refresh_v1",
            user_id = "user_123"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(loginResponse)))

        val loginResult = authService.login("user@example.com", "password")
        assertEquals("access_v1", loginResult.access)

        // Token expires, refresh it
        val refreshResponse = mapOf(
            "access" to "access_v2",
            "refresh" to "refresh_v2"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(refreshResponse)))

        val refreshResult = authService.refreshToken("refresh_v1")
        assertEquals("access_v2", refreshResult["access"])
        assertEquals("refresh_v2", refreshResult["refresh"])

        // Refresh again
        val refreshResponse2 = mapOf(
            "access" to "access_v3",
            "refresh" to "refresh_v3"
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(refreshResponse2)))

        val refreshResult2 = authService.refreshToken("refresh_v2")
        assertEquals("access_v3", refreshResult2["access"])
    }

    // ─── Custom Token Flow ───────────────────────────────────────────────────

    @Test
    fun testCustomTokenIssuance() {
        val tokenResponse = CustomToken(
            custom_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )

        mockServer.enqueue(MockResponse()
            .setResponseCode(200)
            .setBody(gson.toJson(tokenResponse)))

        val result = authService.issueCustomToken(
            userId = "user_123",
            claims = mapOf(
                "role" to "service_account",
                "scope" to "internal"
            )
        )

        assertNotNull(result.custom_token)
        assertTrue(result.custom_token.isNotEmpty())
    }
}
