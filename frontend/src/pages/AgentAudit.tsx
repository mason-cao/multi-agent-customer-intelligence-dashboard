import { ShieldCheck, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
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
import StatCard from '../components/shared/StatCard';
import ChartCard from '../components/shared/ChartCard';
import EmptyState from '../components/shared/EmptyState';
import { AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from '../components/charts';
import Badge, { type BadgeTone } from '../components/shared/Badge';
import { PALETTE } from '../utils/colors';
import { useAgentsSummary } from '../api/hooks';

const SEVERITY_TONE: Record<string, BadgeTone> = {
  critical: 'danger',
  warning: 'warning',
  info: 'muted',
};

// Per-agent run outcome → tone + icon, so the runs table reflects the real
// pipeline state (including degraded "partial" runs), not just pass/fail.
const RUN_STATUS: Record<string, { tone: BadgeTone; icon: LucideIcon; label: string }> = {
  completed: { tone: 'success', icon: CheckCircle, label: 'Completed' },
  partial: { tone: 'warning', icon: AlertTriangle, label: 'Partial' },
  failed: { tone: 'danger', icon: XCircle, label: 'Failed' },
  running: { tone: 'info', icon: Clock, label: 'Running' },
};

function RunStatusBadge({ status }: { status: string }) {
  const meta = RUN_STATUS[status] ?? { tone: 'muted' as BadgeTone, icon: Clock, label: status };
  return <Badge tone={meta.tone} icon={meta.icon} label={meta.label} size="md" className="capitalize" />;
}

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
        description="Transparency into how each pipeline stage reached its conclusions"
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
        <Card className="border-danger/20 bg-danger/10">
          <p className="flex items-center gap-2 text-sm text-danger">
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
            <StatCard title="Total Checks" value={data.audit.total_checks} variant="default" />
            <StatCard title="Passed" value={data.audit.passed} glowColor="color-mix(in oklab, var(--color-success) 14%, transparent)" variant="default" />
            <StatCard title="Failed" value={data.audit.failed} glowColor="color-mix(in oklab, var(--color-danger) 14%, transparent)" variant="default" />
            <StatCard
              title="Pass Rate"
              value={`${data.audit.total_checks > 0 ? ((data.audit.passed / data.audit.total_checks) * 100).toFixed(0) : 0}%`}
              variant="default"
            />
          </div>

          {/* Category breakdown + Agent runs */}
          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Category breakdown — Recharts stacked bar chart */}
            <ChartCard title="Checks by Category" icon={ShieldCheck}>
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
                    fill={PALETTE.success}
                    radius={[0, 0, 0, 0]}
                    barSize={16}
                  />
                  <Bar
                    dataKey="failed"
                    stackId="a"
                    fill={PALETTE.danger}
                    radius={[0, 4, 4, 0]}
                    barSize={16}
                  />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Agent runs */}
            <ChartCard title="Latest Agent Runs" icon={Clock} className="xl:col-span-2">
              <div className="overflow-x-auto">
                <table className="metric-table min-w-[760px] text-left text-sm">
                  <thead>
                    <tr>
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
                          className="border-b border-white/[0.06] transition-colors hover:bg-white/5 last:border-0"
                        >
                          <td className="py-2.5 font-medium capitalize text-white">
                            {r.agent_name}
                          </td>
                          <td className="py-2.5">
                            <RunStatusBadge status={r.status} />
                          </td>
                          <td className="py-2.5 text-right font-mono text-[var(--color-text-secondary)]">
                            {r.duration_ms != null
                              ? r.duration_ms >= 1000
                                ? `${(r.duration_ms / 1000).toFixed(1)}s`
                                : `${r.duration_ms}ms`
                              : '—'}
                          </td>
                          <td className="py-2.5 text-right font-mono text-[var(--color-text-secondary)]">
                            {r.tokens_used ?? 0}
                          </td>
                          <td className="py-2.5 text-xs text-[var(--color-text-tertiary)]">
                            {r.completed_at
                              ? new Date(r.completed_at).toLocaleString()
                              : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-sm text-[var(--color-text-tertiary)]">
                          No agent runs recorded
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          </div>

          {/* Detailed checks */}
          <Card className="mt-6">
            <div className="panel-title-bar">
              <ShieldCheck className="h-4 w-4 text-success" />
              <h3 className="text-sm font-semibold">
                All Audit Checks
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="metric-table min-w-[860px] text-left text-sm">
                <thead>
                  <tr>
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
                        className="border-b border-white/[0.06] transition-colors hover:bg-white/5 last:border-0"
                      >
                        <td className="py-2 text-xs font-medium capitalize text-[var(--color-text-secondary)]">
                          {c.check_category}
                        </td>
                        <td className="py-2 text-xs text-white">
                          {c.check_name}
                        </td>
                        <td className="py-2">
                          <Badge
                            tone={SEVERITY_TONE[c.severity] ?? 'muted'}
                            label={c.severity}
                            size="md"
                            className="min-w-16 justify-center capitalize"
                          />
                        </td>
                        <td className="py-2">
                          {c.passed ? (
                            <CheckCircle className="h-4 w-4 text-success" />
                          ) : (
                            <XCircle className="h-4 w-4 text-danger" />
                          )}
                        </td>
                        <td className="max-w-sm truncate py-2 text-xs text-[var(--color-text-secondary)]">
                          {c.audit_message}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-sm text-[var(--color-text-tertiary)]">
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
