import { useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWorkspace } from '../api/workspaces';
import type { Workspace } from '../types/workspace';
import { WorkspaceContext } from './workspaceContextValue';

const STORAGE_KEY = 'luminosity_active_workspace';

const PRESERVED_KEYS = new Set(['workspaces', 'health']);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [storedId, setStoredId] = useState<string | null>(() => {
    return localStorage.getItem(STORAGE_KEY);
  });
  const [localWorkspace, setLocalWorkspace] = useState<Workspace | null>(null);

  const { data, isLoading, isError, error } = useWorkspace(storedId);
  const errorStatus = (error as { response?: { status?: number } } | null)?.response?.status;
  const workspaceMissing = isError && errorStatus === 404;

  // Use API data when available, fall back to optimistic local data
  const activeWorkspace = workspaceMissing ? null : data ?? localWorkspace;

  // Clear stored workspace only when it genuinely no longer exists (404).
  // Transient network errors (502, timeout, etc.) should NOT wipe the
  // session — the local workspace data keeps the UI functional until the
  // next successful poll.
  useEffect(() => {
    if (storedId && workspaceMissing) {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [storedId, workspaceMissing]);

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
        isLoading: !!storedId && !workspaceMissing && isLoading && !localWorkspace,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}
