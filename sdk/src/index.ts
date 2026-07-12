import type { OwnFirebaseConfig } from './types';
import { AuthSDK } from './auth';
import { DataSDK } from './data';
import { FunctionsSDK } from './functions';
import { StorageSDK } from './storage';
import { PushSDK } from './push';
import { AnalyticsSDK } from './analytics';
import { CrashlyticsSDK } from './crashlytics';
import { RemoteConfigSDK } from './remoteconfig';
import { RealtimeSDK } from './realtime';
import { ABTestingSDK } from './abtesting';
import { AISDK } from './ai';
import { ProjectsSDK } from './projects';
import { AppCheckSDK } from './appcheck';

// Re-export all types
export * from './types';

// Re-export utilities
export * from './errors';
export { SessionManager } from './session';
export type { SessionOptions } from './session';

// Re-export individual SDK classes for tree-shaking / direct instantiation
export {
  AuthSDK,
  DataSDK,
  FunctionsSDK,
  StorageSDK,
  PushSDK,
  AnalyticsSDK,
  CrashlyticsSDK,
  RemoteConfigSDK,
  RealtimeSDK,
  ABTestingSDK,
  AISDK,
  ProjectsSDK,
  AppCheckSDK,
};

// Re-export supplemental types from sub-modules
export type { PushNotificationPayload, PushNotificationRecord } from './push';
export type { AnalyticsQueryParams, AnalyticsQueryResult, BatchEventParams } from './analytics';
export type { CrashGroup, NetworkRequestRecord } from './crashlytics';
export type { ConfigCondition } from './remoteconfig';
export type { RealtimeListenerOptions, RealtimeChange, RealtimeSnapshot, ChangeListener, SnapshotListener, ErrorListener } from './realtime';

/**
 * OwnFirebase — top-level SDK bundle.
 *
 * All service sub-SDKs share the same auth token and project ID.
 * Call `setAccessToken()` after a successful `auth.login()` to propagate
 * the token to every service automatically.
 * Call `cleanup()` when your app is shutting down to properly close connections.
 */
export class OwnFirebase {
  readonly auth: AuthSDK;
  readonly data: DataSDK;
  readonly functions: FunctionsSDK;
  readonly storage: StorageSDK;
  readonly push: PushSDK;
  readonly analytics: AnalyticsSDK;
  readonly crashlytics: CrashlyticsSDK;
  readonly remoteConfig: RemoteConfigSDK;
  readonly realtime: RealtimeSDK;
  readonly ab: ABTestingSDK;
  readonly ai: AISDK;
  readonly projects: ProjectsSDK;
  readonly appCheck: AppCheckSDK;

  private _services: Array<AuthSDK | DataSDK | FunctionsSDK | StorageSDK | PushSDK | AnalyticsSDK | CrashlyticsSDK | RemoteConfigSDK | RealtimeSDK | ABTestingSDK | AISDK | ProjectsSDK | AppCheckSDK>;

  constructor(config: OwnFirebaseConfig) {
    this.auth = new AuthSDK(config);
    this.data = new DataSDK(config);
    this.functions = new FunctionsSDK(config);
    this.storage = new StorageSDK(config);
    this.push = new PushSDK(config);
    this.analytics = new AnalyticsSDK(config);
    this.crashlytics = new CrashlyticsSDK(config);
    this.remoteConfig = new RemoteConfigSDK(config);
    this.realtime = new RealtimeSDK(config);
    this.ab = new ABTestingSDK(config);
    this.ai = new AISDK(config);
    this.projects = new ProjectsSDK(config);
    this.appCheck = new AppCheckSDK(config);

    this._services = [
      this.auth,
      this.data,
      this.functions,
      this.storage,
      this.push,
      this.analytics,
      this.crashlytics,
      this.remoteConfig,
      this.realtime,
      this.ab,
      this.ai,
      this.projects,
      this.appCheck,
    ];
  }

  /**
   * Propagate a JWT access token to all service SDKs.
   * Call this immediately after `auth.login()` or `auth.refreshToken()`.
   */
  setAccessToken(token: string): void {
    for (const svc of this._services) {
      svc.setAccessToken(token);
    }
  }

  /**
   * Propagate a project ID to all service SDKs.
   */
  setProjectId(id: string): void {
    for (const svc of this._services) {
      svc.setProjectId(id);
    }
  }

  /**
   * Clean up resources: flush pending analytics batches, close realtime connection, etc.
   * Call this when your app is shutting down or the user logs out.
   */
  async cleanup(): Promise<void> {
    // Flush any pending analytics events
    if (this.analytics instanceof AnalyticsSDK) {
      try {
        await this.analytics.flushBatch();
      } catch (error) {
        console.warn('Failed to flush analytics batch during cleanup:', error);
      }
      this.analytics.destroy();
    }

    // Close realtime connection
    this.realtime.disconnect();
  }
}

/**
 * Factory function — the recommended way to initialize the SDK.
 *
 * @example
 * ```typescript
 * const app = initOwnFirebase({ baseUrl: 'http://localhost:8000', projectId: 'my-project-id' });
 * const tokens = await app.auth.login('user@example.com', 'password');
 * app.setAccessToken(tokens.access);
 * const docs = await app.data.listDocuments('users');
 * ```
 */
export function initOwnFirebase(config: OwnFirebaseConfig): OwnFirebase {
  return new OwnFirebase(config);
}
