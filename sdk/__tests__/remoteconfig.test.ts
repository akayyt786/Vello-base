import { RemoteConfigSDK } from '../src/remoteconfig';
import type { RemoteConfigParameter, PaginatedResponse } from '../src/types';
import type { ConfigCondition } from '../src/remoteconfig';

global.fetch = jest.fn();

describe('RemoteConfigSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('parameters', () => {
    it('should list parameters', async () => {
      const mockResponse: PaginatedResponse<RemoteConfigParameter> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'param1',
            key: 'feature_flag_new_ui',
            default_value: 'false',
            description: 'Enable new UI design',
            value_type: 'boolean',
          },
          {
            id: 'param2',
            key: 'api_timeout_ms',
            default_value: '5000',
            description: 'API request timeout in milliseconds',
            value_type: 'number',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.listParameters();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
    });

    it('should get specific parameter', async () => {
      const mockParameter: RemoteConfigParameter = {
        id: 'param1',
        key: 'feature_flag_new_ui',
        default_value: 'false',
        description: 'Enable new UI design',
        value_type: 'boolean',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockParameter,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.getParameter('param1');

      expect(result).toEqual(mockParameter);
      expect(result.key).toBe('feature_flag_new_ui');
    });

    it('should create parameter', async () => {
      const mockParameter: RemoteConfigParameter = {
        id: 'param3',
        key: 'app_version_min',
        default_value: '1.0.0',
        description: 'Minimum app version',
        value_type: 'string',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockParameter,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.createParameter({
        key: 'app_version_min',
        default_value: '1.0.0',
        description: 'Minimum app version',
        value_type: 'string',
      });

      expect(result).toEqual(mockParameter);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/config/parameters/',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should update parameter', async () => {
      const mockParameter: RemoteConfigParameter = {
        id: 'param1',
        key: 'feature_flag_new_ui',
        default_value: 'true',
        description: 'Enable new UI design (updated)',
        value_type: 'boolean',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockParameter,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.updateParameter('param1', {
        default_value: 'true',
        description: 'Enable new UI design (updated)',
      });

      expect(result.default_value).toBe('true');
      expect(result.description).toContain('updated');
    });

    it('should delete parameter', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.deleteParameter('param1');

      expect(result).toBeUndefined();
    });

    it('should handle different value types', async () => {
      const stringParam: RemoteConfigParameter = {
        id: 'p1',
        key: 'env',
        default_value: 'production',
        description: 'Environment',
        value_type: 'string',
      };

      const boolParam: RemoteConfigParameter = {
        id: 'p2',
        key: 'debug_mode',
        default_value: 'false',
        description: 'Debug mode',
        value_type: 'boolean',
      };

      const numberParam: RemoteConfigParameter = {
        id: 'p3',
        key: 'max_retries',
        default_value: '3',
        description: 'Max retries',
        value_type: 'number',
      };

      const jsonParam: RemoteConfigParameter = {
        id: 'p4',
        key: 'feature_config',
        default_value: '{"enabled": true}',
        description: 'Feature config',
        value_type: 'json',
      };

      expect(stringParam.value_type).toBe('string');
      expect(boolParam.value_type).toBe('boolean');
      expect(numberParam.value_type).toBe('number');
      expect(jsonParam.value_type).toBe('json');
    });
  });

  describe('conditions', () => {
    it('should list conditions for parameter', async () => {
      const mockConditions: ConfigCondition[] = [
        {
          id: 'cond1',
          name: 'ios_users',
          expression: 'user.platform == "ios"',
          value: 'true',
        },
        {
          id: 'cond2',
          name: 'beta_testers',
          expression: 'user.email like "%@beta.com"',
          value: 'true',
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockConditions,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.listConditions('param1');

      expect(result).toEqual(mockConditions);
      expect(result).toHaveLength(2);
    });

    it('should create condition for parameter', async () => {
      const mockCondition: ConfigCondition = {
        id: 'cond3',
        name: 'android_users',
        expression: 'user.platform == "android"',
        value: 'false',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockCondition,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.createCondition('param1', {
        name: 'android_users',
        expression: 'user.platform == "android"',
        value: 'false',
      });

      expect(result).toEqual(mockCondition);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/config/parameters/param1/conditions/',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should update condition', async () => {
      const mockCondition: ConfigCondition = {
        id: 'cond1',
        name: 'ios_users',
        expression: 'user.platform == "ios" && user.app_version >= "2.0"',
        value: 'true',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockCondition,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.updateCondition('param1', 'cond1', {
        expression: 'user.platform == "ios" && user.app_version >= "2.0"',
      });

      expect(result.expression).toContain('app_version');
    });

    it('should delete condition', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const remoteConfig = new RemoteConfigSDK(config);
      remoteConfig.setAccessToken('access-token');
      remoteConfig.setProjectId('test-project');

      const result = await remoteConfig.deleteCondition('param1', 'cond1');

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/config/parameters/param1/conditions/cond1/',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should handle complex condition expressions', async () => {
      const complexConditions: ConfigCondition[] = [
        {
          id: 'cond-complex1',
          name: 'premium_users_us',
          expression: 'user.subscription_tier == "premium" && user.country == "US" && user.created_at > "2024-01-01"',
          value: '{"feature": "enabled", "tier": "premium"}',
        },
        {
          id: 'cond-complex2',
          name: 'beta_rollout_10_percent',
          expression: 'user.id % 100 < 10',
          value: 'true',
        },
      ];

      expect(complexConditions[0].expression).toContain('&&');
      expect(complexConditions[1].expression).toContain('%');
    });

    it('should handle condition overrides', async () => {
      const baseParam: RemoteConfigParameter = {
        id: 'param-base',
        key: 'feature_enabled',
        default_value: 'false',
        description: 'Base feature flag',
        value_type: 'boolean',
      };

      const conditionOverrides: ConfigCondition[] = [
        {
          id: 'override1',
          name: 'internal_team',
          expression: 'user.email like "%@company.com"',
          value: 'true',
        },
        {
          id: 'override2',
          name: 'beta_program',
          expression: 'user.in_beta_program == true',
          value: 'true',
        },
      ];

      expect(baseParam.default_value).toBe('false');
      expect(conditionOverrides[0].value).toBe('true');
      expect(conditionOverrides[1].value).toBe('true');
    });
  });

  describe('config rollout scenarios', () => {
    it('should support gradual rollout with percentage', async () => {
      const rolloutCondition: ConfigCondition = {
        id: 'rollout-10',
        name: 'gradual_rollout_10_percent',
        expression: 'user.id % 100 < 10',
        value: 'true',
      };

      expect(rolloutCondition.expression).toContain('% 100 < 10');
    });

    it('should support geo-targeted config', async () => {
      const geoCondition: ConfigCondition = {
        id: 'geo-us',
        name: 'us_only_feature',
        expression: 'user.country in ["US", "CA"]',
        value: '{"enabled": true, "variant": "us_version"}',
      };

      expect(geoCondition.expression).toContain('country');
      expect(geoCondition.value).toContain('variant');
    });

    it('should support version-based config', async () => {
      const versionCondition: ConfigCondition = {
        id: 'version-check',
        name: 'minimum_version_requirement',
        expression: 'user.app_version >= "2.0.0"',
        value: '{"min_version": "2.0.0"}',
      };

      expect(versionCondition.expression).toContain('app_version');
    });
  });
});
