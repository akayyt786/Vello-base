import { OwnFirebaseClient } from './client';
import type { Project, ProjectMember, PaginatedResponse } from './types';

export class ProjectsSDK extends OwnFirebaseClient {
  async listProjects(): Promise<PaginatedResponse<Project>> {
    return this.request('GET', `${this.baseUrl}/api/v1/projects/`);
  }

  async getProject(id: string): Promise<Project> {
    return this.request('GET', `${this.baseUrl}/api/v1/projects/${id}/`);
  }

  async createProject(
    data: Pick<Project, 'name'> & Partial<Pick<Project, 'description'>>
  ): Promise<Project> {
    return this.request('POST', `${this.baseUrl}/api/v1/projects/`, data);
  }

  async updateProject(
    id: string,
    updates: Partial<Pick<Project, 'name' | 'description'>>
  ): Promise<Project> {
    return this.request('PATCH', `${this.baseUrl}/api/v1/projects/${id}/`, updates);
  }

  async deleteProject(id: string): Promise<void> {
    return this.request('DELETE', `${this.baseUrl}/api/v1/projects/${id}/`);
  }

  // ─── Memberships ─────────────────────────────────────────────────────────────

  async listMembers(projectId: string): Promise<PaginatedResponse<ProjectMember>> {
    return this.request(
      'GET',
      `${this.baseUrl}/api/v1/memberships/`,
      undefined,
      { query: { project: projectId } }
    );
  }

  async addMember(
    projectId: string,
    userId: string,
    role: ProjectMember['role']
  ): Promise<ProjectMember> {
    return this.request('POST', `${this.baseUrl}/api/v1/memberships/`, {
      project: projectId,
      user: userId,
      role,
    });
  }

  async updateMemberRole(
    membershipId: string,
    role: ProjectMember['role']
  ): Promise<ProjectMember> {
    return this.request(
      'PATCH',
      `${this.baseUrl}/api/v1/memberships/${membershipId}/`,
      { role }
    );
  }

  async removeMember(membershipId: string): Promise<void> {
    return this.request(
      'DELETE',
      `${this.baseUrl}/api/v1/memberships/${membershipId}/`
    );
  }
}
