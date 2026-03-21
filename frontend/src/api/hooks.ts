import { useQuery } from '@tanstack/react-query';
import api from './client';

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health');
      return data;
    },
  });
}
