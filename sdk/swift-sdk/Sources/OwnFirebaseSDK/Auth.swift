import Foundation

public class AuthService: OwnFirebaseClient {
  // MARK: - Core Auth

  public func register(
    email: String,
    password: String,
    username: String? = nil
  ) async throws -> AuthTokens {
    let body = RegisterRequest(email: email, password: password, username: username)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/register/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
    setAccessToken(tokens.access)
    return tokens
  }

  public func login(email: String, password: String) async throws -> AuthTokens {
    let body = LoginRequest(email: email, password: password)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/login/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
    setAccessToken(tokens.access)
    return tokens
  }

  public func refreshToken(refresh: String) async throws -> TokenRefreshResponse {
    let body = RefreshTokenRequest(refresh: refresh)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/refresh/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
  }

  public func logout(refresh: String) async throws {
    let body = LogoutRequest(refresh: refresh)
    try await requestVoid(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/logout/",
      body: body
    )
  }

  public func getMe() async throws -> User {
    return try await request(
      "GET",
      url: "\(config.baseUrl)/api/v1/auth/me/"
    )
  }

  public func anonymousSignIn() async throws -> AuthTokens {
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/anonymous-signin/",
      body: EmptyRequest(),
      options: RequestOptions(noAuth: true)
    )
    setAccessToken(tokens.access)
    return tokens
  }

  public func setCustomClaims(_ claims: [String: AnyCodable]) async throws -> MessageResponse {
    let body = SetCustomClaimsRequest(claims: claims)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/set-custom-claims/",
      body: body
    )
  }

  // MARK: - Social Auth

  public func googleSignIn(idToken: String) async throws -> AuthTokens {
    let body = GoogleSignInRequest(id_token: idToken)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/social/google/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
    setAccessToken(tokens.access)
    return tokens
  }

  public func githubSignIn(accessToken: String) async throws -> AuthTokens {
    let body = GithubSignInRequest(access_token: accessToken)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/social/github/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
    setAccessToken(tokens.access)
    return tokens
  }

  public func listLinkedAccounts() async throws -> [LinkedSocialAccount] {
    return try await request(
      "GET",
      url: "\(config.baseUrl)/api/v1/auth/social/linked/"
    )
  }

  public func unlinkSocialAccount(_ accountId: String) async throws {
    try await requestVoid(
      "DELETE",
      url: "\(config.baseUrl)/api/v1/auth/social/linked/\(accountId)/"
    )
  }

  // MARK: - Phone / OTP

  public func sendPhoneOTP(phoneNumber: String) async throws -> MessageResponse {
    let body = SendPhoneOTPRequest(phone_number: phoneNumber)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/phone/send-otp/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
  }

  public func verifyPhoneOTP(phoneNumber: String, code: String) async throws -> AuthTokens {
    let body = VerifyPhoneOTPRequest(phone_number: phoneNumber, code: code)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/phone/verify-otp/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
    setAccessToken(tokens.access)
    return tokens
  }

  // MARK: - MFA

  public func enrollTOTP() async throws -> EnrollTOTPResponse {
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/mfa/enroll/totp/",
      body: EmptyRequest()
    )
  }

  public func confirmTOTP(code: String) async throws -> MessageResponse {
    let body = ConfirmTOTPRequest(code: code)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/mfa/confirm/totp/",
      body: body
    )
  }

  public func verifyTOTP(code: String) async throws -> AuthTokens {
    let body = VerifyTOTPRequest(code: code)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/mfa/verify/totp/",
      body: body
    )
    setAccessToken(tokens.access)
    return tokens
  }

  public func enrollSMS(phoneNumber: String) async throws -> MessageResponse {
    let body = EnrollSMSRequest(phone_number: phoneNumber)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/mfa/enroll/sms/",
      body: body
    )
  }

  public func confirmSMS(deviceId: String, code: String) async throws -> MessageResponse {
    let body = ConfirmSMSRequest(device_id: deviceId, code: code)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/mfa/confirm/sms/",
      body: body
    )
  }

  public func verifySMS(deviceId: String, code: String) async throws -> AuthTokens {
    let body = VerifySMSRequest(device_id: deviceId, code: code)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/mfa/verify/sms/",
      body: body
    )
    setAccessToken(tokens.access)
    return tokens
  }

  public func sendSMSCode(deviceId: String) async throws -> MessageResponse {
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/mfa/send-sms-code/\(deviceId)/",
      body: EmptyRequest()
    )
  }

  public func listMFADevices() async throws -> [MFADevice] {
    return try await request(
      "GET",
      url: "\(config.baseUrl)/api/v1/auth/mfa/devices/"
    )
  }

  public func deleteMFADevice(_ deviceId: String) async throws {
    try await requestVoid(
      "DELETE",
      url: "\(config.baseUrl)/api/v1/auth/mfa/devices/\(deviceId)/"
    )
  }

  // MARK: - Magic Link

  public func sendMagicLink(email: String) async throws -> MessageResponse {
    let body = SendMagicLinkRequest(email: email)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/magic-link/send/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
  }

  public func verifyMagicLink(token: String) async throws -> AuthTokens {
    let body = VerifyMagicLinkRequest(token: token)
    let tokens: AuthTokens = try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/magic-link/verify/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
    setAccessToken(tokens.access)
    return tokens
  }

  // MARK: - Account Management

  public func upgradeAnonymous(
    email: String,
    password: String,
    password2: String
  ) async throws -> AuthTokens {
    let body = UpgradeAnonymousRequest(email: email, password: password, password2: password2)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/upgrade/",
      body: body
    )
  }

  public func setPassword(
    newPassword: String,
    newPassword2: String,
    currentPassword: String? = nil
  ) async throws -> MessageResponse {
    let body = SetPasswordRequest(
      new_password: newPassword,
      new_password2: newPassword2,
      current_password: currentPassword
    )
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/set-password/",
      body: body
    )
  }

  public func linkEmail(email: String, password: String) async throws -> MessageResponse {
    let body = LinkEmailRequest(email: email, password: password)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/link-email/",
      body: body
    )
  }

  public func verifyEmailChange(token: String) async throws -> MessageResponse {
    let body = VerifyEmailChangeRequest(token: token)
    return try await request(
      "POST",
      url: "\(config.baseUrl)/api/v1/auth/verify-email-change/",
      body: body,
      options: RequestOptions(noAuth: true)
    )
  }

  // MARK: - Custom Token

  public func issueCustomToken(
    userId: String,
    claims: [String: AnyCodable]? = nil
  ) async throws -> CustomToken {
    guard config.projectId != nil else {
      throw OwnFirebaseError.missingProjectId
    }
    let body = IssueCustomTokenRequest(user_id: userId, claims: claims)
    return try await request(
      "POST",
      url: projectUrl("auth/custom-token/"),
      body: body
    )
  }
}

// MARK: - Request Types

private struct RegisterRequest: Encodable {
  let email: String
  let password: String
  let username: String?
}

private struct LoginRequest: Encodable {
  let email: String
  let password: String
}

private struct RefreshTokenRequest: Encodable {
  let refresh: String
}

public struct TokenRefreshResponse: Codable {
  public let access: String
}

private struct LogoutRequest: Encodable {
  let refresh: String
}

private struct SetCustomClaimsRequest: Encodable {
  let claims: [String: AnyCodable]
}

public struct MessageResponse: Codable {
  public let detail: String
}

private struct GoogleSignInRequest: Encodable {
  let id_token: String
}

private struct GithubSignInRequest: Encodable {
  let access_token: String
}

private struct SendPhoneOTPRequest: Encodable {
  let phone_number: String
}

private struct VerifyPhoneOTPRequest: Encodable {
  let phone_number: String
  let code: String
}

public struct EnrollTOTPResponse: Codable {
  public let totp_uri: String
  public let secret: String
}

private struct ConfirmTOTPRequest: Encodable {
  let code: String
}

private struct VerifyTOTPRequest: Encodable {
  let code: String
}

private struct EnrollSMSRequest: Encodable {
  let phone_number: String
}

private struct ConfirmSMSRequest: Encodable {
  let device_id: String
  let code: String
}

private struct VerifySMSRequest: Encodable {
  let device_id: String
  let code: String
}

private struct SendMagicLinkRequest: Encodable {
  let email: String
}

private struct VerifyMagicLinkRequest: Encodable {
  let token: String
}

private struct UpgradeAnonymousRequest: Encodable {
  let email: String
  let password: String
  let password2: String
}

private struct SetPasswordRequest: Encodable {
  let new_password: String
  let new_password2: String
  let current_password: String?
}

private struct LinkEmailRequest: Encodable {
  let email: String
  let password: String
}

private struct VerifyEmailChangeRequest: Encodable {
  let token: String
}

private struct IssueCustomTokenRequest: Encodable {
  let user_id: String
  let claims: [String: AnyCodable]?
}
