const BASE = '/api';

let _token = localStorage.getItem('access_token') || '';

export function setToken(t: string) {
  _token = t;
  localStorage.setItem('access_token', t);
}

export function getToken() { return _token; }

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (_token) headers['Authorization'] = 'Bearer ' + _token;
  const r = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw { status: r.status, detail: await r.json().catch(() => r.text()) };
  if (r.status === 204) return undefined as unknown as T;
  return r.json();
}

export const api = {
  login: (email: string, password: string) => req<{ access: string; refresh: string }>('POST', '/v1/auth/login/', { email, password }),
  me: () => req<{ id: string; email: string; username: string }>('GET', '/v1/auth/me/'),
  listProjects: () => req<any[]>('GET', '/v1/projects/'),
  getProject: (id: string) => req<any>('GET', `/v1/projects/${id}/`),
  listMembers: (id: string) => req<any[]>('GET', `/projects/${id}/members/`),
  listCollections: (id: string) => req<any[]>('GET', `/projects/${id}/data/collections/`),
  aiUsage: (id: string) => req<any[]>('GET', `/projects/${id}/ai/usage/`),
  listExperiments: (id: string) => req<any[]>('GET', `/projects/${id}/abtesting/experiments/`),
  listFunctions: (id: string) => req<any[]>('GET', `/projects/${id}/functions/`),
};
