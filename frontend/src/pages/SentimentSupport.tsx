import { MessageCircle, AlertTriangle, Hash, FileText } from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import StatCard from '../components/shared/StatCard';
import ChartCard from '../components/shared/ChartCard';
import EmptyState from '../components/shared/EmptyState';
import { useSentimentSummary } from '../api/hooks';
import { SENTIMENT_COLORS } from '../utils/colors';
import { AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from '../components/charts';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded-md shimmer ${className}`} />;
}

const LABEL_ORDER = ['very_positive', 'positive', 'neutral', 'negative', 'very_negative'];

const LABEL_DISPLAY: Record<string, string> = {
  very_positive: 'Very Positive',
  positive: 'Positive',
  neutral: 'Neutral',
  negative: 'Negative',
  very_negative: 'Very Negative',
};

function sentColor(score: number): string {
  if (score >= 0.4) return SENTIMENT_COLORS.very_positive;
  if (score >= 0.1) return SENTIMENT_COLORS.positive;
  if (score >= -0.1) return SENTIMENT_COLORS.neutral;
  if (score >= -0.4) return SENTIMENT_COLORS.negative;
  return SENTIMENT_COLORS.very_negative;
}

function barColor(score: number): string {
  if (score >= 0.1) return SENTIMENT_COLORS.positive;
  if (score >= -0.1) return SENTIMENT_COLORS.neutral;
  return SENTIMENT_COLORS.negative;
}

export default function SentimentSupport() {
  const { data: summary, isLoading, isError } = useSentimentSummary();

  const total = summary?.total ?? 0;

  // Build pie data from distribution
  const pieData = summary
    ? LABEL_ORDER
        .filter((label) => (summary.distribution[label] ?? 0) > 0)
        .map((label) => ({
          name: LABEL_DISPLAY[label] ?? label,
          value: summary.distribution[label] ?? 0,
          color: SENTIMENT_COLORS[label] ?? '#94a3b8',
        }))
    : [];

  // Build bar data from topics — sorted by avg_sentiment descending
  const topicBarData = summary
    ? [...summary.topics]
        .sort((a, b) => b.avg_sentiment - a.avg_sentiment)
        .map((t) => ({
          topic: t.topic.replace(/_/g, ' '),
          avg_sentiment: parseFloat(t.avg_sentiment.toFixed(3)),
          count: t.count,
          fill: barColor(t.avg_sentiment),
        }))
    : [];

  const topicBarHeight = Math.max(280, topicBarData.length * 36);

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
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <Card><Skeleton className="h-72 w-full" /></Card>
            <Card className="xl:col-span-2"><Skeleton className="h-72 w-full" /></Card>
          </div>
        </div>
      ) : isError ? (
        <Card className="border-[rgba(248,113,113,0.2)] bg-[rgba(248,113,113,0.1)]">
          <p className="flex items-center gap-2 text-sm text-[rgba(248,113,113,0.9)]">
            <AlertTriangle className="h-4 w-4" />
            Failed to load sentiment data.
          </p>
        </Card>
      ) : !summary ? (
        <EmptyState
          icon={MessageCircle}
          title="No sentiment data available"
          description="Sentiment analysis and topic extraction will appear here once the sentiment agent has processed this workspace's feedback."
        />
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard title="Total Documents" value={total.toLocaleString()} icon={FileText} variant="default" />
            <StatCard
              title="Avg Sentiment Score"
              value={`${summary.avg_score >= 0 ? '+' : ''}${summary.avg_score.toFixed(3)}`}
              icon={MessageCircle}
              variant="default"
            />
            <StatCard title="Topics Detected" value={summary.topics.length} icon={Hash} variant="default" />
          </div>

          {/* Distribution donut + Topic bars */}
          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Sentiment distribution donut */}
            <ChartCard title="Sentiment Distribution" icon={MessageCircle}>

              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="45%"
                      innerRadius="55%"
                      outerRadius="80%"
                      paddingAngle={2}
                      stroke="rgba(255,255,255,0.08)"
                      strokeWidth={1}
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={(value: unknown) => {
                        const num = Number(value);
                        const pct = total > 0 ? ((num / total) * 100).toFixed(1) : '0';
                        return [`${num.toLocaleString()} (${pct}%)`, 'Count'];
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{
                        fontSize: 11,
                        color: 'rgba(255,255,255,0.7)',
                        fontFamily: "'Geist Sans', sans-serif",
                        paddingTop: 8,
                      }}
                      formatter={(value: unknown) => (
                        <span style={{ color: 'rgba(255,255,255,0.7)' }}>{String(value)}</span>
                      )}
                    />
                    {/* Center avg score text */}
                    <text
                      x="50%"
                      y="42%"
                      textAnchor="middle"
                      dominantBaseline="central"
                      style={{
                        fontSize: 22,
                        fontWeight: 700,
                        fontFamily: "'Geist Mono', monospace",
                        fill: sentColor(summary.avg_score),
                      }}
                    >
                      {summary.avg_score >= 0 ? '+' : ''}{summary.avg_score.toFixed(2)}
                    </text>
                    <text
                      x="50%"
                      y="52%"
                      textAnchor="middle"
                      dominantBaseline="central"
                      style={{
                        fontSize: 10,
                        fontFamily: "'Geist Sans', sans-serif",
                        fill: 'rgba(255,255,255,0.45)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}
                    >
                      avg score
                    </text>
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-64 items-center justify-center">
                  <p className="text-sm text-[rgba(255,255,255,0.45)]">
                    No distribution data
                  </p>
                </div>
              )}
            </ChartCard>

            {/* Top topics horizontal bar chart */}
            <ChartCard title="Top Topics by Sentiment" icon={Hash} className="xl:col-span-2">

              {topicBarData.length > 0 ? (
                <ResponsiveContainer width="100%" height={topicBarHeight}>
                  <BarChart
                    data={topicBarData}
                    layout="vertical"
                    margin={{ top: 4, right: 24, bottom: 4, left: 8 }}
                  >
                    <CartesianGrid {...GRID_STYLE} horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[-1, 1]}
                      tickCount={5}
                      {...AXIS_STYLE}
                      tickFormatter={(value: unknown) => String(Number(value).toFixed(1))}
                    />
                    <YAxis
                      type="category"
                      dataKey="topic"
                      width={120}
                      {...AXIS_STYLE}
                      tick={{
                        ...AXIS_STYLE,
                        textAnchor: 'end',
                        style: {
                          textTransform: 'capitalize',
                          fontSize: 11,
                          fill: 'rgba(255,255,255,0.7)',
                          fontFamily: "'Geist Sans', sans-serif",
                        },
                      }}
                    />
                    <Tooltip
                      {...TOOLTIP_STYLE}
                      formatter={(value: unknown, name: unknown) => {
                        const label = String(name) === 'avg_sentiment' ? 'Avg Sentiment' : String(name);
                        return [Number(value).toFixed(3), label];
                      }}
                      labelFormatter={(value: unknown) => {
                        const label = String(value);
                        return label.charAt(0).toUpperCase() + label.slice(1);
                      }}
                    />
                    <Bar
                      dataKey="avg_sentiment"
                      radius={[0, 4, 4, 0]}
                      maxBarSize={22}
                    >
                      {topicBarData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-64 items-center justify-center">
                  <p className="text-sm text-[rgba(255,255,255,0.45)]">
                    No topics extracted from feedback
                  </p>
                </div>
              )}
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}
