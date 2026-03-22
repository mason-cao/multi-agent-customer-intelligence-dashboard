export interface Workspace {
  id: string;
  name: string;
  company_name: string;
  scenario: string;
  industry: string;
  customer_count: number;
  status: 'created' | 'generating' | 'ready' | 'failed';
  current_stage: string | null;
  stage_index: number | null;
  total_stages: number | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface WorkspaceListResponse {
  workspaces: Workspace[];
  total: number;
}

export interface Scenario {
  key: string;
  company_name: string;
  industry: string;
  customer_count: number;
  description: string;
  churn_rate: number;
  profile: string;
}
