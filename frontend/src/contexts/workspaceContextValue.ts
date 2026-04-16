import { createContext, useContext } from 'react';
import type { Workspace } from '../types/workspace';

export interface WorkspaceContextType {
  activeWorkspace: Workspace | null;
  setActiveWorkspace: (ws: Workspace) => void;
  clearWorkspace: () => void;
  isLoading: boolean;
}

export const WorkspaceContext = createContext<WorkspaceContextType>({
  activeWorkspace: null,
  setActiveWorkspace: () => {},
  clearWorkspace: () => {},
  isLoading: true,
});

export function useActiveWorkspace() {
  return useContext(WorkspaceContext);
}
