import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach active workspace ID so dashboard routes read from the correct DB
api.interceptors.request.use((config) => {
  const workspaceId = localStorage.getItem('luminosity_active_workspace');
  if (workspaceId) {
    config.headers['X-Workspace-ID'] = workspaceId;
  }
  return config;
});

// Handle workspace-not-found errors — redirect to hub when the active
// workspace DB has been deleted or is no longer reachable.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 404 &&
      typeof error.response?.data?.detail === 'string' &&
      error.response.data.detail.includes('Workspace database not found')
    ) {
      console.warn('[client interceptor] Workspace DB not found — redirect triggered by:', error.config?.url);
      localStorage.removeItem('luminosity_active_workspace');
      window.location.href = '/workspaces';
      return new Promise(() => {}); // halt further processing
    }
    return Promise.reject(error);
  },
);

export default api;
