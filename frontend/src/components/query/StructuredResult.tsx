import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { CHART_COLORS, AXIS_STYLE, GRID_STYLE, TOOLTIP_STYLE } from '../../components/charts';
import type { QueryResult } from '../../types';

const DIST_FIELD: Record<string, { label: string; value: string }> = {
  churn_by_segment: { label: 'segment_name', value: 'avg_churn_prob' },
  sentiment_by_segment: { label: 'segment_name', value: 'avg_sentiment' },
  revenue_by_segment: { label: 'segment_name', value: 'total_revenue' },
  recommendation_dist: { label: 'action_label', value: 'count' },
  ticket_topics: { label: 'category', value: 'count' },
};

function humanizeKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatNumber(key: string, value: number): string {
  const k = key.toLowerCase();
  if (/(probability|prob|churn|sentiment|engagement|rate|pct|percent)/.test(k) && Math.abs(value) <= 1) {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (/(revenue|mrr|spend|value|amount)/.test(k)) {
    return value >= 1000
      ? `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
      : `$${value.toFixed(2)}`;
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
}

function formatCell(key: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number') return formatNumber(key, value);
  const str = String(value);
  return str.length > 140 ? `${str.slice(0, 137)}…` : str;
}

function formatAxis(key: string, value: number): string {
  const k = key.toLowerCase();
  if (/(probability|prob|churn|sentiment|rate)/.test(k) && Math.abs(value) <= 1) {
    return `${Math.round(value * 100)}%`;
  }
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

type Row = Record<string, unknown>;

function isRowArray(value: unknown): value is Row[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((v) => v !== null && typeof v === 'object' && !Array.isArray(v))
  );
}

function ResultTable({ rows }: { rows: Row[] }) {
  const keys = Object.keys(rows[0] ?? {});
  const shown = rows.slice(0, 8);
  const isNumeric = (key: string) =>
    rows.every((r) => r[key] === null || r[key] === undefined || typeof r[key] === 'number');

  return (
    <div className="overflow-x-auto">
      <table className="metric-table text-xs">
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key} className={isNumeric(key) ? 'text-right' : 'text-left'}>
                {humanizeKey(key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((row, i) => (
            <tr key={i}>
              {keys.map((key) => (
                <td
                  key={key}
                  className={`text-[var(--color-text-secondary)] ${isNumeric(key) ? 'text-right font-mono' : ''}`}
                >
                  {formatCell(key, row[key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > shown.length && (
        <p className="mt-2 text-[10px] text-[var(--color-text-tertiary)]">
          Showing {shown.length} of {rows.length.toLocaleString()} rows ·{' '}
          open the dashboard for the full view.
        </p>
      )}
    </div>
  );
}

function DistributionChart({ intent, rows }: { intent: string; rows: Row[] }) {
  // Resolve the label + value fields (per-intent first, then a heuristic).
  const cols = Object.keys(rows[0] ?? {});
  let labelKey: string | undefined = DIST_FIELD[intent]?.label;
  let valueKey: string | undefined = DIST_FIELD[intent]?.value;
  if (!labelKey || !(labelKey in rows[0])) {
    labelKey = cols.find((k) => typeof rows[0][k] === 'string');
  }
  if (!valueKey || !(valueKey in rows[0])) {
    valueKey = cols.find((k) => typeof rows[0][k] === 'number');
  }
  if (!labelKey || !valueKey) return null;

  const data = rows
    .map((r) => ({ label: String(r[labelKey!]), value: Number(r[valueKey!]) || 0 }))
    .slice(0, 10);
  const height = Math.max(140, data.length * 34);
  const vk = valueKey;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 8 }}>
        <CartesianGrid {...GRID_STYLE} horizontal={false} />
        <XAxis type="number" {...AXIS_STYLE} tickFormatter={(value: unknown) => formatAxis(vk, Number(value))} />
        <YAxis type="category" dataKey="label" width={120} {...AXIS_STYLE} />
        <Tooltip
          {...TOOLTIP_STYLE}
          formatter={(value: unknown) => [formatNumber(vk, Number(value)), humanizeKey(vk)]}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function MetricGrid({ entries }: { entries: [string, unknown][] }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-lg bg-white/[0.03] px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
            {humanizeKey(key)}
          </p>
          <p className="mt-1 font-mono text-sm font-semibold text-white">
            {formatCell(key, value)}
          </p>
        </div>
      ))}
    </div>
  );
}

function KeyValueChips({ title, obj }: { title: string; obj: Record<string, unknown> }) {
  return (
    <div>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
        {title}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {Object.entries(obj).map(([k, v]) => (
          <span
            key={k}
            className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.04] px-2.5 py-1 text-[11px] text-[var(--color-text-secondary)]"
          >
            {humanizeKey(k)}
            <span className="font-mono text-white">{formatCell(k, v)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function StructuredObject({ data }: { data: Record<string, unknown> }) {
  const scalars: [string, unknown][] = [];
  const blocks: React.ReactNode[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (isRowArray(value)) {
      blocks.push(
        <div key={key}>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-text-tertiary)]">
            {humanizeKey(key)}
          </p>
          <ResultTable rows={value} />
        </div>
      );
    } else if (value && typeof value === 'object' && !Array.isArray(value)) {
      blocks.push(<KeyValueChips key={key} title={humanizeKey(key)} obj={value as Record<string, unknown>} />);
    } else if (!Array.isArray(value)) {
      scalars.push([key, value]);
    }
  }
  return (
    <div className="space-y-3">
      {scalars.length > 0 && <MetricGrid entries={scalars} />}
      {blocks}
    </div>
  );
}

export default function StructuredResult({ result }: { result: QueryResult }) {
  const data = result.structured_result;
  const kind = result.result_kind;
  if (data == null || kind === 'text') return null;

  let body: React.ReactNode = null;
  if (isRowArray(data)) {
    body = (
      <>
        {kind === 'distribution' && data.length > 1 && (
          <DistributionChart intent={result.matched_intent} rows={data} />
        )}
        <ResultTable rows={data} />
      </>
    );
  } else if (data && typeof data === 'object' && !Array.isArray(data)) {
    body = <StructuredObject data={data as Record<string, unknown>} />;
  }

  if (!body) return null;
  return <div className="mt-3 space-y-3 border-t border-white/[0.06] pt-3">{body}</div>;
}
