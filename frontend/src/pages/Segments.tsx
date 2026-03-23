import { Users, DollarSign, Activity, AlertTriangle } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import { useSegmentSummary } from '../api/hooks';
import { SEGMENT_COLORS } from '../utils/colors';
import { formatCurrency, formatPercent } from '../utils/formatters';

function SegmentSkeleton() {
  return (
    <Card>
      <div className="h-4 w-32 rounded bg-slate-200 animate-pulse" />
      <div className="mt-4 h-8 w-16 rounded bg-slate-200 animate-pulse" />
      <div className="mt-3 space-y-2">
        <div className="h-3 w-full rounded bg-slate-100 animate-pulse" />
        <div className="h-3 w-3/4 rounded bg-slate-100 animate-pulse" />
      </div>
    </Card>
  );
}

export default function Segments() {
  const { data: segments, isLoading, isError } = useSegmentSummary();

  const total = segments?.reduce((s, seg) => s + seg.customer_count, 0) ?? 0;

  return (
    <div>
      <PageHeader
        title="Segment Intelligence"
        description="Understand and compare customer segments"
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <SegmentSkeleton key={i} />
          ))}
        </div>
      ) : isError ? (
        <Card className="border-red-100 bg-red-50/40">
          <p className="flex items-center gap-2 text-sm text-red-600">
            <AlertTriangle className="h-4 w-4" />
            Failed to load segment data. Ensure the backend is running and agents have been executed.
          </p>
        </Card>
      ) : !segments || segments.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-500">
            No segment data available. Run the segmentation agent to generate results.
          </p>
        </Card>
      ) : (
        <>
          {/* Distribution bar */}
          <Card className="mb-6">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Customer Distribution
            </h3>
            <div className="flex h-8 overflow-hidden rounded-lg">
              {segments.map((seg) => {
                const pct = total > 0 ? (seg.customer_count / total) * 100 : 0;
                return (
                  <div
                    key={seg.segment_name}
                    className="flex items-center justify-center text-[10px] font-bold text-white transition-all"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: SEGMENT_COLORS[seg.segment_name] ?? '#6b7280',
                      minWidth: pct > 3 ? undefined : '2%',
                    }}
                    title={`${seg.segment_name}: ${seg.customer_count} (${pct.toFixed(1)}%)`}
                  >
                    {pct > 8 ? `${pct.toFixed(0)}%` : ''}
                  </div>
                );
              })}
            </div>
            <div className="mt-3 flex flex-wrap gap-4">
              {segments.map((seg) => (
                <div key={seg.segment_name} className="flex items-center gap-1.5 text-xs text-slate-600">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: SEGMENT_COLORS[seg.segment_name] ?? '#6b7280' }}
                  />
                  {seg.segment_name}
                </div>
              ))}
            </div>
          </Card>

          {/* Segment cards */}
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {segments.map((seg, i) => {
              const pct = total > 0 ? (seg.customer_count / total) * 100 : 0;
              const color = SEGMENT_COLORS[seg.segment_name] ?? '#6b7280';
              return (
                <Card key={seg.segment_name} hover className={`animate-fade-in-up stagger-${i + 1}`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block h-3 w-3 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <h3 className="text-sm font-semibold text-slate-800">
                        {seg.segment_name}
                      </h3>
                    </div>
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                      {pct.toFixed(1)}%
                    </span>
                  </div>

                  <p className="mt-3 text-2xl font-bold text-slate-900">
                    {seg.customer_count.toLocaleString()}
                  </p>
                  <p className="text-xs text-slate-400">customers</p>

                  <div className="mt-4 grid grid-cols-3 gap-3 border-t border-slate-100 pt-4">
                    <div>
                      <p className="flex items-center gap-1 text-[10px] font-medium text-slate-400">
                        <DollarSign className="h-3 w-3" /> Avg Rev
                      </p>
                      <p className="mt-0.5 text-sm font-semibold text-slate-700">
                        {formatCurrency(seg.avg_revenue)}
                      </p>
                    </div>
                    <div>
                      <p className="flex items-center gap-1 text-[10px] font-medium text-slate-400">
                        <Activity className="h-3 w-3" /> Engage
                      </p>
                      <p className="mt-0.5 text-sm font-semibold text-slate-700">
                        {seg.avg_engagement.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="flex items-center gap-1 text-[10px] font-medium text-slate-400">
                        <Users className="h-3 w-3" /> Churn
                      </p>
                      <p className="mt-0.5 text-sm font-semibold text-slate-700">
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
