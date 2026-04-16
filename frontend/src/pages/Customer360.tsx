import { useState } from 'react';
import { Users, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import EmptyState from '../components/shared/EmptyState';
import { useCustomers } from '../api/hooks';
import { SEGMENT_COLORS, RISK_COLORS } from '../utils/colors';
import { formatCurrency } from '../utils/formatters';

const PAGE_SIZE = 25;

const RISK_BG: Record<string, string> = {
  low: 'rgba(52,211,153,0.15)',
  medium: 'rgba(251,191,36,0.15)',
  high: 'rgba(251,146,60,0.15)',
  critical: 'rgba(248,113,113,0.15)',
};

function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      className={`rounded-md shimmer ${className}`}
    />
  );
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
        <Card className="border-[rgba(248,113,113,0.2)] bg-[rgba(248,113,113,0.1)]">
          <p className="flex items-center gap-2 text-sm text-[rgba(248,113,113,0.9)]">
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
                <Users className="h-4 w-4 text-[var(--color-primary-400)]" />
                <span className="text-sm font-semibold text-white">
                  {data.total.toLocaleString()} customers
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="rounded-lg border border-[rgba(255,255,255,0.15)] p-1.5 text-[rgba(255,255,255,0.5)] transition hover:bg-[rgba(255,255,255,0.08)] hover:text-[rgba(255,255,255,0.8)] disabled:opacity-30"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="rounded-md bg-[rgba(255,255,255,0.04)] px-2.5 py-1 font-mono text-xs text-[rgba(255,255,255,0.62)]">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-lg border border-[rgba(255,255,255,0.15)] p-1.5 text-[rgba(255,255,255,0.5)] transition hover:bg-[rgba(255,255,255,0.08)] hover:text-[rgba(255,255,255,0.8)] disabled:opacity-30"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </Card>

          {/* Customer table */}
          <Card>
            <div className="overflow-x-auto">
              <table className="metric-table min-w-[920px] text-left text-sm">
                <thead>
                  <tr>
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
                      className="border-b border-[rgba(255,255,255,0.06)] last:border-0 transition-colors hover:bg-[rgba(255,255,255,0.04)]"
                    >
                      <td className="py-2.5 font-medium text-white">
                        {c.name}
                      </td>
                      <td className="py-2.5 text-[rgba(255,255,255,0.6)]">
                        {c.company}
                      </td>
                      <td className="py-2.5">
                        <span className="rounded-full bg-[rgba(255,255,255,0.1)] px-2 py-0.5 text-[10px] font-semibold uppercase text-[rgba(255,255,255,0.6)]">
                          {c.plan_tier}
                        </span>
                      </td>
                      <td className="py-2.5">
                        {c.segment_name ? (
                          <span className="inline-flex items-center gap-2 text-xs">
                            <span
                              className="h-2 w-2 rounded-full"
                              style={{
                                backgroundColor:
                                  SEGMENT_COLORS[c.segment_name] ?? '#6b7280',
                              }}
                            />
                            <span
                              style={{
                                color:
                                  SEGMENT_COLORS[c.segment_name] ??
                                  'rgba(255,255,255,0.6)',
                              }}
                            >
                              {c.segment_name}
                            </span>
                          </span>
                        ) : (
                          <span className="text-xs text-[rgba(255,255,255,0.25)]">
                            —
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-right font-mono text-[rgba(255,255,255,0.7)]">
                        {c.total_revenue != null
                          ? formatCurrency(c.total_revenue)
                          : '—'}
                      </td>
                      <td className="py-2.5 text-right font-mono text-[rgba(255,255,255,0.7)]">
                        {c.engagement_score != null
                          ? c.engagement_score.toFixed(2)
                          : '—'}
                      </td>
                      <td className="py-2.5 text-right font-mono text-[rgba(255,255,255,0.7)]">
                        {c.churn_probability != null
                          ? `${(c.churn_probability * 100).toFixed(1)}%`
                          : '—'}
                      </td>
                      <td className="py-2.5">
                        {c.risk_tier ? (
                          <span
                            className="inline-flex min-w-14 justify-center rounded-full px-2.5 py-1 text-[10px] font-semibold"
                            style={{
                              backgroundColor:
                                RISK_BG[c.risk_tier.toLowerCase()] ??
                                'rgba(255,255,255,0.1)',
                              color:
                                RISK_COLORS[c.risk_tier.toLowerCase()] ??
                                'rgba(255,255,255,0.6)',
                            }}
                          >
                            {c.risk_tier}
                          </span>
                        ) : (
                          <span className="text-xs text-[rgba(255,255,255,0.25)]">
                            —
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-right">
                        {c.avg_sentiment != null ? (
                          <span
                            className="font-mono font-semibold"
                            style={{
                              color:
                                c.avg_sentiment > 0.2
                                  ? '#34d399'
                                  : c.avg_sentiment > -0.2
                                    ? 'rgba(255,255,255,0.45)'
                                    : '#f87171',
                            }}
                          >
                            {c.avg_sentiment.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-xs text-[rgba(255,255,255,0.25)]">
                            —
                          </span>
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
