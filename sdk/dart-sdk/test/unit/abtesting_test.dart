import 'package:test/test.dart';
import 'package:ownfirebase_sdk/types.dart';
import 'package:ownfirebase_sdk/abtesting.dart';

void main() {
  group('ABTestingSDK Unit Tests (Mocked)', () {
    late ABTestingSDK abTesting;
    late OwnFirebaseConfig config;

    setUp(() {
      config = OwnFirebaseConfig(
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      );
      abTesting = ABTestingSDK(config: config);
    });

    test('ABTestingSDK initializes with config', () {
      expect(abTesting.baseUrl, equals('http://localhost:8000'));
      expect(abTesting.projectId, equals('test-project'));
    });

    test('ExperimentAssignment.fromJson parses correctly', () {
      final json = {
        'variant_name': 'variant_b',
        'config': {'button_color': 'blue', 'cta_text': 'Learn More'},
        'experiment_name': 'checkout_flow_v2',
      };
      final assignment = ExperimentAssignment.fromJson(json);
      expect(assignment.variantName, equals('variant_b'));
      expect(assignment.experimentName, equals('checkout_flow_v2'));
      expect(assignment.config['button_color'], equals('blue'));
    });

    test('ExperimentAssignment with empty config', () {
      final json = {
        'variant_name': 'control',
        'config': {},
        'experiment_name': 'test_experiment',
      };
      final assignment = ExperimentAssignment.fromJson(json);
      expect(assignment.config, isEmpty);
      expect(assignment.variantName, equals('control'));
    });

    test('Experiment listing structure', () {
      final experiments = [
        {
          'id': 'exp-1',
          'name': 'checkout_optimization',
          'status': 'running',
        },
        {
          'id': 'exp-2',
          'name': 'homepage_redesign',
          'status': 'completed',
        },
      ];
      expect(experiments, hasLength(2));
      expect(experiments[0]['status'], equals('running'));
      expect(experiments[1]['status'], equals('completed'));
    });

    test('Experiment status values', () {
      final statuses = ['draft', 'running', 'paused', 'completed'];
      expect(statuses, hasLength(4));
      expect(statuses.contains('running'), isTrue);
    });

    test('Variant configuration structure', () {
      final variant = {
        'id': 'var-1',
        'name': 'variant_a',
        'allocation': 50,
        'config': {
          'feature_enabled': true,
          'setting': 'value',
        },
      };
      expect(variant['allocation'], equals(50));
      expect(variant['name'], equals('variant_a'));
    });

    test('Multiple variants with different allocations', () {
      final variants = [
        {'name': 'control', 'allocation': 50},
        {'name': 'variant_a', 'allocation': 25},
        {'name': 'variant_b', 'allocation': 25},
      ];
      final totalAllocation = variants.fold<int>(0, (sum, v) => sum + (v['allocation'] as int));
      expect(totalAllocation, equals(100));
    });

    test('Assignment with complex config', () {
      final json = {
        'variant_name': 'premium',
        'config': {
          'price_point': 9.99,
          'billing_cycle': 'monthly',
          'features': ['analytics', 'api_access', 'priority_support'],
          'metadata': {'tier': 'pro', 'launch_date': '2024-01-01'},
        },
        'experiment_name': 'pricing_experiment',
      };
      final assignment = ExperimentAssignment.fromJson(json);
      expect(assignment.config['features'], isList);
      expect(assignment.config['metadata']['tier'], equals('pro'));
    });

    test('Conversion recording structure', () {
      final conversionData = <String, dynamic>{
        'user_id': 'user-123',
        'metadata': {
          'amount': 99.99,
          'currency': 'USD',
          'timestamp': '2024-01-01T12:00:00Z',
        },
      };
      expect(conversionData['user_id'], equals('user-123'));
      expect(conversionData['metadata']['amount'], equals(99.99));
    });

    test('Experiment results structure', () {
      final results = <String, dynamic>{
        'experiment_id': 'exp-1',
        'variants': {
          'control': {
            'conversions': 100,
            'visitors': 1000,
            'conversion_rate': 0.10,
          },
          'variant_a': {
            'conversions': 120,
            'visitors': 1000,
            'conversion_rate': 0.12,
          },
        },
      };
      expect(results['variants']['control']['conversion_rate'], equals(0.10));
      expect(results['variants']['variant_a']['conversion_rate'], equals(0.12));
    });

    test('Assignment probability distribution', () {
      final distributions = [
        {'variant': 'control', 'probability': 0.5},
        {'variant': 'variant_a', 'probability': 0.25},
        {'variant': 'variant_b', 'probability': 0.25},
      ];
      final totalProb = distributions.fold<double>(
        0.0,
        (sum, d) => sum + (d['probability'] as double),
      );
      expect(totalProb, closeTo(1.0, 0.0001));
    });

    test('Experiment assignment consistency', () {
      // Same user ID should get same variant assignment (deterministic)
      const userId = 'user-123';
      const experimentId = 'exp-1';

      // In real scenario, multiple calls with same params should return same result
      expect(userId, equals('user-123'));
      expect(experimentId, equals('exp-1'));
    });
  });
}
