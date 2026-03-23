import { ShieldCheck, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import EmptyState from '../components/shared/EmptyState';
import { useAgentsSummary } from '../api/hooks';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded bg-slate-200 animate-pulse ${className}`} />;
}

export default function AgentAudit() {
  const { data, isLoading, isError } = useAgentsSummary();

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
        <Card className="border-red-100 bg-red-50/40">
          <p className="flex items-center gap-2 text-sm text-red-600">
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
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Total Checks
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {data.audit.total_checks}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Passed
              </p>
              <p className="mt-2 text-3xl font-bold text-emerald-600">
                {data.audit.passed}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Failed
              </p>
              <p className="mt-2 text-3xl font-bold text-red-500">
                {data.audit.failed}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Pass Rate
              </p>
              <p className="mt-2 text-3xl font-bold text-emerald-600">
                {data.audit.total_checks > 0
                  ? ((data.audit.passed / data.audit.total_checks) * 100).toFixed(0)
                  : 0}%
              </p>
            </Card>
          </div>

          {/* Category breakdown + Agent runs */}
          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Category breakdown */}
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Checks by Category
                </h3>
              </div>
              <div className="space-y-3">
                {Object.entries(data.audit.check_categories).map(([cat, stats]) => (
                  <div key={cat}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-600 capitalize">
                        {cat}
                      </span>
                      <span className="text-slate-400">
                        {stats.passed}/{stats.total}
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full transition-all"
                        style={{
                          width: `${stats.total > 0 ? (stats.passed / stats.total) * 100 : 0}%`,
                          backgroundColor:
                            stats.passed === stats.total ? '#10b981' : '#ef4444',
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {/* Agent runs */}
            <Card className="xl:col-span-2">
              <div className="mb-4 flex items-center gap-2">
                <Clock className="h-4 w-4 text-emerald-600" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Latest Agent Runs
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs text-slate-400">
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
                          className="border-b border-slate-50 last:border-0"
                        >
                          <td className="py-2.5 font-medium capitalize text-slate-700">
                            {r.agent_name}
                          </td>
                          <td className="py-2.5">
                            {r.status === 'completed' ? (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                                <CheckCircle className="h-3.5 w-3.5" />
                                Completed
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-xs font-medium text-red-500">
                                <XCircle className="h-3.5 w-3.5" />
                                {r.status}
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 text-right text-slate-600">
                            {r.duration_ms != null
                              ? r.duration_ms >= 1000
                                ? `${(r.duration_ms / 1000).toFixed(1)}s`
                                : `${r.duration_ms}ms`
                              : '—'}
                          </td>
                          <td className="py-2.5 text-right text-slate-600">
                            {r.tokens_used ?? 0}
                          </td>
                          <td className="py-2.5 text-xs text-slate-400">
                            {r.completed_at
                              ? new Date(r.completed_at).toLocaleString()
                              : '—'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-sm text-slate-400">
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
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <h3 className="text-sm font-semibold text-slate-700">
                All Audit Checks
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs text-slate-400">
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
                        className="border-b border-slate-50 last:border-0"
                      >
                        <td className="py-2 text-xs font-medium text-slate-600 capitalize">
                          {c.check_category}
                        </td>
                        <td className="py-2 text-xs text-slate-700">
                          {c.check_name}
                        </td>
                        <td className="py-2">
                          <span
                            className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                              c.severity === 'critical'
                                ? 'bg-red-50 text-red-600'
                                : c.severity === 'warning'
                                  ? 'bg-amber-50 text-amber-600'
                                  : 'bg-slate-50 text-slate-500'
                            }`}
                          >
                            {c.severity}
                          </span>
                        </td>
                        <td className="py-2">
                          {c.passed ? (
                            <CheckCircle className="h-4 w-4 text-emerald-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                        </td>
                        <td className="max-w-sm truncate py-2 text-xs text-slate-500">
                          {c.audit_message}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-sm text-slate-400">
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
