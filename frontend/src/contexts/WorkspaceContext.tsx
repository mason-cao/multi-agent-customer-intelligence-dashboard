import { useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWorkspace } from '../api/workspaces';
import type { Workspace } from '../types/workspace';
import { WorkspaceContext } from './workspaceContextValue';
import {
  ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY,
  ACTIVE_WORKSPACE_STORAGE_KEY,
  WORKSPACE_MISSING_EVENT,
} from '../constants/workspace';
import { clearStoredSession } from '../utils/session';
import { getApiErrorStatus } from '../api/errors';
import { clearDashboardQueries } from '../api/workspaceQueries';


export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [storedId, setStoredId] = useState<string | null>(() => {
    return localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  });
  const [localWorkspace, setLocalWorkspace] = useState<Workspace | null>(null);

  const { data, isLoading, isError, error } = useWorkspace(storedId);
  const errorStatus = getApiErrorStatus(error);
  const workspaceMissing = isError && errorStatus === 404;

  const activeWorkspace = workspaceMissing ? null :
    (data?.id === storedId ? data : null) ??
    (localWorkspace?.id === storedId ? localWorkspace : null);

  const clearDashboardCache = useCallback(() => {
    clearDashboardQueries(queryClient);
  }, [queryClient]);

  const clearWorkspaceState = useCallback(() => {
    clearDashboardCache();
    setStoredId(null);
    setLocalWorkspace(null);
    localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
    localStorage.removeItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY);
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
    if (ws.access_token) {
      localStorage.setItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY, ws.access_token);
    } else if (ws.id !== storedId) {
      localStorage.removeItem(ACTIVE_WORKSPACE_TOKEN_STORAGE_KEY);
    }
  }, [clearDashboardCache, storedId]);

  const clearWorkspace = useCallback(() => {
    clearWorkspaceState();
  }, [clearWorkspaceState]);

  const logout = useCallback(() => {
    queryClient.clear();
    setStoredId(null);
    setLocalWorkspace(null);
    clearStoredSession();
  }, [queryClient]);

  return (
    <WorkspaceContext.Provider
      value={{
        activeWorkspace,
        setActiveWorkspace,
        clearWorkspace,
        logout,
        isLoading: !!storedId && !workspaceMissing && isLoading && !localWorkspace,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}
