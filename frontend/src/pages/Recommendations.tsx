import { Lightbulb, AlertTriangle, ArrowUpRight } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import EmptyState from '../components/shared/EmptyState';
import {
  useRecommendationSummary,
  useTopRecommendations,
} from '../api/hooks';

const CATEGORY_COLORS: Record<string, string> = {
  retention: '#ef4444',
  growth: '#10b981',
  monitoring: '#6b7280',
  support: '#f59e0b',
};

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded bg-slate-200 animate-pulse ${className}`} />;
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

  const maxAction = actionEntries.length > 0 ? actionEntries[0][1] : 1;

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
        <Card className="border-red-100 bg-red-50/40">
          <p className="flex items-center gap-2 text-sm text-red-600">
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
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Total Recommendations
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {summary.total_recommendations.toLocaleString()}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Avg Urgency Score
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {summary.avg_urgency.toFixed(1)}
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Categories
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(summary.category_distribution).map(([cat, count]) => (
                  <span
                    key={cat}
                    className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold text-white"
                    style={{ backgroundColor: CATEGORY_COLORS[cat] ?? '#6b7280' }}
                  >
                    {cat} ({count})
                  </span>
                ))}
              </div>
            </Card>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Action distribution */}
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-amber-500" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Action Distribution
                </h3>
              </div>
              <div className="space-y-2.5">
                {actionEntries.map(([label, count]) => {
                  const widthPct = (count / maxAction) * 100;
                  return (
                    <div key={label}>
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-600">{label}</span>
                        <span className="text-slate-400">{count}</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-100">
                        <div
                          className="h-2 rounded-full bg-emerald-500 transition-all"
                          style={{ width: `${widthPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Top priority recommendations */}
            <Card className="xl:col-span-2">
              <div className="mb-4 flex items-center gap-2">
                <ArrowUpRight className="h-4 w-4 text-emerald-600" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Top Priority Actions
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs text-slate-400">
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
                          className="border-b border-slate-50 last:border-0"
                        >
                          <td className="py-2.5 font-medium text-slate-700">
                            {r.action_label}
                          </td>
                          <td className="py-2.5">
                            <span
                              className="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold text-white"
                              style={{
                                backgroundColor:
                                  CATEGORY_COLORS[r.action_category] ?? '#6b7280',
                              }}
                            >
                              {r.action_category}
                            </span>
                          </td>
                          <td className="py-2.5 text-xs text-slate-500">
                            {r.primary_driver}
                          </td>
                          <td className="py-2.5 text-right text-sm font-semibold text-slate-700">
                            {r.urgency_score.toFixed(1)}
                          </td>
                          <td className="py-2.5 text-xs text-slate-500">
                            {r.target_timeframe}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-sm text-slate-400">
                          No priority recommendations available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
