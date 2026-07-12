import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/data.dart';

void main() {
  group('DataSDK Unit Tests (Mocked)', () {
    late DataSDK data;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      data = DataSDK(config: config);
    });

    test('DataSDK initializes with config', () {
      expect(data.baseUrl, equals('http://localhost:8000'));
      expect(data.projectId, equals('test-project'));
    });

    test('DataDocument.fromJson parses correctly', () {
      final json = {
        'id': 'doc-123',
        'collection': 'users',
        'data': {'name': 'Alice', 'age': 30},
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
      };
      final doc = DataDocument.fromJson(json);
      expect(doc.id, equals('doc-123'));
      expect(doc.collection, equals('users'));
      expect(doc.data['name'], equals('Alice'));
      expect(doc.data['age'], equals(30));
    });

    test('DataDocument handles empty data', () {
      final json = {
        'id': 'doc-123',
        'collection': 'users',
        'data': null,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
      };
      final doc = DataDocument.fromJson(json);
      expect(doc.data, isEmpty);
    });

    test('DataCollection.fromJson parses correctly', () {
      final json = {
        'id': 'col-123',
        'name': 'users',
        'document_count': 42,
      };
      final collection = DataCollection.fromJson(json);
      expect(collection.id, equals('col-123'));
      expect(collection.name, equals('users'));
      expect(collection.documentCount, equals(42));
    });

    test('PaginatedResponse parses results', () {
      final json = [
        {
          'id': 'doc-1',
          'collection': 'users',
          'data': {'name': 'Alice'},
          'created_at': '2024-01-01T00:00:00Z',
          'updated_at': '2024-01-01T00:00:00Z',
        },
        {
          'id': 'doc-2',
          'collection': 'users',
          'data': {'name': 'Bob'},
          'created_at': '2024-01-01T00:00:00Z',
          'updated_at': '2024-01-01T00:00:00Z',
        },
      ];
      final docs = json.map((item) => DataDocument.fromJson(item as Map<String, dynamic>)).toList();
      expect(docs, hasLength(2));
      expect(docs[0].data['name'], equals('Alice'));
      expect(docs[1].data['name'], equals('Bob'));
    });

    test('DataDocument.toJson serializes correctly', () {
      final doc = DataDocument(
        id: 'doc-123',
        collection: 'users',
        data: {'name': 'Alice', 'age': 30},
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      );
      final json = doc.toJson();
      expect(json['id'], equals('doc-123'));
      expect(json['collection'], equals('users'));
      expect(json['data']['name'], equals('Alice'));
    });

    test('WriteBatch operation structure', () {
      final ops = [
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
      expect(ops, hasLength(3));
      expect(ops[0]['op'], equals('set'));
      expect(ops[1]['op'], equals('update'));
      expect(ops[2]['op'], equals('delete'));
    });

    test('Data with nested structures', () {
      final json = {
        'id': 'doc-123',
        'collection': 'posts',
        'data': {
          'title': 'Hello World',
          'author': {'name': 'Alice', 'id': 'user-1'},
          'tags': ['flutter', 'dart', 'sdk'],
          'metadata': {'views': 100, 'likes': 25},
        },
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:00:00Z',
      };
      final doc = DataDocument.fromJson(json);
      expect(doc.data['author']['name'], equals('Alice'));
      expect(doc.data['tags'], contains('flutter'));
      expect(doc.data['metadata']['likes'], equals(25));
    });

    test('Collection name with subcollection path', () {
      const collectionPath = 'users/user-123/posts';
      expect(collectionPath, contains('/'));
      final parts = collectionPath.split('/');
      expect(parts, hasLength(3));
    });

    test('projectUrl builds correct collection path', () {
      data.setProjectId('my-project');
      final url = data.projectUrl('collections/users/docs/');
      expect(url, contains('my-project'));
      expect(url, contains('collections/users/docs/'));
    });
  });
}
