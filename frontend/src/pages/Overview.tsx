import {
  Zap,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  BarChart3,
} from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import EmptyState from '../components/shared/EmptyState';
import { useOverviewKpis, useOverviewNarrative } from '../api/hooks';
import type { KpiData } from '../types';

function generateSparklineData(trend: number): { value: number }[] {
  const base = 100;
  const target = base * (1 + trend / 100);
  return Array.from({ length: 7 }, (_, i) => ({
    value: base + ((target - base) * i) / 6 + (Math.sin(i * 1.5) * 3),
  }));
}

function KpiCard({ kpi, index }: { kpi: KpiData; index: number }) {
  const sparkData = generateSparklineData(kpi.trend);
  const sparkColor =
    kpi.trend >= 0 ? 'var(--color-success)' : 'var(--color-danger)';
  const sparkId = `spark-${index}`;

  return (
    <Card hover variant="elevated" className={`animate-fade-in-up stagger-${index + 1}`}>
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
            {kpi.label}
          </p>
          <p className="text-hero mt-3 font-mono text-3xl font-bold tracking-tight">
            {kpi.value}
          </p>
          <p className="mt-1.5 flex items-center gap-1 text-xs text-[rgba(255,255,255,0.55)]">
            {kpi.trend > 0 && (
              <TrendingUp className="h-3 w-3 text-[var(--color-success)]" />
            )}
            {kpi.trend < 0 && (
              <TrendingDown className="h-3 w-3 text-[var(--color-danger)]" />
            )}
            {kpi.trend !== 0 && (
              <span
                className={
                  kpi.trend > 0
                    ? 'text-[var(--color-success)]'
                    : 'text-[var(--color-danger)]'
                }
              >
                {kpi.trend > 0 ? '+' : ''}
                {kpi.trend}
              </span>
            )}
            <span>{kpi.trend_label}</span>
          </p>
        </div>

        {/* Mini sparkline */}
        <div className="h-[50px] w-[72px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData}>
              <defs>
                <linearGradient id={sparkId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={sparkColor} stopOpacity={0.3} />
                  <stop
                    offset="100%"
                    stopColor={sparkColor}
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="value"
                stroke={sparkColor}
                strokeWidth={1.5}
                fill={`url(#${sparkId})`}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}

function KpiSkeleton({ index }: { index: number }) {
  return (
    <Card variant="elevated" className={`animate-fade-in-up stagger-${index + 1}`}>
      <div className="h-3 w-24 rounded-md shimmer" />
      <div className="mt-4 h-8 w-16 rounded-md shimmer" />
      <div className="mt-2 h-3 w-20 rounded-md shimmer" />
    </Card>
  );
}

export default function Overview() {
  const { data: kpis, isLoading, isError } = useOverviewKpis();
  const { data: narrative, isLoading: narrativeLoading } =
    useOverviewNarrative();

  const kpiList: KpiData[] = kpis
    ? [
        kpis.total_customers,
        kpis.monthly_revenue,
        kpis.churn_rate,
        kpis.avg_sentiment,
        kpis.active_anomalies,
      ]
    : [];

  return (
    <div>
      <PageHeader
        title="Executive Overview"
        description="AI-powered pulse check on customer health, revenue, and risk"
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => (
              <KpiSkeleton key={i} index={i} />
            ))
          : isError
            ? Array.from({ length: 5 }).map((_, i) => (
                <Card
                  key={i}
                  className={`animate-fade-in-up stagger-${i + 1} border-[rgba(248,113,113,0.2)] bg-[rgba(248,113,113,0.1)]`}
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                    --
                  </p>
                  <p className="mt-3 text-sm text-[var(--color-danger)]">
                    Failed to load
                  </p>
                </Card>
              ))
            : kpiList.length === 0
              ? (
                <div className="col-span-full">
                  <EmptyState
                    icon={BarChart3}
                    title="No metrics available"
                    description="Executive KPIs will appear here once the intelligence pipeline has processed this workspace's data."
                  />
                </div>
              )
              : kpiList.map((kpi, i) => (
                  <KpiCard key={kpi.label} kpi={kpi} index={i} />
                ))}
      </div>

      {/* AI Narrative */}
      <Card className="mt-6 animate-fade-in-up stagger-5 border-l-2 border-[var(--color-primary-400)]">
        <div className="mb-3 flex items-center gap-2">
          <span className="flex items-center gap-1.5 rounded-full bg-[rgba(129,140,248,0.15)] px-2.5 py-1 text-[11px] font-semibold text-[var(--color-primary-400)]">
            <Zap className="h-3 w-3" />
            Generated by AI
          </span>
        </div>

        {narrativeLoading ? (
          <div className="space-y-2">
            <div className="h-4 w-3/4 rounded-md shimmer" />
            <div className="h-4 w-1/2 rounded-md shimmer" />
          </div>
        ) : narrative ? (
          <div className="space-y-3">
            <p className="text-sm leading-relaxed text-[rgba(255,255,255,0.7)]">
              {narrative.executive_summary}
            </p>

            {narrative.highlights.length > 0 && (
              <div className="space-y-1">
                {narrative.highlights.map((h) => (
                  <p
                    key={h}
                    className="flex items-start gap-1.5 text-xs text-[rgba(255,255,255,0.7)]"
                  >
                    <CheckCircle className="mt-0.5 h-3 w-3 shrink-0 text-[var(--color-success)]" />
                    {h}
                  </p>
                ))}
              </div>
            )}

            {narrative.concerns.length > 0 && (
              <div className="space-y-1">
                {narrative.concerns.map((c) => (
                  <p
                    key={c}
                    className="flex items-start gap-1.5 text-xs text-[rgba(255,255,255,0.7)]"
                  >
                    <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-[var(--color-warning)]" />
                    {c}
                  </p>
                ))}
              </div>
            )}

            <p className="text-[10px] text-[rgba(255,255,255,0.35)]">
              Generated {new Date(narrative.generated_at).toLocaleString()}
            </p>
          </div>
        ) : (
          <p className="text-sm leading-relaxed text-[rgba(255,255,255,0.55)]">
            The AI-generated executive narrative will appear here once the
            intelligence pipeline has processed this workspace.
          </p>
        )}
      </Card>
    </div>
  );
}
