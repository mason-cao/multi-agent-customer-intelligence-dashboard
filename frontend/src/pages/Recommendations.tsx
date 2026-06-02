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
import Badge, { type BadgeTone } from '../components/shared/Badge';

const CATEGORY_TONE: Record<string, BadgeTone> = {
  retention: 'danger',
  growth: 'success',
  monitoring: 'muted',
  support: 'warning',
};

function humanize(value: string | null | undefined): string {
  if (!value) return 'Not specified';
  return value
    .replace(/[_-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

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
        <Card className="border-danger/20 bg-danger/10">
          <p className="flex items-center gap-2 text-sm text-danger">
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
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
                Total Recommendations
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-white">
                {summary.total_recommendations.toLocaleString()}
              </p>
              <p className="mt-2 text-xs leading-5 text-[var(--color-text-secondary)]">
                Customers with a recommended next action.
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
                Avg Urgency Score
              </p>
              <p className="mt-2 font-mono text-3xl font-bold text-white">
                {summary.avg_urgency.toFixed(1)}
              </p>
              <p className="mt-2 text-xs leading-5 text-[var(--color-text-secondary)]">
                0-100 score; higher means stronger need to act.
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
                Categories
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(summary.category_distribution).map(([cat, count]) => (
                  <Badge
                    key={cat}
                    tone={CATEGORY_TONE[cat] ?? 'muted'}
                    label={humanize(cat)}
                    count={count}
                    size="md"
                  />
                ))}
              </div>
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Action distribution — Recharts vertical bar chart */}
            <ChartCard
              title="Action Distribution"
              description="How the recommended work is distributed across next-best-action types."
              icon={Lightbulb}
              className="animate-fade-in-up stagger-4"
            >
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
            <ChartCard
              title="Top Priority Actions"
              description="Sorted by priority first, then urgency score."
              icon={ArrowUpRight}
              className="animate-fade-in-up stagger-5 xl:col-span-2"
            >
              <div className="overflow-x-auto">
                <table className="metric-table min-w-[820px] text-left text-sm">
                  <thead>
                    <tr>
                      <th className="pb-2 font-medium">Action</th>
                      <th className="pb-2 font-medium">Category</th>
                      <th className="pb-2 font-medium">Priority</th>
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
                          className="border-b border-white/[0.06] transition-colors hover:bg-white/5 last:border-0"
                        >
                          <td className="py-2.5 font-medium text-white">
                            {r.action_label}
                          </td>
                          <td className="py-2.5">
                            <Badge
                              tone={CATEGORY_TONE[r.action_category] ?? 'muted'}
                              label={humanize(r.action_category)}
                              size="md"
                              className="min-w-20 justify-center"
                            />
                          </td>
                          <td className="py-2.5">
                            <span className="inline-flex rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-[11px] font-semibold text-white">
                              P{r.action_priority}
                            </span>
                          </td>
                          <td className="max-w-[220px] py-2.5 text-xs leading-5 text-[var(--color-text-secondary)]">
                            <p>{humanize(r.primary_driver)}</p>
                            {r.secondary_driver && (
                              <p className="mt-1 text-[var(--color-text-tertiary)]">
                                Also: {humanize(r.secondary_driver)}
                              </p>
                            )}
                          </td>
                          <td className="py-2.5 text-right font-mono text-sm font-semibold text-white">
                            {r.urgency_score.toFixed(1)}
                          </td>
                          <td className="py-2.5 text-xs text-[var(--color-text-secondary)]">
                            {r.target_timeframe}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-sm text-[var(--color-text-tertiary)]">
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
