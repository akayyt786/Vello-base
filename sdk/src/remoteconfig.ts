import { OwnFirebaseClient } from './client';
import type { RemoteConfigParameter, PaginatedResponse } from './types';

export interface ConfigCondition {
  id: string;
  name: string;
  expression: string;
  value: string;
}

export interface RemoteConfigCache {
  ttlMs: number;
  lastFetchTime?: number;
}

export class RemoteConfigSDK extends OwnFirebaseClient {
  private cache = new Map<string, { value: unknown; expiresAt: number }>();
  private cacheTtlMs = 3600000; // 1 hour default

  /**
   * Set the cache TTL (time-to-live) in milliseconds.
   * Default is 1 hour (3600000ms).
   */
  setCacheTTL(ttlMs: number): void {
    this.cacheTtlMs = ttlMs;
  }

  /**
   * Clear all cached remote config values.
   */
  clearCache(): void {
    this.cache.clear();
  }

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

  // ─── Fetch & Cache ───────────────────────────────────────────────────────────

  /**
   * Fetch all remote config parameters with built-in caching.
   * Results are cached for the configured TTL.
   * Pass `forceRefresh=true` to bypass cache.
   */
  async fetchAllParameters(
    forceRefresh = false
  ): Promise<RemoteConfigParameter[]> {
    const cacheKey = '__all_params__';

    // Check cache if not forcing refresh
    if (!forceRefresh) {
      const cached = this.cache.get(cacheKey);
      if (cached && cached.expiresAt > Date.now()) {
        return cached.value as RemoteConfigParameter[];
      }
    }

    // Fetch from server
    const response = await this.listParameters();
    const params = response.results || [];

    // Cache the result
    this.cache.set(cacheKey, {
      value: params,
      expiresAt: Date.now() + this.cacheTtlMs,
    });

    return params;
  }

  /**
   * Get a single parameter by key with caching.
   * Pass `forceRefresh=true` to bypass cache.
   */
  async getParameterByKey(
    key: string,
    forceRefresh = false
  ): Promise<RemoteConfigParameter | null> {
    const cacheKey = `param:${key}`;

    // Check cache if not forcing refresh
    if (!forceRefresh) {
      const cached = this.cache.get(cacheKey);
      if (cached && cached.expiresAt > Date.now()) {
        return cached.value as RemoteConfigParameter | null;
      }
    }

    try {
      // Fetch all and find by key (assuming no direct key lookup)
      const params = await this.fetchAllParameters(forceRefresh);
      const param = params.find(p => p.key === key) || null;

      // Cache the result
      this.cache.set(cacheKey, {
        value: param,
        expiresAt: Date.now() + this.cacheTtlMs,
      });

      return param;
    } catch (error) {
      return null;
    }
  }

  /**
   * Get parameter value by key, with type coercion.
   * Useful for strongly-typed config access.
   */
  async getConfigValue<T>(
    key: string,
    defaultValue?: T,
    forceRefresh = false
  ): Promise<T> {
    const param = await this.getParameterByKey(key, forceRefresh);

    if (!param || !param.default_value) {
      if (defaultValue !== undefined) {
        return defaultValue;
      }
      throw new Error(`Config key not found: ${key}`);
    }

    // Attempt to parse based on value_type
    try {
      switch (param.value_type) {
        case 'json':
          return JSON.parse(param.default_value) as T;
        case 'boolean':
          return (param.default_value === 'true' || param.default_value === '1') as T;
        case 'number':
          return Number(param.default_value) as T;
        case 'string':
        default:
          return param.default_value as T;
      }
    } catch (error) {
      if (defaultValue !== undefined) {
        return defaultValue;
      }
      throw new Error(`Failed to parse config value for key: ${key}`);
    }
  }

  /**
   * Clear expired cache entries.
   */
  pruneCache(): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (entry.expiresAt <= now) {
        this.cache.delete(key);
      }
    }
  }
}
