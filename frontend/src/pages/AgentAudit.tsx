import { ShieldCheck } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import EmptyState from '../components/shared/EmptyState';

export default function AgentAudit() {
  return (
    <div>
      <PageHeader
        title="Agent Audit & Explainability"
        description="Transparency into how AI agents reached their conclusions"
      />
      <EmptyState
        icon={ShieldCheck}
        title="Agent audit trail"
        description="Execution history, validation results, timing, and token usage for each AI agent will appear here once agents have been run."
      />
    </div>
  );
}
