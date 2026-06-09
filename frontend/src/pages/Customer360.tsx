import { useState } from 'react';
import { Users, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import EmptyState from '../components/shared/EmptyState';
import { useCustomers } from '../api/hooks';
import Badge from '../components/shared/Badge';
import { SEGMENT_COLORS, RISK_COLORS, PALETTE } from '../utils/colors';
import { formatCurrency } from '../utils/formatters';

const PAGE_SIZE = 25;

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
        <Card className="border-danger/20 bg-danger/10">
          <p className="flex items-center gap-2 text-sm text-danger">
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
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-[var(--color-primary-400)]" />
                <span className="text-sm font-semibold text-white">
                  {data.total.toLocaleString()} customers
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  aria-label="Previous customer page"
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="rounded-lg border border-white/15 p-1.5 text-[var(--color-text-secondary)] transition hover:bg-white/[0.08] hover:text-white/80 disabled:opacity-30"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="rounded-md bg-white/5 px-2.5 py-1 font-mono text-xs text-[var(--color-text-secondary)]">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  type="button"
                  aria-label="Next customer page"
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-lg border border-white/15 p-1.5 text-[var(--color-text-secondary)] transition hover:bg-white/[0.08] hover:text-white/80 disabled:opacity-30"
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
                      className="border-b border-white/[0.06] last:border-0 transition-colors hover:bg-white/5"
                    >
                      <td className="py-2.5 font-medium text-white">
                        {c.name}
                      </td>
                      <td className="py-2.5 text-[var(--color-text-secondary)]">
                        {c.company}
                      </td>
                      <td className="py-2.5">
                        <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-[var(--color-text-secondary)]">
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
                                  SEGMENT_COLORS[c.segment_name] ?? PALETTE.muted,
                              }}
                            />
                            <span
                              style={{
                                color:
                                  SEGMENT_COLORS[c.segment_name] ??
                                  'var(--color-text-secondary)',
                              }}
                            >
                              {c.segment_name}
                            </span>
                          </span>
                        ) : (
                          <span className="text-xs text-[var(--color-text-tertiary)]">
                            —
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-right font-mono text-[var(--color-text-secondary)]">
                        {c.total_revenue != null
                          ? formatCurrency(c.total_revenue)
                          : '—'}
                      </td>
                      <td className="py-2.5 text-right font-mono text-[var(--color-text-secondary)]">
                        {c.engagement_score != null
                          ? c.engagement_score.toFixed(2)
                          : '—'}
                      </td>
                      <td className="py-2.5 text-right font-mono text-[var(--color-text-secondary)]">
                        {c.churn_probability != null
                          ? `${(c.churn_probability * 100).toFixed(1)}%`
                          : '—'}
                      </td>
                      <td className="py-2.5">
                        {c.risk_tier ? (
                          <Badge
                            color={RISK_COLORS[c.risk_tier.toLowerCase()] ?? PALETTE.muted}
                            label={c.risk_tier}
                            size="md"
                            className="min-w-14 justify-center capitalize"
                          />
                        ) : (
                          <span className="text-xs text-[var(--color-text-tertiary)]">
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
                                  ? PALETTE.success
                                  : c.avg_sentiment > -0.2
                                    ? 'var(--color-text-tertiary)'
                                    : PALETTE.danger,
                            }}
                          >
                            {c.avg_sentiment.toFixed(2)}
                          </span>
                        ) : (
                          <span className="text-xs text-[var(--color-text-tertiary)]">
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
