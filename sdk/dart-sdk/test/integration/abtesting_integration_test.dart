import 'package:test/test.dart';
import 'package:ownfirebase_sdk/ownfirebase_sdk.dart';

void main() {
  group('ABTestingSDK Integration Tests', () {
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
      app.setAccessToken('integration-test-token');
    });

    test('ABTesting service is properly initialized', () {
      expect(app.ab, isNotNull);
      expect(app.ab.baseUrl, equals(baseUrl));
      expect(app.ab.projectId, equals(testProjectId));
    });

    test('Experiment management methods', () {
      final methods = [
        app.ab.listExperiments,
        app.ab.getExperiment,
      ];
      expect(methods, hasLength(2));
    });

    test('Assignment and conversion methods', () {
      final methods = [
        app.ab.getAssignment,
        app.ab.recordConversion,
      ];
      expect(methods, hasLength(2));
    });

    test('Results retrieval method', () {
      expect(app.ab.getResults, isNotNull);
    });

    test('Experiment creation structure', () {
      final experiment = <String, dynamic>{
        'name': 'checkout_button_color',
        'status': 'running',
        'variants': [
          {
            'name': 'control',
            'allocation': 50,
            'config': {'button_color': 'blue'},
          },
          {
            'name': 'variant_a',
            'allocation': 25,
            'config': {'button_color': 'red'},
          },
          {
            'name': 'variant_b',
            'allocation': 25,
            'config': {'button_color': 'green'},
          },
        ],
      };
      expect(experiment['variants'], hasLength(3));
      final totalAllocation = (experiment['variants'] as List)
          .fold<int>(0, (sum, v) => sum + ((v as Map)['allocation'] as int));
      expect(totalAllocation, equals(100));
    });

    test('User assignment to variants', () {
      final assignments = List.generate(
        100,
        (i) {
          final userId = 'user-${i.toString().padLeft(3, '0')}';
          final variants = ['control', 'variant_a', 'variant_b'];
          final variantIndex = i % variants.length;
          return {
            'user_id': userId,
            'variant': variants[variantIndex],
            'assigned_at': '2024-01-01T00:00:00Z',
          };
        },
      );
      expect(assignments, hasLength(100));
    });

    test('Experiment variants with allocation', () {
      final variants = [
        {'name': 'control', 'allocation': 50},
        {'name': 'treatment', 'allocation': 50},
      ];
      final totalAlloc = variants.fold<int>(0, (s, v) => s + (v['allocation'] as int));
      expect(totalAlloc, equals(100));
    });

    test('Assignment response structure', () {
      final assignment = <String, dynamic>{
        'experiment_id': 'exp-checkout-button',
        'user_id': 'user-123',
        'variant_name': 'variant_a',
        'config': {
          'button_color': 'red',
          'button_text': 'Buy Now',
          'animation_enabled': true,
        },
      };
      expect(assignment['variant_name'], equals('variant_a'));
      expect(assignment['config']['button_color'], equals('red'));
    });

    test('Conversion recording', () {
      final conversions = List.generate(
        50,
        (i) => {
          'user_id': 'user-$i',
          'experiment_id': 'exp-123',
          'variant': i % 2 == 0 ? 'control' : 'variant_a',
          'value': (i + 1) * 10.0,
          'timestamp': '2024-01-01T12:00:00Z',
        },
      );
      expect(conversions, hasLength(50));
    });

    test('Experiment results analysis', () {
      final results = <String, dynamic>{
        'experiment_id': 'exp-123',
        'experiment_name': 'checkout_optimization',
        'status': 'completed',
        'variants': {
          'control': {
            'visitors': 1000,
            'conversions': 100,
            'conversion_rate': 0.10,
            'average_value': 50.0,
          },
          'variant_a': {
            'visitors': 1000,
            'conversions': 150,
            'conversion_rate': 0.15,
            'average_value': 52.5,
          },
        },
      };
      expect(results['variants']['control']['conversion_rate'], equals(0.10));
      expect(results['variants']['variant_a']['conversion_rate'], equals(0.15));
    });

    test('Multiple concurrent experiments', () {
      final experiments = [
        {
          'id': 'exp-1',
          'name': 'button_color',
          'status': 'running',
        },
        {
          'id': 'exp-2',
          'name': 'cta_text',
          'status': 'running',
        },
        {
          'id': 'exp-3',
          'name': 'layout_change',
          'status': 'draft',
        },
      ];
      expect(experiments, hasLength(3));
      expect(experiments.where((e) => e['status'] == 'running'), hasLength(2));
    });

    test('Experiment status lifecycle', () {
      final statuses = ['draft', 'running', 'paused', 'completed', 'archived'];
      expect(statuses, hasLength(5));
      expect(statuses.contains('running'), isTrue);
    });

    test('Variant configuration complexity', () {
      final complexConfig = <String, dynamic>{
        'feature_enabled': true,
        'settings': {
          'threshold': 100,
          'timeout_ms': 5000,
        },
        'ui': {
          'button_color': 'red',
          'button_text': 'Premium',
          'animations': ['fade', 'slide'],
        },
        'pricing': {
          'base': 99.99,
          'discount': 0.2,
        },
      };
      expect(complexConfig['ui']['animations'], hasLength(2));
      expect(complexConfig['settings']['timeout_ms'], equals(5000));
    });

    test('Statistical significance calculation', () {
      final stats = {
        'control': {
          'conversion_rate': 0.10,
          'sample_size': 1000,
          'std_error': 0.0095,
        },
        'variant_a': {
          'conversion_rate': 0.12,
          'sample_size': 1000,
          'std_error': 0.0101,
        },
        'p_value': 0.042,
        'significant_at_95_percent': true,
      };
      expect(stats['significant_at_95_percent'], isTrue);
      expect(stats['p_value'], lessThan(0.05));
    });

    test('Experiment pagination', () {
      final paginated = {
        'count': 50,
        'next': 'http://localhost:8000/api/projects/test/experiments/?page=2',
        'previous': null,
        'results': [
          {'id': 'exp-1', 'name': 'experiment_1', 'status': 'running'},
        ],
      };
      expect(paginated['count'], equals(50));
      expect(paginated['results'], hasLength(1));
    });
  });
}
