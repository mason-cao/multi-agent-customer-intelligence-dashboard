export interface Customer {
  customer_id: string;
  name: string;
  email: string;
  company: string;
  industry: string;
  company_size?: string;
  plan_tier: string;
  signup_date: string;
  region: string;
  acquisition_channel?: string;
  is_churned: boolean;
  churned_date: string | null;
}

export interface KpiData {
  label: string;
  value: string | number;
  trend: number;
  trend_label: string;
}

export interface AgentRun {
  id: string;
  agent_name: string;
  run_id: string;
  status: 'running' | 'completed' | 'failed' | 'partial';
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  tokens_used: number | null;
  model_used: string | null;
}

// Segments
export interface SegmentSummary {
  segment_id: number;
  segment_name: string;
  customer_count: number;
  avg_revenue: number;
  avg_engagement: number;
  avg_churn_risk: number;
}

// Churn
export interface ChurnDistribution {
  risk_tier: string;
  count: number;
  mrr_at_risk: number;
}

export interface AtRiskCustomer {
  customer_id: string;
  name: string;
  company: string;
  churn_probability: number;
  risk_tier: string;
  top_risk_factor: string;
  mrr: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

// Recommendations
export interface RecommendationSummary {
  total_recommendations: number;
  action_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
  avg_urgency: number;
  timeframe_distribution: Record<string, number>;
}

export interface RecommendationItem {
  recommendation_id: string;
  customer_id: string;
  action_code: string;
  action_label: string;
  action_category: string;
  action_priority: number;
  urgency_score: number;
  confidence: string;
  primary_driver: string;
  secondary_driver: string | null;
  reasoning: string;
  recommended_channel: string;
  recommended_owner: string;
  target_timeframe: string;
}

// Sentiment
export interface TopicSummary {
  topic: string;
  count: number;
  avg_sentiment: number;
}

export interface SentimentSummary {
  distribution: Record<string, number>;
  avg_score: number;
  total: number;
  topics: TopicSummary[];
}

// Agent Audit
export interface AuditCheck {
  audit_id: string;
  check_category: string;
  check_name: string;
  severity: string;
  passed: boolean;
  audit_message: string;
}

export interface AuditSummaryData {
  total_checks: number;
  passed: number;
  failed: number;
  critical_failures: number;
  warnings: number;
  check_categories: Record<string, { passed: number; total: number }>;
}

export interface AgentsSummary {
  audit: AuditSummaryData;
  runs: AgentRun[];
  checks: AuditCheck[];
}

// Customer list
export interface CustomerDetail {
  customer_id: string;
  name: string;
  email: string;
  company: string;
  industry: string;
  plan_tier: string;
  signup_date: string;
  region: string;
  is_churned: boolean;
  engagement_score: number | null;
  total_revenue: number | null;
  segment_name: string | null;
  churn_probability: number | null;
  risk_tier: string | null;
  avg_sentiment: number | null;
}

export interface CustomerListResponse {
  customers: CustomerDetail[];
  total: number;
}

// Query
export interface QueryResult {
  query_id: string;
  original_question: string;
  matched_intent: string;
  query_status: string;
  answer_text: string;
  structured_result: unknown | null;
  source_tables: string | null;
  row_count: number | null;
  execution_ms: number | null;
  query_version: string;
  executed_at: string;
}
