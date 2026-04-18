import { useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWorkspace } from '../api/workspaces';
import type { Workspace } from '../types/workspace';
import { WorkspaceContext } from './workspaceContextValue';
import {
  ACTIVE_WORKSPACE_STORAGE_KEY,
  WORKSPACE_MISSING_EVENT,
} from '../constants/workspace';

const PRESERVED_KEYS = new Set(['workspaces', 'health']);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [storedId, setStoredId] = useState<string | null>(() => {
    return localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  });
  const [localWorkspace, setLocalWorkspace] = useState<Workspace | null>(null);

  const { data, isLoading, isError, error } = useWorkspace(storedId);
  const errorStatus = (error as { response?: { status?: number } } | null)?.response?.status;
  const workspaceMissing = isError && errorStatus === 404;

  // Use API data when available, fall back to optimistic local data
  const activeWorkspace = workspaceMissing ? null : data ?? localWorkspace;

  const clearDashboardCache = useCallback(() => {
    queryClient.removeQueries({
      predicate: (query) => !PRESERVED_KEYS.has(query.queryKey[0] as string),
    });
  }, [queryClient]);

  const clearWorkspaceState = useCallback(() => {
    clearDashboardCache();
    setStoredId(null);
    setLocalWorkspace(null);
    localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  }, [clearDashboardCache]);

  useEffect(() => {
    window.addEventListener(WORKSPACE_MISSING_EVENT, clearWorkspaceState);
    return () => {
      window.removeEventListener(WORKSPACE_MISSING_EVENT, clearWorkspaceState);
    };
  }, [clearWorkspaceState]);

  const setActiveWorkspace = useCallback((ws: Workspace) => {
    clearDashboardCache();
    setStoredId(ws.id);
    setLocalWorkspace(ws);
    localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, ws.id);
  }, [clearDashboardCache]);

  const clearWorkspace = useCallback(() => {
    clearWorkspaceState();
  }, [clearWorkspaceState]);

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
