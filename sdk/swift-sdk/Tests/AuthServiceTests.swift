import XCTest
@testable import OwnFirebaseSDK

final class AuthServiceTests: XCTestCase {
  var firebase: OwnFirebase!
  var mockURLSession: URLSession!

  override func setUp() {
    super.setUp()
    URLProtocol.registerClass(MockURLProtocol.self)

    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [MockURLProtocol.self]
    mockURLSession = URLSession(configuration: config)

    firebase = OwnFirebase(
      config: OwnFirebaseConfig(
        baseUrl: "http://localhost:8000",
        projectId: "test-project",
        accessToken: nil
      )
    )
  }

  override func tearDown() {
    super.tearDown()
    URLProtocol.unregisterClass(MockURLProtocol.self)
    MockURLProtocol.mockData = nil
    MockURLProtocol.mockResponse = nil
    MockURLProtocol.mockError = nil
  }

  // MARK: - Registration Tests

  func testRegisterSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "user-123",
      email: "test@example.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/register/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.register(
      email: "test@example.com",
      password: "password123",
      username: "testuser"
    )

    XCTAssertEqual(result.access, "access-token")
    XCTAssertEqual(result.refresh, "refresh-token")
    XCTAssertEqual(result.user_id, "user-123")
    XCTAssertEqual(result.email, "test@example.com")
  }

  func testRegisterWithoutUsername() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "user-123",
      email: "test@example.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/register/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.register(
      email: "test@example.com",
      password: "password123"
    )

    XCTAssertEqual(result.access, "access-token")
    XCTAssertEqual(result.user_id, "user-123")
  }

  func testRegisterDuplicateEmail() async throws {
    let errorResponse = APIError(
      status: 400,
      message: "Email already exists"
    )

    let jsonData = try JSONEncoder().encode(errorResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/register/")!,
      statusCode: 400,
      httpVersion: nil,
      headerFields: nil
    )

    do {
      _ = try await firebase.auth.register(
        email: "existing@example.com",
        password: "password123"
      )
      XCTFail("Should throw error")
    } catch {
      XCTAssertTrue(error is OwnFirebaseError)
    }
  }

  // MARK: - Login Tests

  func testLoginSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "user-123",
      email: "test@example.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/login/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.login(
      email: "test@example.com",
      password: "password123"
    )

    XCTAssertEqual(result.access, "access-token")
    XCTAssertEqual(result.refresh, "refresh-token")
  }

  func testLoginInvalidCredentials() async throws {
    let errorResponse = APIError(
      status: 401,
      message: "Invalid credentials"
    )

    let jsonData = try JSONEncoder().encode(errorResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/login/")!,
      statusCode: 401,
      httpVersion: nil,
      headerFields: nil
    )

    do {
      _ = try await firebase.auth.login(
        email: "test@example.com",
        password: "wrongpassword"
      )
      XCTFail("Should throw error")
    } catch {
      XCTAssertTrue(error is OwnFirebaseError)
    }
  }

  // MARK: - Token Refresh Tests

  func testRefreshTokenSuccess() async throws {
    let expectedResponse = TokenRefreshResponse(access: "new-access-token")

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/refresh/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.refreshToken(
      refresh: "refresh-token"
    )

    XCTAssertEqual(result.access, "new-access-token")
  }

  func testRefreshTokenInvalidToken() async throws {
    let errorResponse = APIError(
      status: 401,
      message: "Invalid refresh token"
    )

    let jsonData = try JSONEncoder().encode(errorResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/refresh/")!,
      statusCode: 401,
      httpVersion: nil,
      headerFields: nil
    )

    do {
      _ = try await firebase.auth.refreshToken(
        refresh: "invalid-token"
      )
      XCTFail("Should throw error")
    } catch {
      XCTAssertTrue(error is OwnFirebaseError)
    }
  }

  // MARK: - Logout Tests

  func testLogoutSuccess() async throws {
    MockURLProtocol.mockData = Data()
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/logout/")!,
      statusCode: 204,
      httpVersion: nil,
      headerFields: nil
    )

    try await firebase.auth.logout(refresh: "refresh-token")
  }

  // MARK: - Anonymous Sign In Tests

  func testAnonymousSignInSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "anon-access-token",
      refresh: "anon-refresh-token",
      user_id: "anon-user-123",
      email: nil
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/anonymous-signin/")!,
      statusCode: 201,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.anonymousSignIn()

    XCTAssertEqual(result.access, "anon-access-token")
    XCTAssertNil(result.email)
  }

  // MARK: - Get Me Tests

  func testGetMeSuccess() async throws {
    let expectedUser = User(
      id: "user-123",
      email: "test@example.com",
      username: "testuser",
      first_name: "Test",
      last_name: "User",
      is_active: true
    )

    let jsonData = try JSONEncoder().encode(expectedUser)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/me/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.getMe()

    XCTAssertEqual(result.id, "user-123")
    XCTAssertEqual(result.email, "test@example.com")
    XCTAssertEqual(result.username, "testuser")
  }

  // MARK: - Social Auth Tests

  func testGoogleSignInSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "google-user-123",
      email: "user@gmail.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/social/google/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.googleSignIn(idToken: "google-id-token")

    XCTAssertEqual(result.access, "access-token")
    XCTAssertEqual(result.user_id, "google-user-123")
  }

  func testGithubSignInSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "github-user-123",
      email: "user@github.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/social/github/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.githubSignIn(accessToken: "github-token")

    XCTAssertEqual(result.access, "access-token")
    XCTAssertEqual(result.user_id, "github-user-123")
  }

  func testListLinkedAccounts() async throws {
    let expectedAccounts = [
      LinkedSocialAccount(
        id: "account-1",
        provider: "google",
        provider_uid: "google-123",
        email: "user@gmail.com",
        linked_at: "2024-01-01T00:00:00Z"
      )
    ]

    let jsonData = try JSONEncoder().encode(expectedAccounts)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/social/linked/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.listLinkedAccounts()

    XCTAssertEqual(result.count, 1)
    XCTAssertEqual(result[0].provider, "google")
  }

  func testUnlinkSocialAccount() async throws {
    MockURLProtocol.mockData = Data()
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/social/linked/account-1/")!,
      statusCode: 204,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    try await firebase.auth.unlinkSocialAccount("account-1")
  }

  // MARK: - MFA Tests

  func testEnrollTOTPSuccess() async throws {
    let expectedResponse = EnrollTOTPResponse(
      device_id: "device-1",
      secret: "ABCD1234",
      provisioning_uri: "otpauth://totp/test@example.com"
    )

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/mfa/enroll/totp/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.enrollTOTP()

    XCTAssertEqual(result.secret, "ABCD1234")
    XCTAssertEqual(result.device_id, "device-1")
    XCTAssertTrue(result.provisioning_uri.contains("otpauth"))
  }

  func testConfirmTOTPSuccess() async throws {
    let expectedResponse = MessageResponse(detail: "TOTP confirmed")

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/mfa/confirm/totp/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.confirmTOTP(deviceId: "device-1", code: "123456")

    XCTAssertEqual(result.detail, "TOTP confirmed")
  }

  func testVerifyTOTPSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "user-123",
      email: "test@example.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/mfa/verify/totp/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.verifyTOTP(deviceId: "device-1", code: "123456")

    XCTAssertEqual(result.access, "access-token")
  }

  func testListMFADevices() async throws {
    let expectedDevices = [
      MFADevice(
        id: "device-1",
        type: "totp",
        name: "My Phone",
        confirmed: true,
        created_at: "2024-01-01T00:00:00Z"
      )
    ]

    let jsonData = try JSONEncoder().encode(expectedDevices)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/mfa/devices/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.listMFADevices()

    XCTAssertEqual(result.count, 1)
    XCTAssertEqual(result[0].type, "totp")
  }

  func testDeleteMFADevice() async throws {
    MockURLProtocol.mockData = Data()
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/mfa/devices/device-1/")!,
      statusCode: 204,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    try await firebase.auth.deleteMFADevice("device-1")
  }

  // MARK: - Magic Link Tests

  func testSendMagicLinkSuccess() async throws {
    let expectedResponse = MessageResponse(detail: "Magic link sent")

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/magic-link/send/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.sendMagicLink(email: "test@example.com")

    XCTAssertEqual(result.detail, "Magic link sent")
  }

  func testVerifyMagicLinkSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "user-123",
      email: "test@example.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/magic-link/verify/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.verifyMagicLink(token: "magic-token")

    XCTAssertEqual(result.access, "access-token")
  }

  // MARK: - Account Management Tests

  func testSetPasswordSuccess() async throws {
    let expectedResponse = MessageResponse(detail: "Password updated")

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/set-password/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.setPassword(
      newPassword: "newpass123",
      newPassword2: "newpass123"
    )

    XCTAssertEqual(result.detail, "Password updated")
  }

  func testUpgradeAnonymousSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "new-access-token",
      refresh: "new-refresh-token",
      user_id: "user-123",
      email: "test@example.com"
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/upgrade/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("anon-token")
    let result = try await firebase.auth.upgradeAnonymous(
      email: "test@example.com",
      password: "password123",
      password2: "password123"
    )

    XCTAssertEqual(result.email, "test@example.com")
  }

  func testLinkEmailSuccess() async throws {
    let expectedResponse = MessageResponse(detail: "Email linked")

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/link-email/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.linkEmail(
      email: "newemail@example.com",
      password: "password123"
    )

    XCTAssertEqual(result.detail, "Email linked")
  }

  // MARK: - Phone OTP Tests

  func testSendPhoneOTPSuccess() async throws {
    let expectedResponse = MessageResponse(detail: "OTP sent")

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/phone/send-otp/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.sendPhoneOTP(phoneNumber: "+1234567890")

    XCTAssertEqual(result.detail, "OTP sent")
  }

  func testVerifyPhoneOTPSuccess() async throws {
    let expectedTokens = AuthTokens(
      access: "access-token",
      refresh: "refresh-token",
      user_id: "user-123",
      email: nil
    )

    let jsonData = try JSONEncoder().encode(expectedTokens)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/phone/verify-otp/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    let result = try await firebase.auth.verifyPhoneOTP(
      phoneNumber: "+1234567890",
      code: "123456"
    )

    XCTAssertEqual(result.access, "access-token")
  }

  // MARK: - Custom Token Tests

  func testIssueCustomTokenSuccess() async throws {
    let expectedToken = CustomToken(custom_token: "custom-token-jwt")

    let jsonData = try JSONEncoder().encode(expectedToken)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/projects/test-project/auth/custom-token/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.issueCustomToken(
      userId: "user-123",
      claims: ["role": AnyCodable("admin")]
    )

    XCTAssertEqual(result.custom_token, "custom-token-jwt")
  }

  // MARK: - Set Custom Claims Tests

  func testSetCustomClaimsSuccess() async throws {
    let expectedResponse = MessageResponse(detail: "Claims set")

    let jsonData = try JSONEncoder().encode(expectedResponse)
    MockURLProtocol.mockData = jsonData
    MockURLProtocol.mockResponse = HTTPURLResponse(
      url: URL(string: "http://localhost:8000/api/v1/auth/set-custom-claims/")!,
      statusCode: 200,
      httpVersion: nil,
      headerFields: nil
    )

    firebase.setAccessToken("valid-token")
    let result = try await firebase.auth.setCustomClaims(["role": AnyCodable("admin")])

    XCTAssertEqual(result.detail, "Claims set")
  }
}

// MARK: - Mock URL Protocol

class MockURLProtocol: URLProtocol {
  static var mockData: Data?
  static var mockResponse: HTTPURLResponse?
  static var mockError: Error?

  override class func canInit(with request: URLRequest) -> Bool {
    return true
  }

  override class func canonicalRequest(for request: URLRequest) -> URLRequest {
    return request
  }

  override func startLoading() {
    if let error = MockURLProtocol.mockError {
      client?.urlProtocol(self, didFailWithError: error)
    } else if let response = MockURLProtocol.mockResponse {
      client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
      client?.urlProtocol(self, didLoad: MockURLProtocol.mockData ?? Data())
      client?.urlProtocolDidFinishLoading(self)
    }
  }

  override func stopLoading() {}
}
