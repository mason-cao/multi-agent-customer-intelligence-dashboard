import { ShieldCheck, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import EmptyState from '../components/shared/EmptyState';
import { AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from '../components/charts';
import { useAgentsSummary } from '../api/hooks';

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-[rgba(248,113,113,0.15)] text-[#f87171]',
  warning: 'bg-[rgba(251,191,36,0.15)] text-[#fbbf24]',
  info: 'bg-[rgba(148,163,184,0.15)] text-[#94a3b8]',
};

const DEFAULT_SEVERITY = 'bg-[rgba(148,163,184,0.15)] text-[#94a3b8]';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded-md shimmer ${className}`} />;
}

export default function AgentAudit() {
  const { data, isLoading, isError } = useAgentsSummary();

  // Build chart data from check_categories
  const categoryChartData = data
    ? Object.entries(data.audit.check_categories).map(([cat, stats]) => ({
        category: cat,
        passed: stats.passed,
        failed: stats.total - stats.passed,
      }))
    : [];

  return (
    <div>
      <PageHeader
        title="Agent Audit & Explainability"
        description="Transparency into how AI agents reached their conclusions"
      />

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}><Skeleton className="h-20 w-full" /></Card>
            ))}
          </div>
          <Card><Skeleton className="h-64 w-full" /></Card>
        </div>
      ) : isError ? (
        <Card className="border-[rgba(248,113,113,0.2)] bg-[rgba(248,113,113,0.1)]">
          <p className="flex items-center gap-2 text-sm text-[rgba(248,113,113,0.9)]">
            <AlertTriangle className="h-4 w-4" />
            Failed to load audit data.
          </p>
        </Card>
      ) : !data ? (
        <EmptyState
          icon={ShieldCheck}
          title="No audit data available"
          description="Audit results and agent run history will appear here once the intelligence pipeline has completed for this workspace."
        />
      ) : (
        <>
          {/* Audit KPIs */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                Total Checks
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-white">
                {data.audit.total_checks}
              </p>
            </Card>
            <Card hover style={{ '--glass-hover-glow': 'rgba(52,211,153,0.12)' } as React.CSSProperties}>
              <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                Passed
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-[#34d399]">
                {data.audit.passed}
              </p>
            </Card>
            <Card hover style={{ '--glass-hover-glow': 'rgba(248,113,113,0.12)' } as React.CSSProperties}>
              <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                Failed
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-[#f87171]">
                {data.audit.failed}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                Pass Rate
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-[#34d399]">
                {data.audit.total_checks > 0
                  ? ((data.audit.passed / data.audit.total_checks) * 100).toFixed(0)
                  : 0}%
              </p>
            </Card>
          </div>

          {/* Category breakdown + Agent runs */}
          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Category breakdown — Recharts stacked bar chart */}
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[#34d399]" />
                <h3 className="text-sm font-semibold text-white">
                  Checks by Category
                </h3>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  layout="vertical"
                  data={categoryChartData}
                  margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
                >
                  <CartesianGrid {...GRID_STYLE} horizontal={false} />
                  <XAxis
                    type="number"
                    {...AXIS_STYLE}
                    tickFormatter={(value: unknown) => String(value)}
                  />
                  <YAxis
                    type="category"
                    dataKey="category"
                    width={100}
                    {...AXIS_STYLE}
                    tickFormatter={(value: unknown) => String(value)}
                    style={{ textTransform: 'capitalize' }}
                  />
                  <Tooltip
                    {...TOOLTIP_STYLE}
                    formatter={(value: unknown, name: unknown) => [
                      String(value),
                      String(name) === 'passed' ? 'Passed' : 'Failed',
                    ]}
                  />
                  <Bar
                    dataKey="passed"
                    stackId="a"
                    fill="#34d399"
                    radius={[0, 0, 0, 0]}
                    barSize={16}
                  />
                  <Bar
                    dataKey="failed"
                    stackId="a"
                    fill="#f87171"
                    radius={[0, 4, 4, 0]}
                    barSize={16}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            {/* Agent runs */}
            <Card className="xl:col-span-2">
              <div className="mb-4 flex items-center gap-2">
                <Clock className="h-4 w-4 text-[#818cf8]" />
                <h3 className="text-sm font-semibold text-white">
                  Latest Agent Runs
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-[rgba(255,255,255,0.1)] text-xs text-[rgba(255,255,255,0.45)]">
                      <th className="pb-2 font-medium">Agent</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium text-right">Duration</th>
                      <th className="pb-2 font-medium text-right">Tokens</th>
                      <th className="pb-2 font-medium">Completed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.runs.length ? (
                      data.runs.map((r) => (
                        <tr
                          key={r.id}
                          className="border-b border-[rgba(255,255,255,0.06)] transition-colors hover:bg-[rgba(255,255,255,0.04)] last:border-0"
                        >
                          <td className="py-2.5 font-medium capitalize text-white">
                            {r.agent_name}
                          </td>
                          <td className="py-2.5">
                            {r.status === 'completed' ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-[#34d399]">
                                <CheckCircle className="h-3.5 w-3.5" />
                                Completed
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-[#f87171]">
                                <XCircle className="h-3.5 w-3.5" />
                                {r.status}
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 text-right font-mono text-[rgba(255,255,255,0.7)]">
                            {r.duration_ms != null
                              ? r.duration_ms >= 1000
                                ? `${(r.duration_ms / 1000).toFixed(1)}s`
                                : `${r.duration_ms}ms`
                              : '—'}
                          </td>
                          <td className="py-2.5 text-right font-mono text-[rgba(255,255,255,0.7)]">
                            {r.tokens_used ?? 0}
                          </td>
                          <td className="py-2.5 text-xs text-[rgba(255,255,255,0.45)]">
                            {r.completed_at
                              ? new Date(r.completed_at).toLocaleString()
                              : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-sm text-[rgba(255,255,255,0.45)]">
                          No agent runs recorded
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          {/* Detailed checks */}
          <Card className="mt-6">
            <div className="mb-4 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#34d399]" />
              <h3 className="text-sm font-semibold text-white">
                All Audit Checks
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[rgba(255,255,255,0.1)] text-xs text-[rgba(255,255,255,0.45)]">
                    <th className="pb-2 font-medium">Category</th>
                    <th className="pb-2 font-medium">Check</th>
                    <th className="pb-2 font-medium">Severity</th>
                    <th className="pb-2 font-medium">Result</th>
                    <th className="pb-2 font-medium">Message</th>
                  </tr>
                </thead>
                <tbody>
                  {data.checks.length ? (
                    data.checks.map((c) => (
                      <tr
                        key={c.audit_id}
                        className="border-b border-[rgba(255,255,255,0.06)] transition-colors hover:bg-[rgba(255,255,255,0.04)] last:border-0"
                      >
                        <td className="py-2 text-xs font-medium capitalize text-[rgba(255,255,255,0.7)]">
                          {c.check_category}
                        </td>
                        <td className="py-2 text-xs text-white">
                          {c.check_name}
                        </td>
                        <td className="py-2">
                          <span
                            className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${SEVERITY_BADGE[c.severity] ?? DEFAULT_SEVERITY}`}
                          >
                            {c.severity}
                          </span>
                        </td>
                        <td className="py-2">
                          {c.passed ? (
                            <CheckCircle className="h-4 w-4 text-[#34d399]" />
                          ) : (
                            <XCircle className="h-4 w-4 text-[#f87171]" />
                          )}
                        </td>
                        <td className="max-w-sm truncate py-2 text-xs text-[rgba(255,255,255,0.7)]">
                          {c.audit_message}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-sm text-[rgba(255,255,255,0.45)]">
                        No audit checks recorded
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
