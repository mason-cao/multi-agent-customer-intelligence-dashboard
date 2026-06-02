import { AlertTriangle, BarChart3, TrendingDown } from 'lucide-react';
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
import ChartCard from '../components/shared/ChartCard';
import EmptyState from '../components/shared/EmptyState';
import {
  useChurnDistribution,
  useAtRiskCustomers,
  useFeatureImportance,
} from '../api/hooks';
import Badge from '../components/shared/Badge';
import { RISK_COLORS, PALETTE } from '../utils/colors';
import { formatCurrency } from '../utils/formatters';
import { AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from '../components/charts';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded-md shimmer ${className}`} />;
}

/** Convert a hex color like #f87171 to an rgba string at a given alpha. */
function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export default function ChurnRetention() {
  const { data: distribution, isLoading: distLoading, isError: distError } = useChurnDistribution();
  const { data: atRisk, isLoading: riskLoading, isError: riskError } = useAtRiskCustomers(15);
  const { data: features, isLoading: featLoading, isError: featError } = useFeatureImportance();

  const isLoading = distLoading || riskLoading || featLoading;
  const isError = distError || riskError || featError;
  const isEmpty = !distribution?.length && !atRisk?.length && !features?.length;
  const totalCustomers = distribution?.reduce((s, d) => s + d.count, 0) ?? 0;

  const chartData = features?.slice(0, 8).map((f) => ({
    feature: f.feature,
    importance: f.importance,
  })) ?? [];

  return (
    <div>
      <PageHeader
        title="Churn & Retention Center"
        description="Predict, prevent, and analyze customer churn"
      />

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}><Skeleton className="h-16 w-full" /></Card>
            ))}
          </div>
          <Card><Skeleton className="h-64 w-full" /></Card>
        </div>
      ) : isError ? (
        <Card className="border-danger/20 bg-danger/10">
          <p className="flex items-center gap-2 text-sm text-danger">
            <AlertTriangle className="h-4 w-4" />
            Failed to load churn analysis data.
          </p>
        </Card>
      ) : isEmpty ? (
        <EmptyState
          icon={TrendingDown}
          title="No churn analysis available"
          description="Churn predictions and risk tiers will appear here once the churn agent has processed this workspace's data."
        />
      ) : (
        <>
          {/* Risk tier cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {distribution?.map((tier, i) => {
              const pct = totalCustomers > 0
                ? ((tier.count / totalCustomers) * 100).toFixed(1)
                : '0';
              const colorKey = tier.risk_tier.toLowerCase();
              return (
                <Card
                  key={tier.risk_tier}
                  hover
                  className={`animate-fade-in-up stagger-${i + 1}`}
                  style={{ '--glass-hover-glow': hexToRgba(RISK_COLORS[colorKey] ?? PALETTE.muted, 0.12) } as React.CSSProperties}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: RISK_COLORS[colorKey] ?? PALETTE.muted }}
                    />
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
                      {tier.risk_tier}
                    </p>
                  </div>
                  <p className="mt-2 font-mono text-3xl font-bold text-white">
                    {tier.count.toLocaleString()}
                  </p>
                  <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--color-text-secondary)]">
                    <span className="font-mono text-white/80">{pct}%</span>
                    <span>of customers</span>
                    <span className="font-mono text-white/80">{formatCurrency(tier.mrr_at_risk)}</span>
                    <span>MRR</span>
                  </p>
                </Card>
              );
            })}
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Top at-risk customers */}
            <ChartCard title="Highest-Risk Customers" icon={AlertTriangle} className="animate-fade-in-up stagger-5 xl:col-span-2">
              <div className="overflow-x-auto">
                <table className="metric-table min-w-[720px] text-left text-sm">
                  <thead>
                    <tr>
                      <th className="pb-2 font-medium">Customer</th>
                      <th className="pb-2 font-medium">Company</th>
                      <th className="pb-2 font-medium text-right">Churn %</th>
                      <th className="pb-2 font-medium text-right">MRR</th>
                      <th className="pb-2 font-medium">Top Driver</th>
                    </tr>
                  </thead>
                  <tbody>
                    {atRisk?.length ? (
                      atRisk.map((c) => {
                        const riskColor = RISK_COLORS[c.risk_tier.toLowerCase()] ?? PALETTE.muted;
                        return (
                          <tr
                            key={c.customer_id}
                            className="border-b border-white/[0.06] last:border-0 transition-colors hover:bg-white/5"
                          >
                            <td className="py-2.5 font-medium text-white">
                              {c.name}
                            </td>
                            <td className="py-2.5 text-[var(--color-text-secondary)]">{c.company}</td>
                            <td className="py-2.5 text-right">
                              <Badge
                                color={riskColor}
                                label={`${(c.churn_probability * 100).toFixed(1)}%`}
                                size="md"
                                className="min-w-14 justify-center font-mono"
                              />
                            </td>
                            <td className="py-2.5 text-right font-mono text-[var(--color-text-secondary)]">
                              {formatCurrency(c.mrr)}
                            </td>
                            <td className="py-2.5 text-xs text-[var(--color-text-secondary)]">
                              {c.top_risk_factor}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-sm text-[var(--color-text-tertiary)]">
                          No at-risk customers identified
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </ChartCard>

            {/* Feature importance — Recharts horizontal bar chart */}
            <ChartCard title="Top Churn Drivers" icon={BarChart3} className="animate-fade-in-up stagger-6">
              {chartData.length ? (
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    layout="vertical"
                    data={chartData}
                    margin={{ top: 4, right: 20, bottom: 4, left: 8 }}
                  >
                    <CartesianGrid {...GRID_STYLE} horizontal={false} />
                    <XAxis
                      type="number"
                      {...AXIS_STYLE}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="feature"
                      width={110}
                      {...AXIS_STYLE}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={(value: unknown) =>
                        typeof value === 'number'
                          ? [`${(value * 100).toFixed(1)}%`, 'Importance']
                          : [String(value), 'Importance']
                      }
                    />
                    <Bar
                      dataKey="importance"
                      fill={PALETTE.indigo}
                      radius={[0, 4, 4, 0]}
                      barSize={20}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-8 text-center text-sm text-[var(--color-text-tertiary)]">
                  No feature importance data available
                </p>
              )}
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}
