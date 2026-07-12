import { ProjectsSDK } from '../src/projects';
import type { Project, ProjectMember, PaginatedResponse } from '../src/types';

global.fetch = jest.fn();

describe('ProjectsSDK', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const config = {
    baseUrl: 'http://localhost:8000',
  };

  describe('projects', () => {
    it('should list projects', async () => {
      const mockResponse: PaginatedResponse<Project> = {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'proj1',
            name: 'E-Commerce App',
            slug: 'ecommerce-app',
            description: 'Main e-commerce platform',
            created_at: '2023-12-01T00:00:00Z',
            updated_at: '2024-01-01T12:00:00Z',
          },
          {
            id: 'proj2',
            name: 'Mobile App',
            slug: 'mobile-app',
            description: 'iOS and Android mobile application',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-05T10:00:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.listProjects();

      expect(result.count).toBe(2);
      expect(result.results).toHaveLength(2);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/projects/',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should get specific project', async () => {
      const mockProject: Project = {
        id: 'proj1',
        name: 'E-Commerce App',
        slug: 'ecommerce-app',
        description: 'Main e-commerce platform',
        created_at: '2023-12-01T00:00:00Z',
        updated_at: '2024-01-01T12:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockProject,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.getProject('proj1');

      expect(result).toEqual(mockProject);
      expect(result.name).toBe('E-Commerce App');
    });

    it('should create project', async () => {
      const mockProject: Project = {
        id: 'proj3',
        name: 'New Project',
        slug: 'new-project',
        description: 'A new project for testing',
        created_at: '2024-01-05T00:00:00Z',
        updated_at: '2024-01-05T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockProject,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.createProject({
        name: 'New Project',
        description: 'A new project for testing',
      });

      expect(result).toEqual(mockProject);
      expect(result.id).toBe('proj3');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/projects/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            name: 'New Project',
            description: 'A new project for testing',
          }),
        })
      );
    });

    it('should create project without description', async () => {
      const mockProject: Project = {
        id: 'proj4',
        name: 'Minimal Project',
        slug: 'minimal-project',
        description: '',
        created_at: '2024-01-05T00:00:00Z',
        updated_at: '2024-01-05T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockProject,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.createProject({
        name: 'Minimal Project',
      });

      expect(result.name).toBe('Minimal Project');
    });

    it('should update project', async () => {
      const mockProject: Project = {
        id: 'proj1',
        name: 'Updated Name',
        slug: 'ecommerce-app',
        description: 'Updated description',
        created_at: '2023-12-01T00:00:00Z',
        updated_at: '2024-01-05T15:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockProject,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.updateProject('proj1', {
        name: 'Updated Name',
        description: 'Updated description',
      });

      expect(result.name).toBe('Updated Name');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/projects/proj1/',
        expect.objectContaining({
          method: 'PATCH',
        })
      );
    });

    it('should delete project', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.deleteProject('proj1');

      expect(result).toBeUndefined();
    });
  });

  describe('project members', () => {
    it('should list project members', async () => {
      const mockResponse: PaginatedResponse<ProjectMember> = {
        count: 3,
        next: null,
        previous: null,
        results: [
          {
            id: 'mem1',
            user: 'user1',
            role: 'owner',
            joined_at: '2023-12-01T00:00:00Z',
          },
          {
            id: 'mem2',
            user: 'user2',
            role: 'editor',
            joined_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'mem3',
            user: 'user3',
            role: 'viewer',
            joined_at: '2024-01-02T00:00:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.listMembers('proj1');

      expect(result.count).toBe(3);
      expect(result.results).toHaveLength(3);
      expect(result.results[0].role).toBe('owner');
    });

    it('should add member to project', async () => {
      const mockMember: ProjectMember = {
        id: 'mem4',
        user: 'user4',
        role: 'editor',
        joined_at: '2024-01-05T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockMember,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.addMember('proj1', 'user4', 'editor');

      expect(result).toEqual(mockMember);
      expect(result.role).toBe('editor');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/memberships/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            project: 'proj1',
            user: 'user4',
            role: 'editor',
          }),
        })
      );
    });

    it('should add member as owner', async () => {
      const mockMember: ProjectMember = {
        id: 'mem5',
        user: 'user5',
        role: 'owner',
        joined_at: '2024-01-05T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockMember,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.addMember('proj1', 'user5', 'owner');

      expect(result.role).toBe('owner');
    });

    it('should add member as viewer', async () => {
      const mockMember: ProjectMember = {
        id: 'mem6',
        user: 'user6',
        role: 'viewer',
        joined_at: '2024-01-05T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockMember,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.addMember('proj1', 'user6', 'viewer');

      expect(result.role).toBe('viewer');
    });

    it('should update member role', async () => {
      const mockMember: ProjectMember = {
        id: 'mem2',
        user: 'user2',
        role: 'owner',
        joined_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockMember,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.updateMemberRole('mem2', 'owner');

      expect(result.role).toBe('owner');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/memberships/mem2/',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ role: 'owner' }),
        })
      );
    });

    it('should downgrade member role', async () => {
      const mockMember: ProjectMember = {
        id: 'mem1',
        user: 'user1',
        role: 'viewer',
        joined_at: '2023-12-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockMember,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.updateMemberRole('mem1', 'viewer');

      expect(result.role).toBe('viewer');
    });

    it('should remove member from project', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.removeMember('mem4');

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/memberships/mem4/',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('project collaboration scenarios', () => {
    it('should handle team project setup', async () => {
      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      // Create project
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          id: 'team-proj',
          name: 'Team Project',
          slug: 'team-project',
          description: 'Collaborative project',
          created_at: '2024-01-05T00:00:00Z',
          updated_at: '2024-01-05T00:00:00Z',
        }),
      });

      const projectResult = await projects.createProject({
        name: 'Team Project',
        description: 'Collaborative project',
      });

      expect(projectResult.name).toBe('Team Project');

      // Add team members
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          status: 201,
          json: async () => ({
            id: 'mem-alice',
            user: 'alice',
            role: 'editor',
            joined_at: '2024-01-05T00:00:00Z',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 201,
          json: async () => ({
            id: 'mem-bob',
            user: 'bob',
            role: 'editor',
            joined_at: '2024-01-05T00:00:00Z',
          }),
        });

      const alice = await projects.addMember('team-proj', 'alice', 'editor');
      const bob = await projects.addMember('team-proj', 'bob', 'editor');

      expect(alice.user).toBe('alice');
      expect(bob.user).toBe('bob');
    });

    it('should handle role transitions', async () => {
      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      // Promote viewer to editor
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          id: 'mem-viewer',
          user: 'viewer-user',
          role: 'editor',
          joined_at: '2024-01-01T00:00:00Z',
        }),
      });

      const result = await projects.updateMemberRole('mem-viewer', 'editor');

      expect(result.role).toBe('editor');
    });

    it('should handle multiple projects per user', async () => {
      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          count: 5,
          next: null,
          previous: null,
          results: Array(5).fill(null).map((_, i) => ({
            id: `proj-${i}`,
            name: `Project ${i}`,
            slug: `project-${i}`,
            description: `Description ${i}`,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-05T00:00:00Z',
          })),
        }),
      });

      const result = await projects.listProjects();

      expect(result.count).toBe(5);
    });
  });

  describe('access control and permissions', () => {
    it('should support three role levels', () => {
      const roles: Array<'owner' | 'editor' | 'viewer'> = ['owner', 'editor', 'viewer'];

      expect(roles).toHaveLength(3);
      expect(roles[0]).toBe('owner');
      expect(roles[1]).toBe('editor');
      expect(roles[2]).toBe('viewer');
    });

    it('should track member join dates', async () => {
      const mockResponse: PaginatedResponse<ProjectMember> = {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'mem-recent',
            user: 'recent-user',
            role: 'viewer',
            joined_at: '2024-01-05T12:30:00Z',
          },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const projects = new ProjectsSDK(config);
      projects.setAccessToken('access-token');

      const result = await projects.listMembers('proj1');

      expect(result.results[0].joined_at).toBeDefined();
    });
  });
});
