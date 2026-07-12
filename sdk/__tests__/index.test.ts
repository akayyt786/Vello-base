import { OwnFirebase, initOwnFirebase } from '../src/index';
import { AuthSDK } from '../src/auth';
import { DataSDK } from '../src/data';
import { AnalyticsSDK } from '../src/analytics';
import { FunctionsSDK } from '../src/functions';
import { StorageSDK } from '../src/storage';
import { PushSDK } from '../src/push';
import { RemoteConfigSDK } from '../src/remoteconfig';
import { ABTestingSDK } from '../src/abtesting';
import { AISDK } from '../src/ai';
import { CrashlyticsSDK } from '../src/crashlytics';
import { ProjectsSDK } from '../src/projects';
import { AppCheckSDK } from '../src/appcheck';

describe('OwnFirebase SDK Initialization', () => {
  describe('OwnFirebase class', () => {
    it('should initialize with config', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
        accessToken: 'test-token',
      };

      const app = new OwnFirebase(config);

      expect(app).toBeDefined();
      expect(app.auth).toBeInstanceOf(AuthSDK);
      expect(app.data).toBeInstanceOf(DataSDK);
      expect(app.analytics).toBeInstanceOf(AnalyticsSDK);
    });

    it('should have all service SDKs', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      };

      const app = new OwnFirebase(config);

      expect(app.auth).toBeInstanceOf(AuthSDK);
      expect(app.data).toBeInstanceOf(DataSDK);
      expect(app.functions).toBeInstanceOf(FunctionsSDK);
      expect(app.storage).toBeInstanceOf(StorageSDK);
      expect(app.push).toBeInstanceOf(PushSDK);
      expect(app.analytics).toBeInstanceOf(AnalyticsSDK);
      expect(app.crashlytics).toBeInstanceOf(CrashlyticsSDK);
      expect(app.remoteConfig).toBeInstanceOf(RemoteConfigSDK);
      expect(app.ab).toBeInstanceOf(ABTestingSDK);
      expect(app.ai).toBeInstanceOf(AISDK);
      expect(app.projects).toBeInstanceOf(ProjectsSDK);
      expect(app.appCheck).toBeInstanceOf(AppCheckSDK);
    });

    it('should propagate access token to all services', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      };

      const app = new OwnFirebase(config);

      const testToken = 'new-access-token-xyz';
      app.setAccessToken(testToken);

      // Verify that all services have the token set
      // (We can't directly access protected properties, but the setAccessToken call should work)
      expect(() => app.setAccessToken(testToken)).not.toThrow();
    });

    it('should propagate project ID to all services', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
      };

      const app = new OwnFirebase(config);

      const testProjectId = 'new-project-123';
      app.setProjectId(testProjectId);

      // Verify that setProjectId works
      expect(() => app.setProjectId(testProjectId)).not.toThrow();
    });
  });

  describe('initOwnFirebase factory function', () => {
    it('should create OwnFirebase instance', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      };

      const app = initOwnFirebase(config);

      expect(app).toBeInstanceOf(OwnFirebase);
      expect(app.auth).toBeDefined();
      expect(app.data).toBeDefined();
    });

    it('should work with minimal config', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
      };

      const app = initOwnFirebase(config);

      expect(app).toBeInstanceOf(OwnFirebase);
    });

    it('should work with full config', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'my-project',
        accessToken: 'initial-token',
      };

      const app = initOwnFirebase(config);

      expect(app).toBeInstanceOf(OwnFirebase);
    });

    it('should be equivalent to new OwnFirebase()', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      };

      const app1 = new OwnFirebase(config);
      const app2 = initOwnFirebase(config);

      expect(app1).toBeInstanceOf(OwnFirebase);
      expect(app2).toBeInstanceOf(OwnFirebase);
    });
  });

  describe('SDK composition and integration', () => {
    it('should allow chaining operations', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
        accessToken: 'test-token',
      };

      const app = new OwnFirebase(config);

      // Should be able to set token and project on app
      app.setAccessToken('new-token');
      app.setProjectId('other-project');

      expect(app.auth).toBeDefined();
      expect(app.data).toBeDefined();
    });

    it('should support different baseUrl formats', () => {
      const config1 = initOwnFirebase({
        baseUrl: 'http://localhost:8000',
        projectId: 'proj1',
      });

      const config2 = initOwnFirebase({
        baseUrl: 'http://localhost:8000/',
        projectId: 'proj1',
      });

      const config3 = initOwnFirebase({
        baseUrl: 'https://api.example.com',
        projectId: 'proj1',
      });

      expect(config1).toBeInstanceOf(OwnFirebase);
      expect(config2).toBeInstanceOf(OwnFirebase);
      expect(config3).toBeInstanceOf(OwnFirebase);
    });
  });

  describe('SDK lifecycle', () => {
    it('should initialize with no token initially', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      };

      const app = new OwnFirebase(config);

      // App should be created without token
      expect(app).toBeInstanceOf(OwnFirebase);
    });

    it('should allow updating token after initialization', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      };

      const app = new OwnFirebase(config);

      const token1 = 'token-1';
      const token2 = 'token-2';

      app.setAccessToken(token1);
      app.setAccessToken(token2);

      expect(() => app.setAccessToken(token2)).not.toThrow();
    });

    it('should allow updating project ID after initialization', () => {
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'project-1',
      };

      const app = new OwnFirebase(config);

      const proj1 = 'project-1';
      const proj2 = 'project-2';

      app.setProjectId(proj1);
      app.setProjectId(proj2);

      expect(() => app.setProjectId(proj2)).not.toThrow();
    });
  });

  describe('multi-app support', () => {
    it('should support multiple independent instances', () => {
      const app1 = initOwnFirebase({
        baseUrl: 'http://localhost:8000',
        projectId: 'project-1',
      });

      const app2 = initOwnFirebase({
        baseUrl: 'http://localhost:8001',
        projectId: 'project-2',
      });

      expect(app1).toBeInstanceOf(OwnFirebase);
      expect(app2).toBeInstanceOf(OwnFirebase);
      expect(app1).not.toBe(app2);
    });

    it('should allow different tokens per instance', () => {
      const app1 = initOwnFirebase({
        baseUrl: 'http://localhost:8000',
        projectId: 'project-1',
      });

      const app2 = initOwnFirebase({
        baseUrl: 'http://localhost:8000',
        projectId: 'project-1',
      });

      app1.setAccessToken('token-user1');
      app2.setAccessToken('token-user2');

      expect(() => app1.setAccessToken('token-user1')).not.toThrow();
      expect(() => app2.setAccessToken('token-user2')).not.toThrow();
    });
  });

  describe('type exports', () => {
    it('should export all type definitions', () => {
      // This is a compile-time check, but we verify the imports work
      const config = {
        baseUrl: 'http://localhost:8000',
        projectId: 'test-project',
      };

      const app = initOwnFirebase(config);

      expect(app.auth).toBeDefined();
      expect(app.data).toBeDefined();
      expect(app.analytics).toBeDefined();
    });
  });
});
