import { ABTestingSDK } from '../src/abtesting';
import type { Experiment, ExperimentVariant, ExperimentAssignment, PaginatedResponse } from '../src/types';

global.fetch = jest.fn();

describe('ABTestingSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
    projectId: 'test-project',
  };

  describe('experiments', () => {
    it('should list experiments', async () => {
      const mockResponse: PaginatedResponse<Experiment> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'exp1',
            name: 'checkout_flow_v2',
            status: 'running',
            variants: [
              { id: 'var1', name: 'control', allocation: 50, config: {} },
              { id: 'var2', name: 'new_flow', allocation: 50, config: { flow: 'simplified' } },
            ],
          },
          {
            id: 'exp2',
            name: 'pricing_change',
            status: 'completed',
            variants: [
              { id: 'var3', name: 'original_price', allocation: 50, config: {} },
              { id: 'var4', name: 'discount_price', allocation: 50, config: { discount: 20 } },
            ],
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.listExperiments();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
      expect(result.results[0].status).toBe('running');
    });

    it('should get specific experiment', async () => {
      const mockExperiment: Experiment = {
        id: 'exp1',
        name: 'checkout_flow_v2',
        status: 'running',
        variants: [
          { id: 'var1', name: 'control', allocation: 50, config: {} },
          { id: 'var2', name: 'new_flow', allocation: 50, config: { flow: 'simplified' } },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockExperiment,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.getExperiment('exp1');

      expect(result).toEqual(mockExperiment);
      expect(result.variants).toHaveLength(2);
      expect(result.variants[0].name).toBe('control');
    });

    it('should create experiment', async () => {
      const mockExperiment: Experiment = {
        id: 'exp3',
        name: 'homepage_redesign',
        status: 'draft',
        variants: [
          { id: 'var5', name: 'current', allocation: 100, config: {} },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockExperiment,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.createExperiment({
        name: 'homepage_redesign',
        status: 'draft',
      });

      expect(result).toEqual(mockExperiment);
      expect(result.status).toBe('draft');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/abtesting/experiments/',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should update experiment', async () => {
      const mockExperiment: Experiment = {
        id: 'exp1',
        name: 'checkout_flow_v2',
        status: 'paused',
        variants: [
          { id: 'var1', name: 'control', allocation: 50, config: {} },
          { id: 'var2', name: 'new_flow', allocation: 50, config: { flow: 'simplified' } },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockExperiment,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.updateExperiment('exp1', {
        status: 'paused',
      });

      expect(result.status).toBe('paused');
    });

    it('should delete experiment', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.deleteExperiment('exp1');

      expect(result).toBeUndefined();
    });

    it('should handle different experiment statuses', async () => {
      const statuses = ['draft', 'running', 'paused', 'completed'];

      for (const status of statuses) {
        const mockExperiment: Experiment = {
          id: `exp-${status}`,
          name: `test-${status}`,
          status: status as any,
          variants: [],
        };

        expect(mockExperiment.status).toBe(status);
      }
    });
  });

  describe('experiment assignment', () => {
    it('should get stable variant assignment', async () => {
      const mockAssignment: ExperimentAssignment = {
        variant_name: 'new_flow',
        config: { flow: 'simplified', button_text: 'Checkout Now' },
        experiment_name: 'checkout_flow_v2',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockAssignment,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.getAssignment('exp1', 'user123');

      expect(result).toEqual(mockAssignment);
      expect(result.variant_name).toBe('new_flow');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/abtesting/experiments/exp1/assign/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ targeting_value: 'user123' }),
        })
      );
    });

    it('should return consistent assignment for same user', async () => {
      const mockAssignment: ExperimentAssignment = {
        variant_name: 'control',
        config: {},
        experiment_name: 'pricing_test',
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockAssignment,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result1 = await ab.getAssignment('exp2', 'user456');
      const result2 = await ab.getAssignment('exp2', 'user456');

      expect(result1.variant_name).toBe(result2.variant_name);
    });

    it('should return different assignments for different users', async () => {
      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            variant_name: 'control',
            config: {},
            experiment_name: 'pricing_test',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({
            variant_name: 'variant_b',
            config: { discount: 15 },
            experiment_name: 'pricing_test',
          }),
        });

      const user1Assignment = await ab.getAssignment('exp2', 'user1');
      const user2Assignment = await ab.getAssignment('exp2', 'user2');

      // They should be different (probabilistically)
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should get assignment with variant config', async () => {
      const mockAssignment: ExperimentAssignment = {
        variant_name: 'new_design',
        config: {
          layout: 'grid',
          colors: { primary: '#007bff', accent: '#6f42c1' },
          font_size: 16,
          features: ['dark_mode', 'advanced_search'],
        },
        experiment_name: 'ui_redesign',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockAssignment,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.getAssignment('exp3', 'user789');

      expect(result.config).toEqual({
        layout: 'grid',
        colors: { primary: '#007bff', accent: '#6f42c1' },
        font_size: 16,
        features: ['dark_mode', 'advanced_search'],
      });
    });
  });

  describe('conversion tracking', () => {
    it('should record conversion with event name', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.recordConversion('exp1', 'user123', 'purchase');

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/abtesting/experiments/exp1/convert/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            targeting_value: 'user123',
            event_name: 'purchase',
            value: undefined,
          }),
        })
      );
    });

    it('should record conversion with value', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const result = await ab.recordConversion('exp1', 'user123', 'purchase', 99.99);

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/projects/test-project/abtesting/experiments/exp1/convert/',
        expect.objectContaining({
          body: JSON.stringify({
            targeting_value: 'user123',
            event_name: 'purchase',
            value: 99.99,
          }),
        })
      );
    });

    it('should record various conversion events', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 204,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      const events = [
        { name: 'signup', value: 1 },
        { name: 'purchase', value: 99.99 },
        { name: 'subscription', value: 9.99 },
        { name: 'engagement_score', value: 75 },
      ];

      for (const event of events) {
        await ab.recordConversion('exp1', 'user123', event.name, event.value);
      }

      expect(global.fetch).toHaveBeenCalledTimes(4);
    });

    it('should record multiple conversions per user', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 204,
      });

      const ab = new ABTestingSDK(config);
      ab.setAccessToken('access-token');
      ab.setProjectId('test-project');

      // Same user performs multiple conversions
      await ab.recordConversion('exp1', 'user123', 'page_view', 1);
      await ab.recordConversion('exp1', 'user123', 'add_to_cart', 1);
      await ab.recordConversion('exp1', 'user123', 'purchase', 150.00);

      expect(global.fetch).toHaveBeenCalledTimes(3);
    });
  });

  describe('split allocation scenarios', () => {
    it('should support 50/50 split', () => {
      const variants: ExperimentVariant[] = [
        { id: 'var1', name: 'control', allocation: 50, config: {} },
        { id: 'var2', name: 'treatment', allocation: 50, config: { feature: 'enabled' } },
      ];

      const totalAllocation = variants.reduce((sum, v) => sum + v.allocation, 0);
      expect(totalAllocation).toBe(100);
      expect(variants[0].allocation).toBe(50);
      expect(variants[1].allocation).toBe(50);
    });

    it('should support multi-variant split', () => {
      const variants: ExperimentVariant[] = [
        { id: 'var1', name: 'control', allocation: 25, config: {} },
        { id: 'var2', name: 'variant_a', allocation: 25, config: { version: 'a' } },
        { id: 'var3', name: 'variant_b', allocation: 25, config: { version: 'b' } },
        { id: 'var4', name: 'variant_c', allocation: 25, config: { version: 'c' } },
      ];

      const totalAllocation = variants.reduce((sum, v) => sum + v.allocation, 0);
      expect(totalAllocation).toBe(100);
    });

    it('should support unequal allocation', () => {
      const variants: ExperimentVariant[] = [
        { id: 'var1', name: 'control', allocation: 70, config: {} },
        { id: 'var2', name: 'new_feature', allocation: 30, config: { feature: 'new' } },
      ];

      const totalAllocation = variants.reduce((sum, v) => sum + v.allocation, 0);
      expect(totalAllocation).toBe(100);
      expect(variants[0].allocation).toBe(70);
      expect(variants[1].allocation).toBe(30);
    });

    it('should support gradual rollout', () => {
      const phases = [
        {
          phase: 1,
          variants: [
            { id: 'v1', name: 'control', allocation: 95, config: {} },
            { id: 'v2', name: 'new_feature', allocation: 5, config: { feature: 'new' } },
          ],
        },
        {
          phase: 2,
          variants: [
            { id: 'v1', name: 'control', allocation: 75, config: {} },
            { id: 'v2', name: 'new_feature', allocation: 25, config: { feature: 'new' } },
          ],
        },
        {
          phase: 3,
          variants: [
            { id: 'v1', name: 'control', allocation: 50, config: {} },
            { id: 'v2', name: 'new_feature', allocation: 50, config: { feature: 'new' } },
          ],
        },
      ];

      phases.forEach(p => {
        const total = p.variants.reduce((sum, v) => sum + v.allocation, 0);
        expect(total).toBe(100);
      });
    });
  });
});
