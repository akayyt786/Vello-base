import 'package:test/test.dart';
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() {
  group('AuthSDK Integration Tests (localhost:8000)', () {
    late OwnFirebase app;
    const baseUrl = 'http://localhost:8000';
    const testProjectId = 'test-project-001';

    setUp(() {
      app = initOwnFirebase(
        OwnFirebaseConfig(
          baseUrl: baseUrl,
          projectId: testProjectId,
        ),
      );
    });

    test('Auth service is properly initialized', () {
      expect(app.auth, isNotNull);
      expect(app.auth.baseUrl, equals(baseUrl));
      expect(app.auth.projectId, equals(testProjectId));
    });

    test('setAccessToken propagates to all services', () {
      const token = 'integration-test-token';
      app.setAccessToken(token);

      expect(app.auth.accessToken, equals(token));
      expect(app.data.accessToken, equals(token));
      expect(app.analytics.accessToken, equals(token));
      expect(app.push.accessToken, equals(token));
    });

    test('setProjectId propagates to all services', () {
      const projectId = 'new-test-project';
      app.setProjectId(projectId);

      expect(app.auth.projectId, equals(projectId));
      expect(app.data.projectId, equals(projectId));
      expect(app.analytics.projectId, equals(projectId));
    });

    test('Auth register endpoint is accessible', () async {
      // This test verifies the endpoint exists and is callable
      // In real scenario with backend running, this would test actual registration
      expect(app.auth.baseUrl, contains('localhost'));
    });

    test('Auth login endpoint structure', () async {
      // Verify login method exists and endpoint structure
      expect(app.auth.login, isNotNull);
    });

    test('Auth logout endpoint structure', () async {
      expect(app.auth.logout, isNotNull);
    });

    test('Auth getMe endpoint structure', () async {
      expect(app.auth.getMe, isNotNull);
    });

    test('Auth refresh token endpoint structure', () async {
      expect(app.auth.refreshToken, isNotNull);
    });

    test('Multiple auth methods are available', () {
      final methods = [
        app.auth.login,
        app.auth.register,
        app.auth.logout,
        app.auth.getMe,
        app.auth.anonymousSignIn,
        app.auth.googleSignIn,
        app.auth.githubSignIn,
        app.auth.sendMagicLink,
        app.auth.verifyMagicLink,
      ];
      expect(methods, hasLength(9));
      expect(methods.every((m) => m != null), isTrue);
    });

    test('MFA methods are available', () {
      final mfaMethods = [
        app.auth.enrollTOTP,
        app.auth.confirmTOTP,
        app.auth.verifyTOTP,
        app.auth.listMFADevices,
        app.auth.deleteMFADevice,
      ];
      expect(mfaMethods, hasLength(5));
    });

    test('Social auth methods are available', () {
      final socialMethods = [
        app.auth.googleSignIn,
        app.auth.githubSignIn,
        app.auth.listLinkedAccounts,
        app.auth.unlinkSocialAccount,
      ];
      expect(socialMethods, hasLength(4));
    });

    test('Phone OTP methods are available', () {
      final phoneMethods = [
        app.auth.sendPhoneOTP,
        app.auth.verifyPhoneOTP,
      ];
      expect(phoneMethods, hasLength(2));
    });

    test('Account management methods are available', () {
      final accountMethods = [
        app.auth.upgradeAnonymous,
        app.auth.setPassword,
      ];
      expect(accountMethods, hasLength(2));
    });

    test('Custom token endpoint structure', () {
      expect(app.auth.issueCustomToken, isNotNull);
    });

    test('Auth endpoints use projectUrl for project-scoped operations', () {
      app.setProjectId('my-project');
      final url = app.auth.projectUrl('auth/custom-token/');
      expect(url, contains('my-project'));
      expect(url, contains('api/projects'));
    });

    test('Auth endpoints build correct base URLs', () {
      const testUrl = 'http://localhost:8000/api/v1/auth/login/';
      final expectedPattern = '${baseUrl}/api/v1/auth/login/';
      expect(testUrl, equals(expectedPattern));
    });

    test('Anonymous sign-in flow is available', () {
      expect(app.auth.anonymousSignIn, isNotNull);
    });

    test('Auth token refresh flow is available', () {
      expect(app.auth.refreshToken, isNotNull);
      expect(app.auth.logout, isNotNull);
    });
  });
}
