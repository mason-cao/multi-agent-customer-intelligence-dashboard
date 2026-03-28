import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWorkspace } from '../api/workspaces';
import type { Workspace } from '../types/workspace';

const STORAGE_KEY = 'luminosity_active_workspace';

interface WorkspaceContextType {
  activeWorkspace: Workspace | null;
  setActiveWorkspace: (ws: Workspace) => void;
  clearWorkspace: () => void;
  isLoading: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextType>({
  activeWorkspace: null,
  setActiveWorkspace: () => {},
  clearWorkspace: () => {},
  isLoading: true,
});

export function useActiveWorkspace() {
  return useContext(WorkspaceContext);
}

const PRESERVED_KEYS = new Set(['workspaces', 'health']);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [storedId, setStoredId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });
  const [localWorkspace, setLocalWorkspace] = useState<Workspace | null>(null);

  const { data, isLoading, isError } = useWorkspace(storedId);

  // Use API data when available, fall back to optimistic local data
  const activeWorkspace = data ?? localWorkspace;

  // Keep local workspace in sync with API data
  useEffect(() => {
    if (data) {
      setLocalWorkspace(data);
    }
  }, [data]);

  // Clear stored workspace if it no longer exists (404)
  useEffect(() => {
    if (isError && storedId) {
      setStoredId(null);
      setLocalWorkspace(null);
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [isError, storedId]);

  const clearDashboardCache = useCallback(() => {
    queryClient.removeQueries({
      predicate: (query) => !PRESERVED_KEYS.has(query.queryKey[0] as string),
    });
  }, [queryClient]);

  const setActiveWorkspace = useCallback((ws: Workspace) => {
    clearDashboardCache();
    setStoredId(ws.id);
    setLocalWorkspace(ws);
    localStorage.setItem(STORAGE_KEY, ws.id);
  }, [clearDashboardCache]);

  const clearWorkspace = useCallback(() => {
    clearDashboardCache();
    setStoredId(null);
    setLocalWorkspace(null);
    localStorage.removeItem(STORAGE_KEY);
  }, [clearDashboardCache]);

  return (
    <WorkspaceContext.Provider
      value={{
        activeWorkspace,
        setActiveWorkspace,
        clearWorkspace,
        isLoading: !!storedId && isLoading && !localWorkspace,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}
