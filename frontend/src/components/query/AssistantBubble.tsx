import { Link } from 'react-router-dom';
import { Sparkles, CheckCircle, AlertCircle, Clock, Database, ArrowRight } from 'lucide-react';
import Card from '../../components/shared/Card';
import type { Message } from './messages';
import StructuredResult from './StructuredResult';
import FollowupChips from './FollowupChips';

const INTENT_ROUTE: Record<string, { to: string; label: string }> = {
  top_risk_customers: { to: '/churn', label: 'Open Churn & Retention' },
  high_risk_negative: { to: '/churn', label: 'Open Churn & Retention' },
  churn_by_segment: { to: '/churn', label: 'Open Churn & Retention' },
  customer_lookup: { to: '/customers', label: 'Open Customer 360' },
  industry_breakdown: { to: '/customers', label: 'Open Customer 360' },
  segment_overview: { to: '/segments', label: 'Open Segments' },
  revenue_by_segment: { to: '/segments', label: 'Open Segments' },
  sentiment_by_segment: { to: '/sentiment', label: 'Open Sentiment & Support' },
  ticket_topics: { to: '/sentiment', label: 'Open Sentiment & Support' },
  recommendation_dist: { to: '/recommendations', label: 'Open Recommendations' },
  priority_actions: { to: '/recommendations', label: 'Open Recommendations' },
  executive_insights: { to: '/', label: 'Open Overview' },
  customer_summary: { to: '/', label: 'Open Overview' },
  audit_findings: { to: '/agents', label: 'Open Agent Audit' },
};

export default function AssistantBubble({
  message,
  disabled,
  onAsk,
}: {
  message: Message;
  disabled: boolean;
  onAsk: (q: string) => void;
}) {
  const result = message.result;
  const isError = message.tone === 'error' || result?.query_status === 'error';
  const drill = result && result.query_status === 'success' ? INTENT_ROUTE[result.matched_intent] : undefined;
  const followups = result?.suggested_followups ?? [];

  return (
    <div className="flex items-start gap-3">
      <div
        className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full ${
          isError ? 'bg-danger/15' : 'bg-primary-400/15'
        }`}
      >
        {isError ? (
          <AlertCircle className="h-3.5 w-3.5 text-[var(--color-danger)]" />
        ) : (
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-primary-400)]" />
        )}
      </div>

      <Card className={`w-full max-w-2xl ${isError ? 'border-danger/20 bg-danger/10' : ''}`}>
        <p
          className={`whitespace-pre-line text-sm leading-relaxed ${
            isError ? 'text-danger' : 'text-[var(--color-text-secondary)]'
          }`}
        >
          {message.content}
        </p>

        {result && <StructuredResult result={result} />}

        {result && followups.length > 0 && (
          <FollowupChips items={followups} disabled={disabled} onAsk={onAsk} />
        )}

        {result && (
          <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-white/[0.06] pt-3 text-[10px] text-[var(--color-text-tertiary)]">
            <span className="flex items-center gap-1">
              {result.query_status === 'success' ? (
                <CheckCircle className="h-3 w-3 text-[var(--color-success)]" />
              ) : (
                <AlertCircle className="h-3 w-3 text-[var(--color-warning)]" />
              )}
              {result.matched_intent.replace(/_/g, ' ')}
            </span>
            {result.execution_ms != null && (
              <span className="flex items-center gap-1 font-mono">
                <Clock className="h-3 w-3" />
                {result.execution_ms}ms
              </span>
            )}
            {result.source_tables && (
              <span className="flex items-center gap-1">
                <Database className="h-3 w-3" />
                {result.source_tables}
              </span>
            )}
            {drill && (
              <Link
                to={drill.to}
                className="ml-auto flex items-center gap-1 font-medium text-[var(--color-text-accent)] transition-colors hover:text-[var(--color-primary-400)]"
              >
                {drill.label}
                <ArrowRight className="h-3 w-3" />
              </Link>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
