import { useQuery, type QueryClient, type QueryKey } from '@tanstack/react-query';
import { useActiveWorkspace } from '../contexts/workspaceContextValue';
import api, { getWorkspaceCredentials } from './client';

export const DASHBOARD_QUERY_KEY = 'dashboard';

export function clearDashboardQueries(queryClient: QueryClient, workspaceId?: string) {
  const queryKey = workspaceId ? [DASHBOARD_QUERY_KEY, workspaceId] : [DASHBOARD_QUERY_KEY];
  void queryClient.cancelQueries({ queryKey });
  queryClient.removeQueries({ queryKey });
}

export function useWorkspaceQuery<T>(path: string, key: QueryKey, keepPrevious = false) {
  const { activeWorkspace } = useActiveWorkspace();
  const stored = getWorkspaceCredentials();
  const workspace = activeWorkspace ? {
    id: activeWorkspace.id,
    token: activeWorkspace.access_token ?? (stored?.id === activeWorkspace.id ? stored.token : null),
  } : undefined;
  return useQuery<T>({
    queryKey: [DASHBOARD_QUERY_KEY, activeWorkspace?.id, activeWorkspace?.completed_at, ...key],
    queryFn: ({ signal }) => api.get<T>(path, { signal, workspace }),
    enabled: activeWorkspace?.status === 'ready' && !!workspace?.token,
    placeholderData: keepPrevious ? (previous, previousQuery) =>
      previousQuery?.queryKey[1] === activeWorkspace?.id &&
      previousQuery?.queryKey[2] === activeWorkspace?.completed_at ? previous : undefined
      : undefined,
  });
}
