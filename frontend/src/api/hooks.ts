import { useQuery, useMutation } from '@tanstack/react-query';
import api from './client';
import { useActiveWorkspace } from '../contexts/workspaceContextValue';
import type {
  KpiData,
  SegmentSummary,
  ChurnDistribution,
  AtRiskCustomer,
  FeatureImportance,
  RecommendationSummary,
  RecommendationItem,
  SentimentSummary,
  AgentsSummary,
  CustomerListResponse,
  QueryResult,
} from '../types';

// ── Overview ──────────────────────────────────────────────

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
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<OverviewKpis>({
    queryKey: ['overview', 'kpis', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/overview/kpis');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

export function useOverviewNarrative() {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<NarrativeResponse>({
    queryKey: ['overview', 'narrative', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/overview/narrative');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

// ── Segments ──────────────────────────────────────────────

export function useSegmentSummary() {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<SegmentSummary[]>({
    queryKey: ['segments', 'summary', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/segments/summary');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

// ── Churn ─────────────────────────────────────────────────

export function useChurnDistribution() {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<ChurnDistribution[]>({
    queryKey: ['churn', 'distribution', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/churn/distribution');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

export function useAtRiskCustomers(limit = 20) {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<AtRiskCustomer[]>({
    queryKey: ['churn', 'at-risk', limit, activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get(`/churn/at-risk?limit=${limit}`);
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

export function useFeatureImportance() {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<FeatureImportance[]>({
    queryKey: ['churn', 'feature-importance', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/churn/feature-importance');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

// ── Recommendations ───────────────────────────────────────

export function useRecommendationSummary() {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<RecommendationSummary>({
    queryKey: ['recommendations', 'summary', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/recommendations/summary');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

export function useTopRecommendations(limit = 20) {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<RecommendationItem[]>({
    queryKey: ['recommendations', 'top', limit, activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get(`/recommendations/top?limit=${limit}`);
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

// ── Sentiment ─────────────────────────────────────────────

export function useSentimentSummary() {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<SentimentSummary>({
    queryKey: ['sentiment', 'summary', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/sentiment/summary');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

// ── Agent Audit ───────────────────────────────────────────

export function useAgentsSummary() {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<AgentsSummary>({
    queryKey: ['agents', 'summary', activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get('/agents/summary');
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

// ── Customers ─────────────────────────────────────────────

export function useCustomers(limit = 50, offset = 0) {
  const { activeWorkspace } = useActiveWorkspace();
  return useQuery<CustomerListResponse>({
    queryKey: ['customers', limit, offset, activeWorkspace?.id, activeWorkspace?.completed_at],
    queryFn: async () => {
      const { data } = await api.get(`/customers?limit=${limit}&offset=${offset}`);
      return data;
    },
    enabled: !!activeWorkspace && activeWorkspace.status === 'ready',
  });
}

// ── Query (Ask Anything) ──────────────────────────────────

export function useAskQuestion() {
  return useMutation<QueryResult, Error, string>({
    mutationFn: async (question: string) => {
      const { data } = await api.post('/query', { question });
      return data;
    },
  });
}
