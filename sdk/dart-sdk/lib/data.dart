import 'client.dart';
import 'types.dart';

/// Data management SDK for OwnFirebase (Firestore-like)
class DataSDK extends OwnFirebaseClient {
  DataSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Collections ─────────────────────────────────────────────────────────────

  Future<List<DataCollection>> listCollections() async {
    return request<List<DataCollection>>(
      'GET',
      projectUrl('collections/'),
      null,
      fromJson: (json) {
        final list = json as List;
        return list
            .map((item) => DataCollection.fromJson(item as Map<String, dynamic>))
            .toList();
      },
    );
  }

  Future<DataCollection> createCollection(String name) async {
    return request<DataCollection>(
      'POST',
      projectUrl('collections/'),
      {'name': name},
      fromJson: (json) => DataCollection.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Documents ────────────────────────────────────────────────────────────────

  /// List documents in a collection. Supports subcollection paths using forward slashes
  /// (e.g. "users/uid/posts")
  Future<PaginatedResponse<DataDocument>> listDocuments(
    String collection, {
    Map<String, String>? filters,
  }) async {
    final response = await request<Map<String, dynamic>>(
      'GET',
      projectUrl('collections/$collection/docs/'),
      null,
      query: filters ?? {},
      fromJson: (json) => json as Map<String, dynamic>,
    );

    final results = (response['results'] as List?)
            ?.map((item) => DataDocument.fromJson(item as Map<String, dynamic>))
            .toList() ??
        [];

    return PaginatedResponse(
      count: response['count'] as int? ?? 0,
      next: response['next'] as String?,
      previous: response['previous'] as String?,
      results: results,
    );
  }

  Future<DataDocument> getDocument(String collection, String docId) async {
    return request<DataDocument>(
      'GET',
      projectUrl('collections/$collection/docs/$docId/'),
      null,
      fromJson: (json) => DataDocument.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<DataDocument> createDocument(
    String collection,
    Map<String, dynamic> data,
  ) async {
    return request<DataDocument>(
      'POST',
      projectUrl('collections/$collection/docs/'),
      {'data': data},
      fromJson: (json) => DataDocument.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<DataDocument> updateDocument(
    String collection,
    String docId,
    Map<String, dynamic> data,
  ) async {
    return request<DataDocument>(
      'PATCH',
      projectUrl('collections/$collection/docs/$docId/'),
      {'data': data},
      fromJson: (json) => DataDocument.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<DataDocument> replaceDocument(
    String collection,
    String docId,
    Map<String, dynamic> data,
  ) async {
    return request<DataDocument>(
      'PUT',
      projectUrl('collections/$collection/docs/$docId/'),
      {'data': data},
      fromJson: (json) => DataDocument.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<void> deleteDocument(String collection, String docId) async {
    return request<void>(
      'DELETE',
      projectUrl('collections/$collection/docs/$docId/'),
      null,
      fromJson: (_) => null,
    );
  }

  // ─── Batch Operations ─────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> writeBatch(List<Map<String, dynamic>> operations) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('transaction/'),
      {'operations': operations},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Security Rules ───────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getRules() async {
    return request<Map<String, dynamic>>(
      'GET',
      '$baseUrl/api/v1/rules/',
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> updateRules(String rules) async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/rules/',
      {'rules': rules},
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> testRules(
    String rule,
    Map<String, dynamic> context,
  ) async {
    return request<Map<String, dynamic>>(
      'POST',
      '$baseUrl/api/v1/rules/test/',
      {
        'rule': rule,
        'context': context,
      },
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }
}
