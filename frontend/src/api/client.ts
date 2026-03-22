import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach active workspace ID so dashboard routes read from the correct DB
api.interceptors.request.use((config) => {
  const workspaceId = localStorage.getItem('nexus_active_workspace');
  if (workspaceId) {
    config.headers['X-Workspace-ID'] = workspaceId;
  }
  return config;
});

export default api;
