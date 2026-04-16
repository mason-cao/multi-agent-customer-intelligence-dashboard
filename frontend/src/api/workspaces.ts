import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosError } from 'axios';
import api from './client';
import type { Workspace, WorkspaceListResponse, Scenario, CreateWorkspaceInput } from '../types/workspace';

type ApiError = AxiosError<{ detail?: string }>;

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
    retry: (failureCount, error) => {
      if ((error as ApiError).response?.status === 404) return false;
      return failureCount < 3;
    },
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
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
  return useMutation<Workspace, Error, CreateWorkspaceInput>({
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
  return useMutation<Workspace, Error, string>({
    mutationFn: async (workspaceId) => {
      const { data } = await api.post(`/workspaces/${workspaceId}/generate`);
      return data;
    },
    onSuccess: (_, workspaceId) => {
      queryClient.invalidateQueries({ queryKey: ['workspaces', workspaceId] });
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      // Clear stale dashboard data from the previous generation
      queryClient.removeQueries({
        predicate: (query) => {
          const key = query.queryKey[0] as string;
          return key !== 'workspaces' && key !== 'health';
        },
      });
    },
  });
}

export function useDeleteWorkspace() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (workspaceId) => {
      await api.delete(`/workspaces/${workspaceId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
  });
}
