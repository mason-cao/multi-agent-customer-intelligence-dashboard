import { useQuery, useMutation } from '@tanstack/react-query';
import api from './client';
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

// ── Segments ──────────────────────────────────────────────

export function useSegmentSummary() {
  return useQuery<SegmentSummary[]>({
    queryKey: ['segments', 'summary'],
    queryFn: async () => {
      const { data } = await api.get('/segments/summary');
      return data;
    },
  });
}

// ── Churn ─────────────────────────────────────────────────

export function useChurnDistribution() {
  return useQuery<ChurnDistribution[]>({
    queryKey: ['churn', 'distribution'],
    queryFn: async () => {
      const { data } = await api.get('/churn/distribution');
      return data;
    },
  });
}

export function useAtRiskCustomers(limit = 20) {
  return useQuery<AtRiskCustomer[]>({
    queryKey: ['churn', 'at-risk', limit],
    queryFn: async () => {
      const { data } = await api.get(`/churn/at-risk?limit=${limit}`);
      return data;
    },
  });
}

export function useFeatureImportance() {
  return useQuery<FeatureImportance[]>({
    queryKey: ['churn', 'feature-importance'],
    queryFn: async () => {
      const { data } = await api.get('/churn/feature-importance');
      return data;
    },
  });
}

// ── Recommendations ───────────────────────────────────────

export function useRecommendationSummary() {
  return useQuery<RecommendationSummary>({
    queryKey: ['recommendations', 'summary'],
    queryFn: async () => {
      const { data } = await api.get('/recommendations/summary');
      return data;
    },
  });
}

export function useTopRecommendations(limit = 20) {
  return useQuery<RecommendationItem[]>({
    queryKey: ['recommendations', 'top', limit],
    queryFn: async () => {
      const { data } = await api.get(`/recommendations/top?limit=${limit}`);
      return data;
    },
  });
}

// ── Sentiment ─────────────────────────────────────────────

export function useSentimentSummary() {
  return useQuery<SentimentSummary>({
    queryKey: ['sentiment', 'summary'],
    queryFn: async () => {
      const { data } = await api.get('/sentiment/summary');
      return data;
    },
  });
}

// ── Agent Audit ───────────────────────────────────────────

export function useAgentsSummary() {
  return useQuery<AgentsSummary>({
    queryKey: ['agents', 'summary'],
    queryFn: async () => {
      const { data } = await api.get('/agents/summary');
      return data;
    },
  });
}

// ── Customers ─────────────────────────────────────────────

export function useCustomers(limit = 50, offset = 0) {
  return useQuery<CustomerListResponse>({
    queryKey: ['customers', limit, offset],
    queryFn: async () => {
      const { data } = await api.get(`/customers?limit=${limit}&offset=${offset}`);
      return data;
    },
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
