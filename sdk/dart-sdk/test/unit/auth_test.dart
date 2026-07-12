import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/auth.dart';

void main() {
  group('AuthSDK Unit Tests (Mocked)', () {
    late AuthSDK auth;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      auth = AuthSDK(config: config);
    });

    test('AuthSDK initializes with config', () {
      expect(auth.baseUrl, equals('http://localhost:8000'));
      expect(auth.projectId, equals('test-project'));
    });

    test('setAccessToken updates token', () {
      const token = 'test-token-123';
      auth.setAccessToken(token);
      expect(auth.accessToken, equals(token));
    });

    test('setProjectId updates project ID', () {
      const projectId = 'new-project';
      auth.setProjectId(projectId);
      expect(auth.projectId, equals(projectId));
    });

    test('projectUrl throws when projectId not set', () {
      final authNoProject = AuthSDK(config: OwnFirebaseConfig(baseUrl: 'http://localhost:8000'));
      expect(() => authNoProject.projectUrl('test'), throwsException);
    });

    test('projectUrl builds correct path with projectId', () {
      const projectId = 'my-project';
      auth.setProjectId(projectId);
      final url = auth.projectUrl('auth/custom-token/');
      expect(url, contains(projectId));
      expect(url, contains('auth/custom-token/'));
    });

    test('AuthTokens.fromJson parses correctly', () {
      final json = {
        'access': 'access-token',
        'refresh': 'refresh-token',
        'user_id': 'user-123',
        'email': 'user@example.com',
      };
      final tokens = AuthTokens.fromJson(json);
      expect(tokens.access, equals('access-token'));
      expect(tokens.refresh, equals('refresh-token'));
      expect(tokens.userId, equals('user-123'));
      expect(tokens.email, equals('user@example.com'));
    });

    test('AuthTokens.toJson serializes correctly', () {
      final tokens = AuthTokens(
        access: 'access-token',
        refresh: 'refresh-token',
        userId: 'user-123',
        email: 'user@example.com',
      );
      final json = tokens.toJson();
      expect(json['access'], equals('access-token'));
      expect(json['refresh'], equals('refresh-token'));
      expect(json['user_id'], equals('user-123'));
      expect(json['email'], equals('user@example.com'));
    });

    test('User.fromJson parses correctly', () {
      final json = {
        'id': 'user-123',
        'email': 'user@example.com',
        'username': 'testuser',
        'first_name': 'Test',
        'last_name': 'User',
        'is_active': true,
      };
      final user = User.fromJson(json);
      expect(user.id, equals('user-123'));
      expect(user.email, equals('user@example.com'));
      expect(user.username, equals('testuser'));
      expect(user.firstName, equals('Test'));
      expect(user.lastName, equals('User'));
      expect(user.isActive, isTrue);
    });

    test('MFADevice.fromJson parses correctly', () {
      final json = {
        'id': 'device-123',
        'type': 'totp',
        'name': 'My Authenticator',
        'confirmed': true,
        'created_at': '2024-01-01T00:00:00Z',
      };
      final device = MFADevice.fromJson(json);
      expect(device.id, equals('device-123'));
      expect(device.type, equals('totp'));
      expect(device.name, equals('My Authenticator'));
      expect(device.confirmed, isTrue);
    });

    test('LinkedSocialAccount.fromJson parses correctly', () {
      final json = {
        'id': 'social-123',
        'provider': 'google',
        'provider_uid': 'google-user-id',
        'email': 'user@gmail.com',
        'linked_at': '2024-01-01T00:00:00Z',
      };
      final account = LinkedSocialAccount.fromJson(json);
      expect(account.id, equals('social-123'));
      expect(account.provider, equals('google'));
      expect(account.providerUid, equals('google-user-id'));
      expect(account.email, equals('user@gmail.com'));
    });

    test('APIError has correct toString', () {
      final error = APIError(
        status: 401,
        message: 'Unauthorized',
        detail: {'code': 'invalid_token'},
      );
      expect(error.toString(), contains('401'));
      expect(error.toString(), contains('Unauthorized'));
    });

    test('baseUrl removes trailing slash', () {
      final configWithSlash = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000/',
        projectId: 'test-project',
      );
      final authWithSlash = AuthSDK(config: configWithSlash);
      expect(authWithSlash.baseUrl, equals('http://localhost:8000'));
    });

    test('AuthTokens handles missing optional fields', () {
      final json = {
        'access': 'access-token',
        'refresh': 'refresh-token',
        'user_id': 'user-123',
      };
      final tokens = AuthTokens.fromJson(json);
      expect(tokens.email, isNull);
    });
  });
}
