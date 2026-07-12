import 'client.dart';
import 'types.dart';

/// A/B Testing SDK for OwnFirebase
class ABTestingSDK extends OwnFirebaseClient {
  ABTestingSDK({required OwnFirebaseConfig config}) : super(config: config);

  // ─── Experiments ──────────────────────────────────────────────────────────────

  Future<List<Map<String, dynamic>>> listExperiments() async {
    return request<List<Map<String, dynamic>>>(
      'GET',
      projectUrl('experiments/'),
      null,
      fromJson: (json) {
        final list = json as List;
        return list.map((item) => item as Map<String, dynamic>).toList();
      },
    );
  }

  Future<Map<String, dynamic>> getExperiment(String experimentId) async {
    return request<Map<String, dynamic>>(
      'GET',
      projectUrl('experiments/$experimentId/'),
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Assignment ───────────────────────────────────────────────────────────────

  Future<ExperimentAssignment> getAssignment(
    String experimentId,
    String userId,
  ) async {
    return request<ExperimentAssignment>(
      'POST',
      projectUrl('experiments/$experimentId/assign/'),
      {'user_id': userId},
      fromJson: (json) => ExperimentAssignment.fromJson(json as Map<String, dynamic>),
    );
  }

  // ─── Conversion ────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> recordConversion(
    String experimentId,
    String userId, {
    Map<String, dynamic>? metadata,
  }) async {
    return request<Map<String, dynamic>>(
      'POST',
      projectUrl('experiments/$experimentId/convert/'),
      {
        'user_id': userId,
        if (metadata != null) 'metadata': metadata,
      },
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }

  // ─── Results ───────────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> getResults(String experimentId) async {
    return request<Map<String, dynamic>>(
      'GET',
      projectUrl('experiments/$experimentId/results/'),
      null,
      fromJson: (json) => json as Map<String, dynamic>,
    );
  }
}
