import { useQuery } from '@tanstack/react-query';
import api from './client';
import type { KpiData } from '../types';

interface OverviewKpis {
  total_customers: KpiData;
  monthly_revenue: KpiData;
  churn_rate: KpiData;
  avg_sentiment: KpiData;
  active_anomalies: KpiData;
}

interface NarrativeResponse {
  executive_summary: string;
  key_metrics: { label: string; value: string | number }[];
  highlights: string[];
  concerns: string[];
  generated_at: string;
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data } = await api.get('/health');
      return data;
    },
  });
}

export function useOverviewKpis() {
  return useQuery<OverviewKpis>({
    queryKey: ['overview', 'kpis'],
    queryFn: async () => {
      const { data } = await api.get('/overview/kpis');
      return data;
    },
  });
}

export function useOverviewNarrative() {
  return useQuery<NarrativeResponse>({
    queryKey: ['overview', 'narrative'],
    queryFn: async () => {
      const { data } = await api.get('/overview/narrative');
      return data;
    },
  });
}
