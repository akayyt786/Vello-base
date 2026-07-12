package com.ownfirebase.sdk.auth

import com.ownfirebase.sdk.client.OwnFirebaseClient
import com.ownfirebase.sdk.types.*

/**
 * Authentication service for OwnFirebase SDK.
 * Handles user registration, login, logout, MFA, social auth, and more.
 */
class AuthService(config: OwnFirebaseConfig) : OwnFirebaseClient(config) {

    // ─── Core Auth ────────────────────────────────────────────────────────────

    /**
     * Register a new user with email and password.
     */
    fun register(
        email: String,
        password: String,
        username: String? = null
    ): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/register/",
            mapOf(
                "email" to email,
                "password" to password,
                "username" to username
            ).filterValues { it != null },
            RequestOptions(noAuth = true)
        )
    }

    /**
     * Login user with email and password.
     */
    fun login(email: String, password: String): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/login/",
            mapOf("email" to email, "password" to password),
            RequestOptions(noAuth = true)
        )
    }

    /**
     * Refresh access token using refresh token.
     */
    fun refreshToken(refresh: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/refresh/",
            mapOf("refresh" to refresh),
            RequestOptions(noAuth = true)
        )
    }

    /**
     * Logout user and invalidate refresh token.
     */
    fun logout(refresh: String) {
        request<Unit>(
            "POST",
            "$baseUrl/api/v1/auth/logout/",
            mapOf("refresh" to refresh)
        )
    }

    /**
     * Get current authenticated user's profile.
     */
    fun getMe(): User {
        return request(
            "GET",
            "$baseUrl/api/v1/auth/me/"
        )
    }

    /**
     * Sign in anonymously (creates anonymous user).
     */
    fun anonymousSignIn(): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/anonymous-signin/",
            emptyMap<String, String>(),
            RequestOptions(noAuth = true)
        )
    }

    /**
     * Set custom claims on the current user.
     */
    fun setCustomClaims(claims: Map<String, Any?>): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/set-custom-claims/",
            mapOf("claims" to claims)
        )
    }

    // ─── Social Auth ──────────────────────────────────────────────────────────

    /**
     * Sign in with Google using ID token.
     */
    fun googleSignIn(idToken: String): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/social/google/",
            mapOf("id_token" to idToken),
            RequestOptions(noAuth = true)
        )
    }

    /**
     * Sign in with GitHub using access token.
     */
    fun githubSignIn(accessToken: String): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/social/github/",
            mapOf("access_token" to accessToken),
            RequestOptions(noAuth = true)
        )
    }

    /**
     * List all linked social accounts for current user.
     */
    fun listLinkedAccounts(): List<LinkedSocialAccount> {
        return request(
            "GET",
            "$baseUrl/api/v1/auth/social/linked/"
        )
    }

    /**
     * Unlink a social account from current user.
     */
    fun unlinkSocialAccount(accountId: String) {
        request<Unit>(
            "DELETE",
            "$baseUrl/api/v1/auth/social/linked/$accountId/"
        )
    }

    // ─── Phone / OTP ──────────────────────────────────────────────────────────

    /**
     * Send OTP code to phone number.
     */
    fun sendPhoneOTP(phoneNumber: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/phone/send-otp/",
            mapOf("phone_number" to phoneNumber),
            RequestOptions(noAuth = true)
        )
    }

    /**
     * Verify phone OTP and sign in.
     */
    fun verifyPhoneOTP(phoneNumber: String, code: String): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/phone/verify-otp/",
            mapOf("phone_number" to phoneNumber, "code" to code),
            RequestOptions(noAuth = true)
        )
    }

    // ─── MFA (Multi-Factor Authentication) ────────────────────────────────────

    /**
     * Enroll TOTP (Time-based One-Time Password).
     */
    fun enrollTOTP(): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/mfa/enroll/totp/",
            emptyMap<String, String>()
        )
    }

    /**
     * Confirm TOTP enrollment with code.
     */
    fun confirmTOTP(code: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/mfa/confirm/totp/",
            mapOf("code" to code)
        )
    }

    /**
     * Verify TOTP code during login.
     */
    fun verifyTOTP(code: String): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/mfa/verify/totp/",
            mapOf("code" to code)
        )
    }

    /**
     * Enroll SMS for MFA.
     */
    fun enrollSMS(phoneNumber: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/mfa/enroll/sms/",
            mapOf("phone_number" to phoneNumber)
        )
    }

    /**
     * Confirm SMS enrollment.
     */
    fun confirmSMS(deviceId: String, code: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/mfa/confirm/sms/",
            mapOf("device_id" to deviceId, "code" to code)
        )
    }

    /**
     * Verify SMS code during login.
     */
    fun verifySMS(deviceId: String, code: String): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/mfa/verify/sms/",
            mapOf("device_id" to deviceId, "code" to code)
        )
    }

    /**
     * Send SMS code to MFA device.
     */
    fun sendSMSCode(deviceId: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/mfa/send-sms-code/$deviceId/",
            emptyMap<String, String>()
        )
    }

    /**
     * List all MFA devices for current user.
     */
    fun listMFADevices(): List<MFADevice> {
        return request(
            "GET",
            "$baseUrl/api/v1/auth/mfa/devices/"
        )
    }

    /**
     * Delete an MFA device.
     */
    fun deleteMFADevice(deviceId: String) {
        request<Unit>(
            "DELETE",
            "$baseUrl/api/v1/auth/mfa/devices/$deviceId/"
        )
    }

    // ─── Passwordless / Magic Link ────────────────────────────────────────────

    /**
     * Send magic link to email for passwordless login.
     */
    fun sendMagicLink(email: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/magic-link/send/",
            mapOf("email" to email),
            RequestOptions(noAuth = true)
        )
    }

    /**
     * Verify magic link token and sign in.
     */
    fun verifyMagicLink(token: String): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/magic-link/verify/",
            mapOf("token" to token),
            RequestOptions(noAuth = true)
        )
    }

    // ─── Account Management ───────────────────────────────────────────────────

    /**
     * Upgrade anonymous user to full user with email/password.
     */
    fun upgradeAnonymous(
        email: String,
        password: String,
        password2: String
    ): AuthTokens {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/upgrade/",
            mapOf(
                "email" to email,
                "password" to password,
                "password2" to password2
            )
        )
    }

    /**
     * Set or change user password.
     */
    fun setPassword(
        newPassword: String,
        newPassword2: String,
        currentPassword: String? = null
    ): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/set-password/",
            mapOf(
                "new_password" to newPassword,
                "new_password2" to newPassword2,
                "current_password" to currentPassword
            ).filterValues { it != null }
        )
    }

    /**
     * Link email account to current user.
     */
    fun linkEmail(email: String, password: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/link-email/",
            mapOf("email" to email, "password" to password)
        )
    }

    /**
     * Verify email change token.
     */
    fun verifyEmailChange(token: String): Map<String, String> {
        return request(
            "POST",
            "$baseUrl/api/v1/auth/verify-email-change/",
            mapOf("token" to token),
            RequestOptions(noAuth = true)
        )
    }

    // ─── Custom Token (project-scoped) ────────────────────────────────────────

    /**
     * Issue a custom token for a specific user.
     */
    fun issueCustomToken(
        userId: String,
        claims: Map<String, Any?>? = null
    ): CustomToken {
        return request(
            "POST",
            projectUrl("auth/custom-token/"),
            mapOf(
                "user_id" to userId,
                "claims" to claims
            ).filterValues { it != null }
        )
    }
}
