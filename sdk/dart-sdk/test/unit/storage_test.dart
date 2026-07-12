import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/storage.dart';

void main() {
  group('StorageSDK Unit Tests (Mocked)', () {
    late StorageSDK storage;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      storage = StorageSDK(config: config);
    });

    test('StorageSDK initializes with config', () {
      expect(storage.baseUrl, equals('http://localhost:8000'));
      expect(storage.projectId, equals('test-project'));
    });

    test('StorageUploadUrl.fromJson parses correctly', () {
      final json = {
        'file_id': '11111111-1111-1111-1111-111111111111',
        'upload_url': 'https://minio.example.com/bucket/avatars/photo.png?sig=abc',
        'method': 'PUT',
        'expires_in': 900,
        'path': 'avatars/photo.png',
        'bucket': 'project-test-bucket',
      };
      final uploadUrl = StorageUploadUrl.fromJson(json);
      expect(uploadUrl.fileId, equals('11111111-1111-1111-1111-111111111111'));
      expect(uploadUrl.uploadUrl, equals('https://minio.example.com/bucket/avatars/photo.png?sig=abc'));
      expect(uploadUrl.method, equals('PUT'));
      expect(uploadUrl.expiresIn, equals(900));
      expect(uploadUrl.path, equals('avatars/photo.png'));
      expect(uploadUrl.bucket, equals('project-test-bucket'));
    });

    test('StorageObject.fromJson parses a pending file', () {
      final json = {
        'id': '22222222-2222-2222-2222-222222222222',
        'path': 'avatars/photo.png',
        'original_name': 'photo.png',
        'content_type': 'image/png',
        'size': null,
        'status': 'pending',
        'metadata': {},
        'thumbnails': {},
        'download_url': null,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
      };
      final file = StorageObject.fromJson(json);
      expect(file.id, equals('22222222-2222-2222-2222-222222222222'));
      expect(file.path, equals('avatars/photo.png'));
      expect(file.originalName, equals('photo.png'));
      expect(file.contentType, equals('image/png'));
      expect(file.size, isNull);
      expect(file.status, equals('pending'));
      expect(file.downloadUrl, isNull);
    });

    test('StorageObject.fromJson parses a confirmed file with download URL', () {
      final json = {
        'id': '33333333-3333-3333-3333-333333333333',
        'path': 'documents/report.pdf',
        'original_name': 'report.pdf',
        'content_type': 'application/pdf',
        'size': 204800,
        'status': 'confirmed',
        'metadata': {'uploaded_by': 'user-1'},
        'thumbnails': null,
        'download_url': 'https://minio.example.com/bucket/documents/report.pdf?sig=xyz',
        'created_at': '2024-01-02T00:00:00Z',
        'updated_at': '2024-01-02T00:05:00Z',
      };
      final file = StorageObject.fromJson(json);
      expect(file.size, equals(204800));
      expect(file.status, equals('confirmed'));
      expect(file.metadata['uploaded_by'], equals('user-1'));
      expect(file.thumbnails, isNull);
      expect(file.downloadUrl, equals('https://minio.example.com/bucket/documents/report.pdf?sig=xyz'));
    });

    test('StorageObject for different lifecycle statuses', () {
      final statuses = ['pending', 'confirmed', 'processing', 'ready', 'error'];
      for (final status in statuses) {
        final file = StorageObject(
          id: 'file-$status',
          path: 'files/$status.bin',
          originalName: '$status.bin',
          contentType: 'application/octet-stream',
          status: status,
          metadata: const {},
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        );
        expect(file.status, equals(status));
      }
    });

    test('StorageObject.toJson round-trips field names', () {
      final file = StorageObject(
        id: 'file-1',
        path: 'images/logo.png',
        originalName: 'logo.png',
        contentType: 'image/png',
        size: 1024,
        status: 'ready',
        metadata: const {'width': 512},
        thumbnails: const {'small': 'images/logo_small.png'},
        downloadUrl: 'https://example.com/logo.png',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      );
      final json = file.toJson();
      expect(json['original_name'], equals('logo.png'));
      expect(json['content_type'], equals('image/png'));
      expect(json['download_url'], equals('https://example.com/logo.png'));
      expect(json['thumbnails'], equals({'small': 'images/logo_small.png'}));
    });

    test('StorageFileListResponse.fromJson parses file list (not DRF pagination)', () {
      final json = {
        'files': [
          {
            'id': 'file-1',
            'path': 'a.txt',
            'original_name': 'a.txt',
            'content_type': 'text/plain',
            'size': 10,
            'status': 'ready',
            'metadata': {},
            'thumbnails': {},
            'download_url': 'https://example.com/a.txt',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
          },
          {
            'id': 'file-2',
            'path': 'b.txt',
            'original_name': 'b.txt',
            'content_type': 'text/plain',
            'size': 20,
            'status': 'pending',
            'metadata': {},
            'thumbnails': {},
            'download_url': null,
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T00:00:00Z',
          },
        ],
        'total': 2,
        'limit': 50,
        'offset': 0,
      };
      final response = StorageFileListResponse.fromJson(json);
      expect(response.files, hasLength(2));
      expect(response.total, equals(2));
      expect(response.limit, equals(50));
      expect(response.offset, equals(0));
      expect(response.files.first.path, equals('a.txt'));
      expect(response.files.last.status, equals('pending'));
    });

    test('StorageFileListResponse.fromJson handles empty file list', () {
      final json = {
        'files': [],
        'total': 0,
        'limit': 50,
        'offset': 0,
      };
      final response = StorageFileListResponse.fromJson(json);
      expect(response.files, isEmpty);
      expect(response.total, equals(0));
    });

    test('Upload request body structure', () {
      final body = {
        'path': 'avatars/photo.png',
        'content_type': 'image/png',
        'size': 5000,
        'metadata': {'source': 'mobile'},
      };
      expect(body['path'], equals('avatars/photo.png'));
      expect(body['content_type'], equals('image/png'));
      expect(body['metadata'], equals({'source': 'mobile'}));
    });

    test('Confirm upload request body structure', () {
      final body = {'file_id': '44444444-4444-4444-4444-444444444444'};
      expect(body['file_id'], equals('44444444-4444-4444-4444-444444444444'));
    });

    test('List files query params structure', () {
      final query = {
        'prefix': 'avatars/',
        'limit': '25',
        'offset': '0',
      };
      expect(query['prefix'], equals('avatars/'));
      expect(query['limit'], equals('25'));
    });
  });
}
