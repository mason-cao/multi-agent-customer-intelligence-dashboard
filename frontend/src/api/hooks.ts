import { useQuery, useMutation } from '@tanstack/react-query';
import api from './client';
import { useActiveWorkspace } from '../contexts/workspaceContextValue';
import { useWorkspaceQuery } from './workspaceQueries';
import { getWorkspaceCredentials } from './client';
import type {
  KpiData,
  OverviewTrends,
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
  QuerySuggestion,
} from '../types';


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
    queryFn: ({ signal }) => api.get('/health', { signal }),
  });
}

export function useOverviewKpis() {
  return useWorkspaceQuery<OverviewKpis>('/overview/kpis', ['overview', 'kpis']);
}

export function useOverviewNarrative() {
  return useWorkspaceQuery<NarrativeResponse>('/overview/narrative', ['overview', 'narrative']);
}

export function useOverviewTrends() {
  return useWorkspaceQuery<OverviewTrends>('/overview/trends', ['overview', 'trends']);
}


export function useSegmentSummary() {
  return useWorkspaceQuery<SegmentSummary[]>('/segments/summary', ['segments', 'summary']);
}


export function useChurnDistribution() {
  return useWorkspaceQuery<ChurnDistribution[]>('/churn/distribution', ['churn', 'distribution']);
}

export function useAtRiskCustomers(limit = 20) {
  return useWorkspaceQuery<AtRiskCustomer[]>(`/churn/at-risk?limit=${limit}`, ['churn', 'at-risk', limit]);
}

export function useFeatureImportance() {
  return useWorkspaceQuery<FeatureImportance[]>('/churn/feature-importance', ['churn', 'feature-importance']);
}


export function useRecommendationSummary() {
  return useWorkspaceQuery<RecommendationSummary>('/recommendations/summary', ['recommendations', 'summary']);
}

export function useTopRecommendations(limit = 20) {
  return useWorkspaceQuery<RecommendationItem[]>(`/recommendations/top?limit=${limit}`, ['recommendations', 'top', limit]);
}


export function useSentimentSummary() {
  return useWorkspaceQuery<SentimentSummary>('/sentiment/summary', ['sentiment', 'summary']);
}


export function useAgentsSummary() {
  return useWorkspaceQuery<AgentsSummary>('/agents/summary', ['agents', 'summary']);
}


export function useCustomers(limit = 50, offset = 0, q = '') {
  const search = q.trim();
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (search) params.set('q', search);
  return useWorkspaceQuery<CustomerListResponse>(
    `/customers?${params}`, ['customers', limit, offset, search], true,
  );
}


export function useAskQuestion() {
  const { activeWorkspace } = useActiveWorkspace();
  const stored = getWorkspaceCredentials();
  const workspace = activeWorkspace ? {
    id: activeWorkspace.id,
    token: activeWorkspace.access_token ?? (stored?.id === activeWorkspace.id ? stored.token : null),
  } : undefined;
  return useMutation<QueryResult, Error, string>({
    mutationFn: (question) => api.post<QueryResult>('/query', { question }, { workspace }),
  });
}

export function useQuerySuggestions() {
  // Suggestions come from the static intent registry, so they don't depend on
  // the active workspace and can be cached for the session.
  return useQuery<QuerySuggestion[]>({
    queryKey: ['query', 'suggestions'],
    queryFn: ({ signal }) => api.get<QuerySuggestion[]>('/query/suggestions', { signal }),
    staleTime: Infinity,
  });
}
