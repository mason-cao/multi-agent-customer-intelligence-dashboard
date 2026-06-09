import axios from 'axios';
import {
  ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY,
  ACTIVE_WORKSPACE_STORAGE_KEY,
  ADMIN_TOKEN_STORAGE_KEY,
  WORKSPACE_MISSING_EVENT,
} from '../constants/workspace';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach active credentials so the API can enforce admin and workspace access.
api.interceptors.request.use((config) => {
  const adminToken =
    import.meta.env.VITE_ADMIN_API_TOKEN ||
    localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
  if (adminToken) {
    config.headers['X-Admin-Token'] = adminToken;
  }

  const workspaceId = localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  const workspaceToken = localStorage.getItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY);
  if (workspaceId && workspaceToken) {
    config.headers['X-Workspace-ID'] = workspaceId;
    config.headers['X-Workspace-Token'] = workspaceToken;
  }
  return config;
});

// Handle workspace-not-found errors — redirect to hub when the active
// workspace DB has been deleted or is no longer reachable.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    const requestUrl = error.config?.url ?? '';
    const workspaceDatabaseMissing =
      error.response?.status === 404 &&
      typeof detail === 'string' &&
      detail.includes('Workspace database not found');
    const workspaceRecordMissing =
      error.response?.status === 404 &&
      typeof detail === 'string' &&
      detail.includes("This workspace doesn't exist") &&
      requestUrl.startsWith('/workspaces/');

    if (workspaceDatabaseMissing || workspaceRecordMissing) {
      const workspaceId = localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
      localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
      localStorage.removeItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY);
      window.dispatchEvent(
        new CustomEvent(WORKSPACE_MISSING_EVENT, {
          detail: { workspaceId },
        }),
      );
    }
    return Promise.reject(error);
  },
);

export default api;
