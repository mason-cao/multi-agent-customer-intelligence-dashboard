import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from './client';
import type { Workspace, WorkspaceListResponse, Scenario } from '../types/workspace';

export function useWorkspaces() {
  return useQuery<WorkspaceListResponse>({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const { data } = await api.get('/workspaces');
      return data;
    },
    refetchInterval: (query) => {
      const list = query.state.data;
      return list?.workspaces.some((ws) => ws.status === 'generating')
        ? 2000
        : false;
    },
  });
}

export function useWorkspace(id: string | null) {
  return useQuery<Workspace>({
    queryKey: ['workspaces', id],
    queryFn: async () => {
      const { data } = await api.get(`/workspaces/${id}`);
      return data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      return query.state.data?.status === 'generating' ? 2000 : false;
    },
  });
}

export function useScenarios() {
  return useQuery<Scenario[]>({
    queryKey: ['workspaces', 'scenarios'],
    queryFn: async () => {
      const { data } = await api.get('/workspaces/scenarios');
      return data;
    },
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();
  return useMutation<Workspace, Error, { name: string; scenario: string }>({
    mutationFn: async (body) => {
      const { data } = await api.post('/workspaces', body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });
}

export function useGenerateWorkspace() {
  const queryClient = useQueryClient();
  return useMutation<{ status: string; workspace_id: string }, Error, string>({
    mutationFn: async (workspaceId) => {
      const { data } = await api.post(`/workspaces/${workspaceId}/generate`);
      return data;
    },
    onSuccess: (_, workspaceId) => {
      queryClient.invalidateQueries({ queryKey: ['workspaces', workspaceId] });
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });
}
