import { OwnFirebaseClient } from './client';
import type {
  Experiment,
  ExperimentVariant,
  ExperimentAssignment,
  PaginatedResponse,
} from './types';

export class ABTestingSDK extends OwnFirebaseClient {
  // ─── Experiments ─────────────────────────────────────────────────────────────

  async listExperiments(): Promise<PaginatedResponse<Experiment>> {
    return this.request('GET', this.projectUrl('abtesting/experiments/'));
  }

  async getExperiment(id: string): Promise<Experiment> {
    return this.request('GET', this.projectUrl(`abtesting/experiments/${id}/`));
  }

  async createExperiment(
    experiment: Omit<Experiment, 'id' | 'variants'>
  ): Promise<Experiment> {
    return this.request(
      'POST',
      this.projectUrl('abtesting/experiments/'),
      experiment
    );
  }

  async updateExperiment(
    id: string,
    updates: Partial<Omit<Experiment, 'id' | 'variants'>>
  ): Promise<Experiment> {
    return this.request(
      'PATCH',
      this.projectUrl(`abtesting/experiments/${id}/`),
      updates
    );
  }

  async deleteExperiment(id: string): Promise<void> {
    return this.request(
      'DELETE',
      this.projectUrl(`abtesting/experiments/${id}/`)
    );
  }

  // ─── Assignment & Conversion ─────────────────────────────────────────────────

  /**
   * Get a stable variant assignment for the given targeting value (e.g. user ID).
   * The server uses consistent hashing so the same value always maps to the same variant.
   */
  async getAssignment(
    experimentId: string,
    targetingValue: string
  ): Promise<ExperimentAssignment> {
    return this.request(
      'POST',
      this.projectUrl(`abtesting/experiments/${experimentId}/assign/`),
      { targeting_value: targetingValue }
    );
  }

  async recordConversion(
    experimentId: string,
    targetingValue: string,
    eventName: string,
    value?: number
  ): Promise<void> {
    return this.request(
      'POST',
      this.projectUrl(`abtesting/experiments/${experimentId}/convert/`),
      { targeting_value: targetingValue, event_name: eventName, value }
    );
  }
}
