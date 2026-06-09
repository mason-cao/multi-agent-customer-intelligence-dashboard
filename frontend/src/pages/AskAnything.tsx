import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import type { AxiosError } from 'axios';
import {
  Sparkles,
  Send,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Database,
  Trash2,
  ArrowRight,
  CornerDownRight,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import { CHART_COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from '../components/charts';
import { useAskQuestion, useQuerySuggestions } from '../api/hooks';
import type { QueryResult } from '../types';

const DEFAULT_EXAMPLES = [
  'Which segment has the highest churn risk?',
  'Show the top 10 highest-risk customers.',
  'Break down revenue by segment',
  'What are the most common support ticket topics?',
];

// Where each intent's full view lives, for "open in dashboard" drill-down.
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

// Preferred (label, value) fields for the distribution chart, per intent.
const DIST_FIELD: Record<string, { label: string; value: string }> = {
  churn_by_segment: { label: 'segment_name', value: 'avg_churn_prob' },
  sentiment_by_segment: { label: 'segment_name', value: 'avg_sentiment' },
  revenue_by_segment: { label: 'segment_name', value: 'total_revenue' },
  recommendation_dist: { label: 'action_label', value: 'count' },
  ticket_topics: { label: 'category', value: 'count' },
};

interface Message {
  role: 'user' | 'assistant';
  content: string;
  result?: QueryResult;
  tone?: 'default' | 'error';
}

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

function getQueryErrorMessage(error: Error): string {
  const axiosError = error as AxiosError<ApiErrorBody>;
  const detail = axiosError.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const message = detail.find((item) => typeof item.msg === 'string')?.msg;
    if (message) return message;
  }
  if (axiosError.response?.status === 404) {
    return 'This workspace data is no longer available. Return to Workspaces and choose an active workspace.';
  }
  return 'I could not complete that query. Check that the workspace data is ready and try again.';
}

// ── Value formatting ───────────────────────────────────────────

function humanizeKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatNumber(key: string, value: number): string {
  const k = key.toLowerCase();
  if (/(probability|prob|churn|sentiment|engagement|rate|pct|percent)/.test(k) && Math.abs(value) <= 1) {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (/(revenue|mrr|spend|value|amount)/.test(k)) {
    return value >= 1000
      ? `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
      : `$${value.toFixed(2)}`;
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
}

function formatCell(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number') return formatNumber(key, value);
  const str = String(value);
  return str.length > 140 ? `${str.slice(0, 137)}…` : str;
}

function formatAxis(key: string, value: number): string {
  const k = key.toLowerCase();
  if (/(probability|prob|churn|sentiment|rate)/.test(k) && Math.abs(value) <= 1) {
    return `${Math.round(value * 100)}%`;
  }
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

type Row = Record<string, unknown>;

function isRowArray(value: unknown): value is Row[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((v) => v !== null && typeof v === 'object' && !Array.isArray(v))
  );
}

// ── Structured renderers ───────────────────────────────────────

function ResultTable({ rows }: { rows: Row[] }) {
  const keys = Object.keys(rows[0] ?? {});
  const shown = rows.slice(0, 8);
  const isNumeric = (key: string) =>
    rows.every((r) => r[key] === null || r[key] === undefined || typeof r[key] === 'number');

  return (
    <div className="overflow-x-auto">
      <table className="metric-table text-xs">
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key} className={isNumeric(key) ? 'text-right' : 'text-left'}>
                {humanizeKey(key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((row, i) => (
            <tr key={i}>
              {keys.map((key) => (
                <td
                  key={key}
                  className={`text-[var(--color-text-secondary)] ${isNumeric(key) ? 'text-right font-mono' : ''}`}
                >
                  {formatCell(key, row[key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > shown.length && (
        <p className="mt-2 text-[10px] text-[var(--color-text-tertiary)]">
          Showing {shown.length} of {rows.length.toLocaleString()} rows ·{' '}
          open the dashboard for the full view.
        </p>
      )}
    </div>
  );
}

function DistributionChart({ intent, rows }: { intent: string; rows: Row[] }) {
  // Resolve the label + value fields (per-intent first, then a heuristic).
  const cols = Object.keys(rows[0] ?? {});
  let labelKey: string | undefined = DIST_FIELD[intent]?.label;
  let valueKey: string | undefined = DIST_FIELD[intent]?.value;
  if (!labelKey || !(labelKey in rows[0])) {
    labelKey = cols.find((k) => typeof rows[0][k] === 'string');
  }
  if (!valueKey || !(valueKey in rows[0])) {
    valueKey = cols.find((k) => typeof rows[0][k] === 'number');
  }
  if (!labelKey || !valueKey) return null;

  const data = rows
    .map((r) => ({ label: String(r[labelKey!]), value: Number(r[valueKey!]) || 0 }))
    .slice(0, 10);
  const height = Math.max(140, data.length * 34);
  const vk = valueKey;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 8 }}>
        <CartesianGrid {...GRID_STYLE} horizontal={false} />
        <XAxis type="number" {...AXIS_STYLE} tickFormatter={(value: unknown) => formatAxis(vk, Number(value))} />
        <YAxis type="category" dataKey="label" width={120} {...AXIS_STYLE} />
        <Tooltip
          {...TOOLTIP_STYLE}
          formatter={(value: unknown) => [formatNumber(vk, Number(value)), humanizeKey(vk)]}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function MetricGrid({ entries }: { entries: [string, unknown][] }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-lg bg-white/[0.03] px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
            {humanizeKey(key)}
          </p>
          <p className="mt-1 font-mono text-sm font-semibold text-white">
            {formatCell(key, value)}
          </p>
        </div>
      ))}
    </div>
  );
}

function KeyValueChips({ title, obj }: { title: string; obj: Record<string, unknown> }) {
  return (
    <div>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
        {title}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(obj).map(([k, v]) => (
          <span
            key={k}
            className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.04] px-2.5 py-1 text-[11px] text-[var(--color-text-secondary)]"
          >
            {humanizeKey(k)}
            <span className="font-mono text-white">{formatCell(k, v)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/** Render an object payload: scalars as a metric grid, nested arrays as
 *  tables, nested scalar dicts as chips. */
function StructuredObject({ data }: { data: Record<string, unknown> }) {
  const scalars: [string, unknown][] = [];
  const blocks: React.ReactNode[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (isRowArray(value)) {
      blocks.push(
        <div key={key}>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
            {humanizeKey(key)}
          </p>
          <ResultTable rows={value} />
        </div>
      );
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      blocks.push(<KeyValueChips key={key} title={humanizeKey(key)} obj={value as Record<string, unknown>} />);
    } else if (!Array.isArray(value)) {
      scalars.push([key, value]);
    }
  }
  return (
    <div className="space-y-3">
      {scalars.length > 0 && <MetricGrid entries={scalars} />}
      {blocks}
    </div>
  );
}

function StructuredResult({ result }: { result: QueryResult }) {
  const data = result.structured_result;
  const kind = result.result_kind;
  if (data == null || kind === 'text') return null;

  let body: React.ReactNode = null;
  if (isRowArray(data)) {
    body = (
      <>
        {kind === 'distribution' && data.length > 1 && (
          <DistributionChart intent={result.matched_intent} rows={data} />
        )}
        <ResultTable rows={data} />
      </>
    );
  } else if (data && typeof data === 'object' && !Array.isArray(data)) {
    body = <StructuredObject data={data as Record<string, unknown>} />;
  }

  if (!body) return null;
  return <div className="mt-3 space-y-3 border-t border-white/[0.06] pt-3">{body}</div>;
}

// ── Follow-ups ─────────────────────────────────────────────────

function FollowupChips({
  items,
  disabled,
  onAsk,
}: {
  items: string[];
  disabled: boolean;
  onAsk: (q: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-[var(--color-text-tertiary)]">
        <CornerDownRight className="h-3 w-3" />
        Follow up
      </span>
      {items.map((q) => (
        <button
          key={q}
          onClick={() => onAsk(q)}
          disabled={disabled}
          className="rounded-full border border-white/[0.12] bg-white/[0.03] px-2.5 py-1 text-[11px] text-[var(--color-text-secondary)] transition-colors duration-200 hover:border-primary-400/40 hover:bg-primary-400/10 hover:text-[var(--color-text-accent)] disabled:opacity-50"
        >
          {q}
        </button>
      ))}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────

export default function AskAnything() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const { mutate, isPending } = useAskQuestion();
  const { data: suggestions } = useQuerySuggestions();
  const threadEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isPending]);

  function handleSubmit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || isPending) return;

    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setQuestion('');

    mutate(trimmed, {
      onSuccess: (result) => {
        setMessages((prev) => [...prev, { role: 'assistant', content: result.answer_text, result }]);
      },
      onError: (error) => {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: getQueryErrorMessage(error), tone: 'error' },
        ]);
      },
    });
  }

  function clearThread() {
    setMessages([]);
  }

  const hasMessages = messages.length > 0;
  const promptExamples = (suggestions?.length ? suggestions.map((s) => s.example) : DEFAULT_EXAMPLES);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between">
        <PageHeader title="Ask Anything" description="Natural language intelligence queries" />
        {hasMessages && (
          <button
            onClick={clearThread}
            className="flex items-center gap-1.5 text-xs text-[var(--color-text-tertiary)] transition hover:text-[var(--color-text-secondary)]"
          >
            <Trash2 className="h-3 w-3" />
            Clear thread
          </button>
        )}
      </div>

      {/* Conversation thread */}
      <div className="flex-1 overflow-y-auto pb-4">
        {!hasMessages && !isPending ? (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-400/10 ring-1 ring-primary-400/15">
              <Sparkles className="h-7 w-7 text-[var(--color-primary-400)]" />
            </div>
            <h3 className="mt-5 text-sm font-semibold text-white">
              Ask a question about your data
            </h3>
            <p className="mt-1.5 max-w-md text-center text-[13px] leading-relaxed text-[var(--color-text-tertiary)]">
              Query your customer intelligence in natural language. Results render as
              charts, tables, and metrics — pick a starting point:
            </p>
            <div className="mt-6 grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
              {(suggestions ?? []).slice(0, 6).map((s) => (
                <button
                  key={s.intent}
                  onClick={() => handleSubmit(s.example)}
                  disabled={isPending}
                  className="glass-hover group flex items-center justify-between gap-3 rounded-xl px-4 py-3 text-left disabled:opacity-50"
                >
                  <span>
                    <span className="block text-xs font-semibold text-white">{s.label}</span>
                    <span className="mt-0.5 block text-[11px] text-[var(--color-text-tertiary)]">
                      {s.example}
                    </span>
                  </span>
                  <ArrowRight className="h-4 w-4 shrink-0 text-[var(--color-text-tertiary)] transition-colors group-hover:text-[var(--color-primary-400)]" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) =>
              msg.role === 'user' ? (
                <UserBubble key={idx} content={msg.content} />
              ) : (
                <AssistantBubble key={idx} message={msg} disabled={isPending} onAsk={handleSubmit} />
              )
            )}

            {isPending && (
              <div className="flex items-start gap-3">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-400/15">
                  <Sparkles className="h-3.5 w-3.5 text-[var(--color-primary-400)]" />
                </div>
                <Card className="max-w-lg">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-[var(--color-primary-400)]" />
                    <span className="text-sm text-[var(--color-text-secondary)]">Thinking…</span>
                  </div>
                </Card>
              </div>
            )}

            <div ref={threadEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="mt-auto border-t border-white/[0.06] pt-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {promptExamples.slice(0, 5).map((q) => (
            <button
              key={q}
              onClick={() => handleSubmit(q)}
              disabled={isPending}
              className="rounded-full border border-white/[0.12] bg-white/[0.035] px-3 py-1.5 text-[11px] text-[var(--color-text-secondary)] transition-all duration-200 hover:border-primary-400/40 hover:bg-primary-400/10 hover:text-[var(--color-text-accent)] disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        <Card variant="hero">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 shrink-0 text-[var(--color-primary-400)]" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit(question)}
              placeholder="Ask a question about your customers…"
              disabled={isPending}
              aria-label="Ask a question about your customers"
              className="glass-input flex-1 disabled:opacity-50"
            />
            <button
              onClick={() => handleSubmit(question)}
              disabled={isPending || !question.trim()}
              aria-label="Send question"
              className="btn-primary py-2.5 disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0"
            >
              {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Message bubbles ────────────────────────────────────────────

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="glass-surface max-w-md rounded-2xl rounded-br-md px-4 py-3">
        <p className="text-sm text-white">{content}</p>
      </div>
    </div>
  );
}

function AssistantBubble({
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

        {/* Metadata footer */}
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
