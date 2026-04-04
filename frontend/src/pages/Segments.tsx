import { useMemo } from 'react';
import { Users, DollarSign, Activity, AlertTriangle, Layers, PieChart as PieChartIcon } from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import ChartCard from '../components/shared/ChartCard';
import EmptyState from '../components/shared/EmptyState';
import { useSegmentSummary } from '../api/hooks';
import { SEGMENT_COLORS } from '../utils/colors';
import { GlassTooltip, TOOLTIP_STYLE } from '../components/charts';
import { formatCurrency, formatPercent } from '../utils/formatters';

function SegmentSkeleton() {
  return (
    <Card>
      <div className="h-4 w-32 rounded-md shimmer" />
      <div className="mt-4 h-8 w-16 rounded-md shimmer" />
      <div className="mt-3 space-y-2">
        <div className="h-3 w-full rounded-md shimmer" />
        <div className="h-3 w-3/4 rounded-md shimmer" />
      </div>
    </Card>
  );
}

function ChartSkeleton({ height = 280 }: { height?: number }) {
  return (
    <Card>
      <div className="h-4 w-40 rounded-md shimmer" />
      <div
        className="mt-4 w-full rounded-md shimmer"
        style={{ height }}
      />
    </Card>
  );
}

export default function Segments() {
  const { data: segments, isLoading, isError } = useSegmentSummary();

  const total = segments?.reduce((s, seg) => s + seg.customer_count, 0) ?? 0;

  const radarData = useMemo(() => {
    if (!segments || segments.length === 0) return [];

    const maxRevenue = Math.max(...segments.map((s) => s.avg_revenue));
    const maxEngagement = Math.max(...segments.map((s) => s.avg_engagement));
    const maxChurn = Math.max(...segments.map((s) => s.avg_churn_risk));

    return [
      {
        axis: 'Revenue',
        ...Object.fromEntries(
          segments.map((s) => [
            s.segment_name,
            maxRevenue > 0 ? s.avg_revenue / maxRevenue : 0,
          ])
        ),
      },
      {
        axis: 'Engagement',
        ...Object.fromEntries(
          segments.map((s) => [
            s.segment_name,
            maxEngagement > 0 ? s.avg_engagement / maxEngagement : 0,
          ])
        ),
      },
      {
        axis: 'Churn Risk',
        ...Object.fromEntries(
          segments.map((s) => [
            s.segment_name,
            maxChurn > 0 ? s.avg_churn_risk / maxChurn : 0,
          ])
        ),
      },
    ];
  }, [segments]);

  return (
    <div>
      <PageHeader
        title="Segment Intelligence"
        description="Understand and compare customer segments"
      />

      {isLoading ? (
        <>
          <div className="mb-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
            <ChartSkeleton height={280} />
            <ChartSkeleton height={300} />
          </div>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <SegmentSkeleton key={i} />
            ))}
          </div>
        </>
      ) : isError ? (
        <Card className="border-[rgba(248,113,113,0.2)]">
          <p className="flex items-center gap-2 text-sm text-[rgba(248,113,113,0.9)]">
            <AlertTriangle className="h-4 w-4" />
            Failed to load segment data. Ensure the backend is running and
            agents have been executed.
          </p>
        </Card>
      ) : !segments || segments.length === 0 ? (
        <EmptyState
          icon={Layers}
          title="No segment data available"
          description="Customer segments will appear here once the segmentation agent has analyzed this workspace's customer base."
        />
      ) : (
        <>
          {/* Top charts row */}
          <div className="mb-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
            {/* Donut Chart */}
            <ChartCard title="Customer Distribution" icon={PieChartIcon} className="animate-fade-in-up stagger-1">
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={segments.map((seg) => ({
                      name: seg.segment_name,
                      value: seg.customer_count,
                    }))}
                    cx="50%"
                    cy="50%"
                    innerRadius="60%"
                    outerRadius="80%"
                    paddingAngle={2}
                    dataKey="value"
                    stroke="none"
                  >
                    {segments.map((seg) => (
                      <Cell
                        key={seg.segment_name}
                        fill={SEGMENT_COLORS[seg.segment_name] ?? '#6b7280'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    content={
                      <GlassTooltip
                        formatter={(value: number) => {
                          const pct =
                            total > 0 ? ((value / total) * 100).toFixed(1) : '0';
                          return `${value.toLocaleString()} (${pct}%)`;
                        }}
                      />
                    }
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconType="circle"
                    iconSize={8}
                    formatter={(value: string) => (
                      <span className="text-xs text-[rgba(255,255,255,0.7)]">
                        {value}
                      </span>
                    )}
                  />
                  {/* Center text */}
                  <text
                    x="50%"
                    y="46%"
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="fill-white font-mono text-2xl font-bold"
                  >
                    {total.toLocaleString()}
                  </text>
                  <text
                    x="50%"
                    y="55%"
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="fill-[rgba(255,255,255,0.45)] text-xs"
                  >
                    customers
                  </text>
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Radar Chart */}
            <ChartCard title="Segment Comparison" icon={Activity} className="animate-fade-in-up stagger-2">
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="rgba(255,255,255,0.1)" />
                  <PolarAngleAxis
                    dataKey="axis"
                    tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }}
                  />
                  <PolarRadiusAxis
                    angle={90}
                    domain={[0, 1]}
                    tick={false}
                    axisLine={false}
                  />
                  {segments.map((seg) => {
                    const color =
                      SEGMENT_COLORS[seg.segment_name] ?? '#6b7280';
                    return (
                      <Radar
                        key={seg.segment_name}
                        name={seg.segment_name}
                        dataKey={seg.segment_name}
                        stroke={color}
                        fill={color}
                        fillOpacity={0.15}
                        strokeWidth={1.5}
                      />
                    );
                  })}
                  <Tooltip
                    {...TOOLTIP_STYLE}
                    formatter={(value: unknown) => typeof value === 'number' ? value.toFixed(2) : String(value)}
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconType="circle"
                    iconSize={8}
                    formatter={(value: string) => (
                      <span className="text-xs text-[rgba(255,255,255,0.7)]">
                        {value}
                      </span>
                    )}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          {/* Segment detail cards */}
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {segments.map((seg, i) => {
              const pct =
                total > 0 ? (seg.customer_count / total) * 100 : 0;
              const color =
                SEGMENT_COLORS[seg.segment_name] ?? '#6b7280';
              return (
                <Card
                  key={seg.segment_name}
                  hover
                  className={`animate-fade-in-up stagger-${i + 1}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <h3 className="text-sm font-semibold text-white">
                        {seg.segment_name}
                      </h3>
                    </div>
                    <span className="rounded-full bg-[rgba(255,255,255,0.1)] px-2 py-0.5 text-[11px] font-medium text-[rgba(255,255,255,0.7)]">
                      {pct.toFixed(1)}%
                    </span>
                  </div>

                  <p className="mt-3 font-mono text-2xl font-bold text-white">
                    {seg.customer_count.toLocaleString()}
                  </p>
                  <p className="text-xs text-[rgba(255,255,255,0.45)]">
                    customers
                  </p>

                  <div className="mt-4 grid grid-cols-3 gap-3 border-t border-[rgba(255,255,255,0.1)] pt-4">
                    <div>
                      <p className="flex items-center gap-1 text-[10px] font-medium text-[rgba(255,255,255,0.45)]">
                        <DollarSign className="h-3 w-3" /> Avg Rev
                      </p>
                      <p className="mt-0.5 font-mono text-sm font-semibold text-white">
                        {formatCurrency(seg.avg_revenue)}
                      </p>
                    </div>
                    <div>
                      <p className="flex items-center gap-1 text-[10px] font-medium text-[rgba(255,255,255,0.45)]">
                        <Activity className="h-3 w-3" /> Engage
                      </p>
                      <p className="mt-0.5 font-mono text-sm font-semibold text-white">
                        {seg.avg_engagement.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="flex items-center gap-1 text-[10px] font-medium text-[rgba(255,255,255,0.45)]">
                        <Users className="h-3 w-3" /> Churn
                      </p>
                      <p className="mt-0.5 font-mono text-sm font-semibold text-white">
                        {formatPercent(seg.avg_churn_risk)}
                      </p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
