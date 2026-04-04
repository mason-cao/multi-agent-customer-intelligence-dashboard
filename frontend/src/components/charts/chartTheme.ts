export const CHART_COLORS = [
  '#818cf8', // indigo-400 (primary)
  '#34d399', // emerald-400 (success)
  '#fbbf24', // amber-400 (warning)
  '#f87171', // red-400 (danger)
  '#a78bfa', // violet-400
  '#60a5fa', // blue-400
  '#fb923c', // orange-400
  '#f472b6', // pink-400
];

export const AXIS_STYLE = {
  stroke: 'rgba(255,255,255,0.08)',
  fontSize: 11,
  fontFamily: "'Geist Mono', monospace",
  fill: 'rgba(255,255,255,0.38)',
  tick: { fill: 'rgba(255,255,255,0.70)', fontSize: 11, fontFamily: "'Geist Mono', monospace" },
};

export const GRID_STYLE = {
  stroke: 'rgba(255,255,255,0.04)',
  strokeDasharray: '3 3',
};

export const TOOLTIP_STYLE = {
  contentStyle: {
    background: 'rgba(8, 12, 28, 0.92)',
    border: '1px solid rgba(255, 255, 255, 0.10)',
    borderRadius: '0.75rem',
    backdropFilter: 'blur(24px)',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), 0 0 1px rgba(255,255,255,0.08)',
    padding: '8px 12px',
  },
  labelStyle: {
    color: 'rgba(255, 255, 255, 0.95)',
    fontSize: 12,
    fontWeight: 600,
    fontFamily: "'Geist Sans', sans-serif",
    marginBottom: 4,
  },
  itemStyle: {
    color: 'rgba(255, 255, 255, 0.60)',
    fontSize: 11,
    fontFamily: "'Geist Mono', monospace",
    padding: '1px 0',
  },
  cursor: { stroke: 'rgba(255, 255, 255, 0.08)' },
};

export function areaGradientStops(id: string, color: string) {
  return {
    id,
    color,
    stops: [
      { offset: '0%', opacity: 0.3 },
      { offset: '100%', opacity: 0 },
    ],
  };
}

/** Format large numbers with K/M suffixes: 1200 → "1.2K", 2500000 → "2.5M" */
export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}
