import { OwnFirebaseClient } from './client';
import type { RemoteConfigParameter, PaginatedResponse } from './types';

export interface ConfigCondition {
  id: string;
  name: string;
  expression: string;
  value: string;
}

export class RemoteConfigSDK extends OwnFirebaseClient {
  // ─── Parameters ──────────────────────────────────────────────────────────────

  async listParameters(): Promise<PaginatedResponse<RemoteConfigParameter>> {
    return this.request('GET', this.projectUrl('config/parameters/'));
  }

  async getParameter(id: string): Promise<RemoteConfigParameter> {
    return this.request('GET', this.projectUrl(`config/parameters/${id}/`));
  }

  async createParameter(
    parameter: Omit<RemoteConfigParameter, 'id'>
  ): Promise<RemoteConfigParameter> {
    return this.request('POST', this.projectUrl('config/parameters/'), parameter);
  }

  async updateParameter(
    id: string,
    updates: Partial<Omit<RemoteConfigParameter, 'id'>>
  ): Promise<RemoteConfigParameter> {
    return this.request(
      'PATCH',
      this.projectUrl(`config/parameters/${id}/`),
      updates
    );
  }

  async deleteParameter(id: string): Promise<void> {
    return this.request('DELETE', this.projectUrl(`config/parameters/${id}/`));
  }

  // ─── Conditions ──────────────────────────────────────────────────────────────

  async listConditions(configId: string): Promise<ConfigCondition[]> {
    return this.request(
      'GET',
      this.projectUrl(`config/parameters/${configId}/conditions/`)
    );
  }

  async createCondition(
    configId: string,
    condition: Omit<ConfigCondition, 'id'>
  ): Promise<ConfigCondition> {
    return this.request(
      'POST',
      this.projectUrl(`config/parameters/${configId}/conditions/`),
      condition
    );
  }

  async updateCondition(
    configId: string,
    conditionId: string,
    updates: Partial<Omit<ConfigCondition, 'id'>>
  ): Promise<ConfigCondition> {
    return this.request(
      'PATCH',
      this.projectUrl(`config/parameters/${configId}/conditions/${conditionId}/`),
      updates
    );
  }

  async deleteCondition(configId: string, conditionId: string): Promise<void> {
    return this.request(
      'DELETE',
      this.projectUrl(`config/parameters/${configId}/conditions/${conditionId}/`)
    );
  }
}
