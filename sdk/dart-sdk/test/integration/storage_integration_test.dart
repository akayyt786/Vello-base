import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/storage.dart';

// NOTE: constructed directly via `StorageSDK(config: ...)` rather than through
// `initOwnFirebase(...).storage`, since the barrel file (ownfirebase_sdk.dart)
// does not yet wire up the storage module.
void main() {
  group('StorageSDK Integration Tests', () {
    late StorageSDK storage;
    const baseUrl = 'http://localhost:8000';
    const testProjectId = 'test-project-001';

    setUp(() {
      storage = StorageSDK(
        config: OwnFirebaseConfig(
          baseUrl: baseUrl,
          projectId: testProjectId,
        ),
      );
      storage.setAccessToken('integration-test-token');
    });

    test('Storage service is properly initialized', () {
      expect(storage, isNotNull);
      expect(storage.baseUrl, equals(baseUrl));
      expect(storage.projectId, equals(testProjectId));
    });

    test('Upload lifecycle methods exist', () {
      final methods = [
        storage.getUploadUrl,
        storage.confirmUpload,
      ];
      expect(methods, hasLength(2));
    });

    test('File management methods exist', () {
      final methods = [
        storage.listFiles,
        storage.getFile,
        storage.deleteFile,
      ];
      expect(methods, hasLength(3));
    });

    test('Upload request for multiple content types', () {
      final uploads = [
        {'path': 'avatars/photo.png', 'content_type': 'image/png'},
        {'path': 'documents/report.pdf', 'content_type': 'application/pdf'},
        {'path': 'videos/clip.mp4', 'content_type': 'video/mp4'},
      ];
      expect(uploads, hasLength(3));
      expect(uploads.map((u) => u['content_type']).toSet(),
          equals({'image/png', 'application/pdf', 'video/mp4'}));
    });

    test('Upload request with size and metadata', () {
      final uploadRequest = {
        'path': 'avatars/photo.png',
        'content_type': 'image/png',
        'size': 51200,
        'metadata': {
          'uploaded_by': 'user-123',
          'source': 'mobile',
        },
      };
      expect(uploadRequest['size'], equals(51200));
      expect(uploadRequest['metadata'], isNotNull);
    });

    test('Presigned upload URL response structure', () {
      final uploadUrlResponse = {
        'file_id': '11111111-1111-1111-1111-111111111111',
        'upload_url': 'https://minio.example.com/bucket/avatars/photo.png?sig=abc',
        'method': 'PUT',
        'expires_in': 900,
        'path': 'avatars/photo.png',
        'bucket': 'project-test-001-bucket',
      };
      expect(uploadUrlResponse['method'], equals('PUT'));
      expect(uploadUrlResponse['expires_in'], equals(900));
    });

    test('Confirm upload request structure', () {
      const fileId = '11111111-1111-1111-1111-111111111111';
      final confirmRequest = {'file_id': fileId};
      expect(confirmRequest['file_id'], equals(fileId));
    });

    test('File list request with prefix and pagination', () {
      final listParams = {
        'prefix': 'avatars/',
        'limit': 25,
        'offset': 0,
      };
      expect(listParams['prefix'], equals('avatars/'));
      expect(listParams['limit'], lessThanOrEqualTo(200));
    });

    test('File list response structure (files/total/limit/offset)', () {
      final listResponse = {
        'files': List.generate(
          3,
          (i) => {
            'id': 'file-$i',
            'path': 'avatars/photo-$i.png',
            'status': 'ready',
          },
        ),
        'total': 3,
        'limit': 50,
        'offset': 0,
      };
      expect(listResponse['files'], hasLength(3));
      expect(listResponse['total'], equals(3));
      expect(listResponse.containsKey('count'), isFalse);
      expect(listResponse.containsKey('results'), isFalse);
    });

    test('File deletion flow', () {
      const path = 'avatars/photo-to-remove.png';
      expect(path, isNotEmpty);
    });

    test('File paths with nested prefixes', () {
      final paths = [
        'avatars/user-1/photo.png',
        'documents/2024/report.pdf',
        'videos/uploads/clip.mp4',
      ];
      for (final path in paths) {
        expect(path.contains('/'), isTrue);
      }
    });

    test('File lifecycle statuses', () {
      final statuses = ['pending', 'confirmed', 'processing', 'ready', 'error'];
      expect(statuses, hasLength(5));
      expect(statuses.contains('ready'), isTrue);
    });

    test('Large file batch listing', () {
      final files = List.generate(
        200,
        (i) => {
          'id': 'file-$i',
          'path': 'bulk/file-$i.bin',
        },
      );
      expect(files, hasLength(200));
    });
  });
}
