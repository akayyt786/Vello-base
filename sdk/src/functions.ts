import { OwnFirebaseClient } from './client';
import type { FunctionDefinition, FunctionInvocation, FunctionLog } from './types';

export class FunctionsSDK extends OwnFirebaseClient {
  async listFunctions(): Promise<FunctionDefinition[]> {
    return this.request('GET', this.projectUrl('functions/'));
  }

  async getFunction(name: string): Promise<FunctionDefinition> {
    return this.request('GET', this.projectUrl(`functions/${name}/`));
  }

  async createFunction(
    definition: Omit<FunctionDefinition, 'id'>
  ): Promise<FunctionDefinition> {
    return this.request('POST', this.projectUrl('functions/'), definition);
  }

  async updateFunction(
    name: string,
    updates: Partial<Omit<FunctionDefinition, 'id' | 'name'>>
  ): Promise<FunctionDefinition> {
    return this.request('PATCH', this.projectUrl(`functions/${name}/`), updates);
  }

  async deleteFunction(name: string): Promise<void> {
    return this.request('DELETE', this.projectUrl(`functions/${name}/`));
  }

  async invoke(
    name: string,
    payload?: Record<string, unknown>
  ): Promise<FunctionInvocation> {
    return this.request('POST', this.projectUrl(`functions/${name}/invoke/`), {
      payload: payload ?? {},
    });
  }

  async getLogs(
    name: string,
    options?: { limit?: number; since?: string }
  ): Promise<FunctionLog[]> {
    const query: Record<string, string> = {};
    if (options?.limit !== undefined) query['limit'] = String(options.limit);
    if (options?.since) query['since'] = options.since;
    return this.request(
      'GET',
      this.projectUrl(`functions/${name}/logs/`),
      undefined,
      { query }
    );
  }
}
