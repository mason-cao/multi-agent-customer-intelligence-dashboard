import { Lightbulb, AlertTriangle, ArrowUpRight } from 'lucide-react';
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
import ChartCard from '../components/shared/ChartCard';
import EmptyState from '../components/shared/EmptyState';
import { CHART_COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from '../components/charts';
import {
  useRecommendationSummary,
  useTopRecommendations,
} from '../api/hooks';

const CATEGORY_BADGE: Record<string, string> = {
  retention: 'bg-[rgba(248,113,113,0.15)] text-[#f87171]',
  growth: 'bg-[rgba(52,211,153,0.15)] text-[#34d399]',
  monitoring: 'bg-[rgba(148,163,184,0.15)] text-[#94a3b8]',
  support: 'bg-[rgba(251,191,36,0.15)] text-[#fbbf24]',
};

const DEFAULT_BADGE = 'bg-[rgba(148,163,184,0.15)] text-[#94a3b8]';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded-md shimmer ${className}`} />;
}

export default function Recommendations() {
  const { data: summary, isLoading: sumLoading, isError: sumError } = useRecommendationSummary();
  const { data: topRecs, isLoading: recLoading, isError: recError } = useTopRecommendations(15);

  const isLoading = sumLoading || recLoading;
  const isError = sumError || recError;

  // Sort action distribution by count desc for the bar chart
  const actionEntries = summary
    ? Object.entries(summary.action_distribution).sort(([, a], [, b]) => b - a)
    : [];

  const chartData = actionEntries.map(([label, count]) => ({
    action: label,
    count,
  }));

  return (
    <div>
      <PageHeader
        title="Recommendation Center"
        description="AI-generated actionable recommendations for each segment and customer"
      />

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}><Skeleton className="h-20 w-full" /></Card>
            ))}
          </div>
          <Card><Skeleton className="h-64 w-full" /></Card>
        </div>
      ) : isError ? (
        <Card className="border-[rgba(248,113,113,0.2)] bg-[rgba(248,113,113,0.1)]">
          <p className="flex items-center gap-2 text-sm text-[rgba(248,113,113,0.9)]">
            <AlertTriangle className="h-4 w-4" />
            Failed to load recommendation data.
          </p>
        </Card>
      ) : !summary ? (
        <EmptyState
          icon={Lightbulb}
          title="No recommendations generated"
          description="AI-generated action recommendations will appear here once the recommendation agent has analyzed this workspace's customer data."
        />
      ) : (
        <>
          {/* Summary KPIs */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                Total Recommendations
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-white">
                {summary.total_recommendations.toLocaleString()}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                Avg Urgency Score
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-white">
                {summary.avg_urgency.toFixed(1)}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
                Categories
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(summary.category_distribution).map(([cat, count]) => (
                  <span
                    key={cat}
                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${CATEGORY_BADGE[cat] ?? DEFAULT_BADGE}`}
                  >
                    <span>{cat}</span>
                    <span className="font-mono opacity-80">{count}</span>
                  </span>
                ))}
              </div>
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Action distribution — Recharts vertical bar chart */}
            <ChartCard title="Action Distribution" icon={Lightbulb} className="animate-fade-in-up stagger-4">
              <ResponsiveContainer width="100%" height={250}>
                <BarChart
                  layout="vertical"
                  data={chartData}
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
                    dataKey="action"
                    width={110}
                    {...AXIS_STYLE}
                    tickFormatter={(value: unknown) => String(value)}
                  />
                  <Tooltip
                    {...TOOLTIP_STYLE}
                    formatter={(value: unknown) => [String(value), 'Count']}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
                    {chartData.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={CHART_COLORS[index % CHART_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Top priority recommendations */}
            <ChartCard title="Top Priority Actions" icon={ArrowUpRight} className="animate-fade-in-up stagger-5 xl:col-span-2">
              <div className="overflow-x-auto">
                <table className="metric-table min-w-[760px] text-left text-sm">
                  <thead>
                    <tr>
                      <th className="pb-2 font-medium">Action</th>
                      <th className="pb-2 font-medium">Category</th>
                      <th className="pb-2 font-medium">Driver</th>
                      <th className="pb-2 font-medium text-right">Urgency</th>
                      <th className="pb-2 font-medium">Timeframe</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topRecs?.length ? (
                      topRecs.map((r) => (
                        <tr
                          key={r.recommendation_id}
                          className="border-b border-[rgba(255,255,255,0.06)] transition-colors hover:bg-[rgba(255,255,255,0.04)] last:border-0"
                        >
                          <td className="py-2.5 font-medium text-white">
                            {r.action_label}
                          </td>
                          <td className="py-2.5">
                            <span
                              className={`inline-flex min-w-20 justify-center rounded-full px-2.5 py-1 text-[10px] font-semibold ${CATEGORY_BADGE[r.action_category] ?? DEFAULT_BADGE}`}
                            >
                              {r.action_category}
                            </span>
                          </td>
                          <td className="py-2.5 text-xs text-[rgba(255,255,255,0.7)]">
                            {r.primary_driver}
                          </td>
                          <td className="py-2.5 text-right font-mono text-sm font-semibold text-white">
                            {r.urgency_score.toFixed(1)}
                          </td>
                          <td className="py-2.5 text-xs text-[rgba(255,255,255,0.7)]">
                            {r.target_timeframe}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-sm text-[rgba(255,255,255,0.45)]">
                          No priority recommendations available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}
