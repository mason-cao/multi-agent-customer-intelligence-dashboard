import { MessageCircle, AlertTriangle, Hash } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import { useSentimentSummary } from '../api/hooks';
import { SENTIMENT_COLORS } from '../utils/colors';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded bg-slate-200 animate-pulse ${className}`} />;
}

const LABEL_ORDER = ['positive', 'neutral', 'negative'];

export default function SentimentSupport() {
  const { data: summary, isLoading, isError } = useSentimentSummary();

  const total = summary?.total ?? 0;

  // Sentiment score to color
  function sentColor(score: number): string {
    if (score > 0.2) return SENTIMENT_COLORS.positive;
    if (score > -0.2) return SENTIMENT_COLORS.neutral;
    return SENTIMENT_COLORS.negative;
  }

  return (
    <div>
      <PageHeader
        title="Sentiment & Support Intelligence"
        description="Voice of the customer — sentiment trends, topics, and support analysis"
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
      ) : isError || !summary ? (
        <Card className="border-red-100 bg-red-50/40">
          <p className="flex items-center gap-2 text-sm text-red-600">
            <AlertTriangle className="h-4 w-4" />
            Failed to load sentiment data.
          </p>
        </Card>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Total Documents
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {total.toLocaleString()}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                tickets &amp; feedback analyzed
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Avg Sentiment Score
              </p>
              <p
                className="mt-2 text-3xl font-bold"
                style={{ color: sentColor(summary.avg_score) }}
              >
                {summary.avg_score.toFixed(3)}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                scale: -1.0 to +1.0
              </p>
            </Card>
            <Card hover>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Topics Detected
              </p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {summary.topics.length}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                unique topics extracted
              </p>
            </Card>
          </div>

          {/* Distribution + Topics */}
          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Sentiment distribution */}
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-emerald-600" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Sentiment Distribution
                </h3>
              </div>

              {/* Stacked bar */}
              <div className="flex h-10 overflow-hidden rounded-lg">
                {LABEL_ORDER.map((label) => {
                  const count = summary.distribution[label] ?? 0;
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  return (
                    <div
                      key={label}
                      className="flex items-center justify-center text-[11px] font-bold text-white"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: SENTIMENT_COLORS[label] ?? '#9ca3af',
                      }}
                      title={`${label}: ${count} (${pct.toFixed(1)}%)`}
                    >
                      {pct > 10 ? `${pct.toFixed(0)}%` : ''}
                    </div>
                  );
                })}
              </div>

              {/* Legend */}
              <div className="mt-4 space-y-2">
                {LABEL_ORDER.map((label) => {
                  const count = summary.distribution[label] ?? 0;
                  const pct = total > 0 ? (count / total) * 100 : 0;
                  return (
                    <div
                      key={label}
                      className="flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full"
                          style={{
                            backgroundColor: SENTIMENT_COLORS[label] ?? '#9ca3af',
                          }}
                        />
                        <span className="font-medium text-slate-600 capitalize">
                          {label}
                        </span>
                      </div>
                      <span className="text-slate-400">
                        {count.toLocaleString()} ({pct.toFixed(1)}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Top topics */}
            <Card className="xl:col-span-2">
              <div className="mb-4 flex items-center gap-2">
                <Hash className="h-4 w-4 text-emerald-600" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Top Topics
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs text-slate-400">
                      <th className="pb-2 font-medium">Topic</th>
                      <th className="pb-2 font-medium text-right">Mentions</th>
                      <th className="pb-2 font-medium text-right">Avg Sentiment</th>
                      <th className="pb-2 font-medium">Sentiment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.topics.map((t) => {
                      const barPct = Math.min(
                        100,
                        Math.max(0, ((t.avg_sentiment + 1) / 2) * 100)
                      );
                      return (
                        <tr
                          key={t.topic}
                          className="border-b border-slate-50 last:border-0"
                        >
                          <td className="py-2.5 font-medium text-slate-700 capitalize">
                            {t.topic.replace(/_/g, ' ')}
                          </td>
                          <td className="py-2.5 text-right text-slate-600">
                            {t.count.toLocaleString()}
                          </td>
                          <td className="py-2.5 text-right">
                            <span
                              className="font-semibold"
                              style={{ color: sentColor(t.avg_sentiment) }}
                            >
                              {t.avg_sentiment.toFixed(3)}
                            </span>
                          </td>
                          <td className="py-2.5">
                            <div className="h-2 w-24 rounded-full bg-slate-100">
                              <div
                                className="h-2 rounded-full transition-all"
                                style={{
                                  width: `${barPct}%`,
                                  backgroundColor: sentColor(t.avg_sentiment),
                                }}
                              />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
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
