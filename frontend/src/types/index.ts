export interface Customer {
  customer_id: string;
  name: string;
  email: string;
  company: string;
  industry: string;
  company_size: string;
  plan_tier: string;
  signup_date: string;
  region: string;
  acquisition_channel: string;
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
