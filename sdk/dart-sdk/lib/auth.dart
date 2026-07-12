import 'client.dart';
import 'types.dart';

/// Authentication SDK for OwnFirebase
class AuthSDK extends OwnFirebaseClient {
  AuthSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Core Auth ───────────────────────────────────────────────────────────────

  Future<AuthTokens> register(
    String email,
    String password, {
    String? username,
  }) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/register/',
      {
        'email': email,
        'password': password,
        if (username != null) 'username': username,
      },
      noAuth: true,
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<AuthTokens> login(String email, String password) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/login/',
      {
        'email': email,
        'password': password,
      },
      noAuth: true,
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<Map<String, String>> refreshToken(String refresh) async {
    return request<Map<String, String>>(
      'POST',
      '$baseUrl/api/v1/auth/refresh/',
      {'refresh': refresh},
      noAuth: true,
      fromJson: (json) => Map<String, String>.from(json as Map),
    );
  }

  Future<void> logout(String refresh) async {
    return request<void>(
      'POST',
      '$baseUrl/api/v1/auth/logout/',
      {'refresh': refresh},
      fromJson: (_) => null,
    );
  }

  Future<User> getMe() async {
    return request<User>(
      'GET',
      '$baseUrl/api/v1/auth/me/',
      null,
      fromJson: (json) => User.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<AuthTokens> anonymousSignIn() async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/anonymous-signin/',
      {},
      noAuth: true,
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<Map<String, dynamic>> setCustomClaims(Map<String, dynamic> claims) async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/auth/set-custom-claims/',
      {'claims': claims},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Social Auth ─────────────────────────────────────────────────────────────

  Future<AuthTokens> googleSignIn(String idToken) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/social/google/',
      {'id_token': idToken},
      noAuth: true,
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<AuthTokens> githubSignIn(String accessToken) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/social/github/',
      {'access_token': accessToken},
      noAuth: true,
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<List<LinkedSocialAccount>> listLinkedAccounts() async {
    return request<List<LinkedSocialAccount>>(
      'GET',
      '$baseUrl/api/v1/auth/social/linked/',
      null,
      fromJson: (json) {
        final list = json as List;
        return list
            .map((item) => LinkedSocialAccount.fromJson(item as Map<String, dynamic>))
            .toList();
      },
    );
  }

  Future<void> unlinkSocialAccount(String accountId) async {
    return request<void>(
      'DELETE',
      '$baseUrl/api/v1/auth/social/linked/$accountId/',
      null,
      fromJson: (_) => null,
    );
  }

  // ─── Phone / OTP ─────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> sendPhoneOTP(String phoneNumber) async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/auth/phone/send-otp/',
      {'phone_number': phoneNumber},
      noAuth: true,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  Future<AuthTokens> verifyPhoneOTP(String phoneNumber, String otpCode) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/phone/verify-otp/',
      {'phone_number': phoneNumber, 'otp_code': otpCode},
      noAuth: true,
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── MFA ─────────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> enrollTOTP() async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/auth/mfa/enroll/totp/',
      {},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  /// Confirms and activates a TOTP device enrolled via [enrollTOTP].
  ///
  /// [deviceId] is the MFA device `id` returned by [enrollTOTP]
  /// (`enhanced_auth/serializers.py`'s `ConfirmTOTPSerializer` requires both
  /// `device_id` and `totp_code`).
  Future<Map<String, dynamic>> confirmTOTP(String deviceId, String totpCode) async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/auth/mfa/confirm/totp/',
      {'device_id': deviceId, 'totp_code': totpCode},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  /// Verifies a TOTP code for an already-confirmed device (e.g. during login).
  ///
  /// [deviceId] identifies which enrolled MFA device the code is for
  /// (`enhanced_auth/serializers.py`'s `VerifyTOTPSerializer` requires both
  /// `device_id` and `totp_code`).
  Future<AuthTokens> verifyTOTP(String deviceId, String totpCode) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/mfa/verify/totp/',
      {'device_id': deviceId, 'totp_code': totpCode},
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<List<MFADevice>> listMFADevices() async {
    return request<List<MFADevice>>(
      'GET',
      '$baseUrl/api/v1/auth/mfa/devices/',
      null,
      fromJson: (json) {
        final list = json as List;
        return list.map((item) => MFADevice.fromJson(item as Map<String, dynamic>)).toList();
      },
    );
  }

  Future<void> deleteMFADevice(String deviceId) async {
    return request<void>(
      'DELETE',
      '$baseUrl/api/v1/auth/mfa/devices/$deviceId/',
      null,
      fromJson: (_) => null,
    );
  }

  // ─── Magic Link ───────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> sendMagicLink(String email) async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/auth/magic-link/send/',
      {'email': email},
      noAuth: true,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  Future<AuthTokens> verifyMagicLink(String token) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/magic-link/verify/',
      {'token': token},
      noAuth: true,
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Account Management ───────────────────────────────────────────────────────

  Future<AuthTokens> upgradeAnonymous(
    String email,
    String password,
    String password2,
  ) async {
    return request<AuthTokens>(
      'POST',
      '$baseUrl/api/v1/auth/upgrade/',
      {
        'email': email,
        'password': password,
        'password2': password2,
      },
      fromJson: (json) => AuthTokens.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<Map<String, dynamic>> setPassword(
    String newPassword,
    String newPassword2, {
    String? currentPassword,
  }) async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/auth/set-password/',
      {
        'new_password': newPassword,
        'new_password2': newPassword2,
        if (currentPassword != null) 'current_password': currentPassword,
      },
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  /// Issue a custom server-signed token for [uid] with arbitrary [claims],
  /// for exchanging a project's own user identifiers for an OwnFirebase
  /// session (mirrors Firebase Admin's `createCustomToken`). Requires
  /// editor/owner role on the project. Returns `{token, expires_at}`.
  Future<Map<String, dynamic>> issueCustomToken(
    String uid,
    Map<String, dynamic> claims,
  ) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('auth/custom-token/'),
      {'uid': uid, 'claims': claims},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }
}
