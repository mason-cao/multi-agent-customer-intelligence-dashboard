import { createContext, useContext } from 'react';
import type { Workspace } from '../types/workspace';

export interface WorkspaceContextType {
  activeWorkspace: Workspace | null;
  setActiveWorkspace: (ws: Workspace) => void;
  clearWorkspace: () => void;
  logout: () => void;
  isLoading: boolean;
}

export const WorkspaceContext = createContext<WorkspaceContextType>({
  activeWorkspace: null,
  setActiveWorkspace: () => {},
  clearWorkspace: () => {},
  logout: () => {},
  isLoading: true,
});

export function useActiveWorkspace() {
  return useContext(WorkspaceContext);
}
