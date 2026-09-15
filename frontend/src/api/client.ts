import {
  ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY,
  ACTIVE_WORKSPACE_STORAGE_KEY,
  ADMIN_TOKEN_STORAGE_KEY,
  WORKSPACE_MISSING_EVENT,
} from '../constants/workspace';
import { ApiError, getApiErrorDetail } from './errors';

export interface WorkspaceCredentials {
  id: string;
  token: string | null;
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  workspace?: WorkspaceCredentials;
}

export function getWorkspaceCredentials(): WorkspaceCredentials | undefined {
  const id = localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  return id ? { id, token: localStorage.getItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY) } : undefined;
}

function handleMissingWorkspace(error: ApiError, path: string, workspace?: WorkspaceCredentials) {
  if (error.status !== 404 || !workspace) return;
  const detail = getApiErrorDetail(error);
  const missing = detail?.startsWith('Workspace database not found:') ||
    (detail === "This workspace doesn't exist." &&
      (!path.startsWith('/workspaces') || path === `/workspaces/${workspace.id}`));
  const active = getWorkspaceCredentials();
  // A response from an earlier workspace or token must not clear a newer session.
  if (!missing || active?.id !== workspace.id || active.token !== workspace.token) return;
  localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  localStorage.removeItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY);
  window.dispatchEvent(new CustomEvent(WORKSPACE_MISSING_EVENT, { detail: { workspaceId: workspace.id } }));
}

export async function request<T>(path: string, options: RequestOptions = {}, body?: unknown): Promise<T> {
  const { workspace = getWorkspaceCredentials(), ...init } = options;
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (body !== undefined) headers.set('Content-Type', 'application/json');
  const adminToken = localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ||
    import.meta.env?.VITE_ADMIN_API_TOKEN || import.meta.env?.VITE_ADMIN_TOKEN;
  if (adminToken) headers.set('X-Admin-Token', adminToken);
  if (workspace?.id && workspace.token) {
    headers.set('X-Workspace-ID', workspace.id);
    headers.set('X-Workspace-Token', workspace.token);
  }
  const response = await fetch(`/api${path}`, {
    ...init, headers, body: body === undefined ? undefined : JSON.stringify(body),
  });
  const raw = await response.text();
  let data: unknown = raw || undefined;
  if (raw) {
    try { data = JSON.parse(raw); } catch { /* Proxies may return a plain-text error. */ }
  }
  if (!response.ok) {
    const error = new ApiError(response.status, data);
    handleMissingWorkspace(error, path, workspace);
    throw error;
  }
  return data as T;
}

const api = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: 'POST' }, body),
  delete: (path: string, options?: RequestOptions) => request<void>(path, { ...options, method: 'DELETE' }),
};
export default api;
