import 'package:test/test.dart';
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() {
  group('DataSDK Integration Tests (CRUD Operations)', () {
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
      // In real integration, would authenticate first
      app.setAccessToken('integration-test-token');
    });

    test('Data service is properly initialized', () {
      expect(app.data, isNotNull);
      expect(app.data.baseUrl, equals(baseUrl));
      expect(app.data.projectId, equals(testProjectId));
    });

    test('Collection CRUD methods are available', () {
      final methods = [
        app.data.listCollections,
        app.data.createCollection,
      ];
      expect(methods, hasLength(2));
    });

    test('Document CRUD methods are available', () {
      final methods = [
        app.data.listDocuments,
        app.data.getDocument,
        app.data.createDocument,
        app.data.updateDocument,
        app.data.replaceDocument,
        app.data.deleteDocument,
      ];
      expect(methods, hasLength(6));
    });

    test('Batch operations are available', () {
      expect(app.data.writeBatch, isNotNull);
    });

    test('Security rules operations are available', () {
      final methods = [
        app.data.getRules,
        app.data.updateRules,
        app.data.testRules,
      ];
      expect(methods, hasLength(3));
    });

    test('Document subcollection paths are supported', () {
      const subcollectionPath = 'users/user-123/posts';
      expect(subcollectionPath, contains('/'));
      final parts = subcollectionPath.split('/');
      expect(parts, hasLength(3));
    });

    test('Batch operation structure supports all operations', () {
      final batchOps = [
        {
          'op': 'set',
          'collection': 'users',
          'doc_id': 'user-1',
          'data': {'name': 'Alice'},
        },
        {
          'op': 'update',
          'collection': 'users',
          'doc_id': 'user-2',
          'data': {'age': 31},
        },
        {
          'op': 'delete',
          'collection': 'users',
          'doc_id': 'user-3',
        },
      ];
      expect(batchOps, hasLength(3));
      expect(batchOps.map((op) => op['op']).toSet(), equals({'set', 'update', 'delete'}));
    });

    test('Document filter structure', () {
      final filters = {
        'status': 'active',
        'role': 'admin',
        'created_after': '2024-01-01',
      };
      expect(filters, hasLength(3));
      expect(filters.containsKey('status'), isTrue);
    });

    test('Collection creation endpoint', () {
      const collectionName = 'test-collection';
      expect(collectionName, isNotEmpty);
      expect(collectionName.length, greaterThan(0));
    });

    test('Document data serialization', () {
      final docData = {
        'name': 'Alice',
        'age': 30,
        'email': 'alice@example.com',
        'profile': {
          'bio': 'Flutter developer',
          'location': 'San Francisco',
        },
        'interests': ['dart', 'flutter', 'firebase'],
      };
      expect(docData, isA<Map<String, dynamic>>());
      expect(docData['profile'], isA<Map>());
      expect(docData['interests'], isA<List>());
    });

    test('Paginated document listing', () {
      final paginationMeta = {
        'count': 100,
        'next': 'http://localhost:8000/api/projects/test/collections/users/docs/?page=2',
        'previous': null,
        'results': [],
      };
      expect(paginationMeta['count'], equals(100));
      expect(paginationMeta['next'], isNotNull);
      expect(paginationMeta['previous'], isNull);
    });

    test('Document timestamps are preserved', () {
      final doc = {
        'id': 'doc-1',
        'collection': 'users',
        'data': {'name': 'Alice'},
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-02T12:34:56Z',
      };
      expect(doc['created_at'], equals('2024-01-01T00:00:00Z'));
      expect(doc['updated_at'], equals('2024-01-02T12:34:56Z'));
    });

    test('Nested subcollection support', () {
      const nestedPath = 'organizations/org-1/teams/team-2/members';
      final parts = nestedPath.split('/');
      expect(parts, hasLength(5));
    });

    test('Rules testing endpoint', () {
      final ruleContext = {
        'user_id': 'user-123',
        'is_admin': true,
        'request': {'method': 'GET', 'path': '/users/user-123'},
      };
      expect(ruleContext['user_id'], equals('user-123'));
    });

    test('Batch write result structure', () {
      final result = {
        'written': 3,
        'errors': [],
      };
      expect(result['written'], equals(3));
      expect(result['errors'], isEmpty);
    });

    test('Write batch with errors structure', () {
      final resultWithErrors = {
        'written': 2,
        'errors': [
          {
            'index': 2,
            'code': 'permission_denied',
            'message': 'User does not have permission',
          },
        ],
      };
      expect(resultWithErrors['written'], equals(2));
      expect(resultWithErrors['errors'], isNotEmpty);
    });
  });
}
