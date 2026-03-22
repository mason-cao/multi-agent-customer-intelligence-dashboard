import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
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

export function WorkspaceProvider({ children }: { children: ReactNode }) {
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

  const setActiveWorkspace = useCallback((ws: Workspace) => {
    setStoredId(ws.id);
    setLocalWorkspace(ws);
    localStorage.setItem(STORAGE_KEY, ws.id);
  }, []);

  const clearWorkspace = useCallback(() => {
    setStoredId(null);
    setLocalWorkspace(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

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
