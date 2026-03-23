import { useState } from 'react';
import { Users, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import EmptyState from '../components/shared/EmptyState';
import { useCustomers } from '../api/hooks';
import { SEGMENT_COLORS, RISK_COLORS } from '../utils/colors';
import { formatCurrency } from '../utils/formatters';

const PAGE_SIZE = 25;

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded bg-slate-200 animate-pulse ${className}`} />;
}

export default function Customer360() {
  const [page, setPage] = useState(0);
  const offset = page * PAGE_SIZE;
  const { data, isLoading, isError } = useCustomers(PAGE_SIZE, offset);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div>
      <PageHeader
        title="Customer 360 Explorer"
        description="Deep-dive into individual customer profiles, behavior, and AI analysis"
      />

      {isLoading ? (
        <Card>
          <div className="space-y-3">
            {Array.from({ length: 10 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </Card>
      ) : isError || !data ? (
        <Card className="border-red-100 bg-red-50/40">
          <p className="flex items-center gap-2 text-sm text-red-600">
            <AlertTriangle className="h-4 w-4" />
            Failed to load customer data.
          </p>
        </Card>
      ) : data.customers.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No customer profiles found"
          description="Customer profiles will appear here once the intelligence pipeline has processed this workspace's data."
        />
      ) : (
        <>
          {/* Summary bar */}
          <Card className="mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-emerald-600" />
                <span className="text-sm font-semibold text-slate-700">
                  {data.total.toLocaleString()} customers
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="rounded-lg border border-slate-200 p-1.5 text-slate-400 transition hover:bg-slate-50 disabled:opacity-30"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-slate-500">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-lg border border-slate-200 p-1.5 text-slate-400 transition hover:bg-slate-50 disabled:opacity-30"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </Card>

          {/* Customer table */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-xs text-slate-400">
                    <th className="pb-2 font-medium">Name</th>
                    <th className="pb-2 font-medium">Company</th>
                    <th className="pb-2 font-medium">Plan</th>
                    <th className="pb-2 font-medium">Segment</th>
                    <th className="pb-2 font-medium text-right">Revenue</th>
                    <th className="pb-2 font-medium text-right">Engagement</th>
                    <th className="pb-2 font-medium text-right">Churn %</th>
                    <th className="pb-2 font-medium">Risk</th>
                    <th className="pb-2 font-medium text-right">Sentiment</th>
                  </tr>
                </thead>
                <tbody>
                  {data.customers.map((c) => (
                    <tr
                      key={c.customer_id}
                      className="border-b border-slate-50 last:border-0 transition-colors hover:bg-slate-50/50"
                    >
                      <td className="py-2.5 font-medium text-slate-700">
                        {c.name}
                      </td>
                      <td className="py-2.5 text-slate-500">{c.company}</td>
                      <td className="py-2.5">
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-500">
                          {c.plan_tier}
                        </span>
                      </td>
                      <td className="py-2.5">
                        {c.segment_name ? (
                          <span className="inline-flex items-center gap-1 text-xs">
                            <span
                              className="h-2 w-2 rounded-full"
                              style={{
                                backgroundColor:
                                  SEGMENT_COLORS[c.segment_name] ?? '#6b7280',
                              }}
                            />
                            <span className="text-slate-600">{c.segment_name}</span>
                          </span>
                        ) : (
                          <span className="text-xs text-slate-300">—</span>
                        )}
                      </td>
                      <td className="py-2.5 text-right text-slate-600">
                        {c.total_revenue != null
                          ? formatCurrency(c.total_revenue)
                          : '—'}
                      </td>
                      <td className="py-2.5 text-right text-slate-600">
                        {c.engagement_score != null
                          ? c.engagement_score.toFixed(2)
                          : '—'}
                      </td>
                      <td className="py-2.5 text-right text-slate-600">
                        {c.churn_probability != null
                          ? `${(c.churn_probability * 100).toFixed(1)}%`
                          : '—'}
                      </td>
                      <td className="py-2.5">
                        {c.risk_tier ? (
                          <span
                            className="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold text-white"
                            style={{
                              backgroundColor:
                                RISK_COLORS[c.risk_tier.toLowerCase()] ?? '#6b7280',
                            }}
                          >
                            {c.risk_tier}
                          </span>
                        ) : (
                          <span className="text-xs text-slate-300">—</span>
                        )}
                      </td>
                      <td className="py-2.5 text-right">
                        {c.avg_sentiment != null ? (
                          <span
                            className="font-semibold"
                            style={{
                              color:
                                c.avg_sentiment > 0.2
                                  ? '#10b981'
                                  : c.avg_sentiment > -0.2
                                    ? '#9ca3af'
                                    : '#ef4444',
                            }}
                          >
                            {c.avg_sentiment.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-xs text-slate-300">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
