import { useId } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import Card from './Card';
import useCountUp from '../../hooks/useCountUp';

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: { value: number; label?: string };
  sparkline?: { data: number[]; color?: string };
  variant?: 'default' | 'elevated' | 'hero';
  glowColor?: string;
  className?: string;
}

export default function StatCard({
  title,
  value,
  icon: Icon,
  trend,
  sparkline,
  variant = 'elevated',
  glowColor,
  className = '',
}: StatCardProps) {
  const sparkColor =
    sparkline?.color ??
    (trend && trend.value >= 0
      ? '#5eead4'
      : '#fb7185');
  const sparkShadow =
    trend && trend.value < 0
      ? 'rgba(248, 113, 113, 0.55)'
      : 'rgba(45, 212, 191, 0.50)';

  const sparkData = sparkline
    ? sparkline.data.map((v) => ({ value: v }))
    : undefined;

  const sparkId = `stat-spark-${useId().replace(/:/g, '')}`;

  const numericTarget = typeof value === 'number' ? value : NaN;
  const animated = useCountUp(Number.isFinite(numericTarget) ? numericTarget : 0);
  const displayValue =
    typeof value === 'number' && Number.isFinite(value)
      ? Number.isInteger(value)
        ? Math.round(animated).toLocaleString()
        : animated.toFixed(value.toString().split('.')[1]?.length ?? 1)
      : value;

  const style = glowColor
    ? ({ '--glass-hover-glow': glowColor } as React.CSSProperties)
    : undefined;

  return (
    <Card hover variant={variant} className={className} style={style}>
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {Icon && (
              <Icon className="h-3.5 w-3.5 text-[rgba(255,255,255,0.45)]" />
            )}
            <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.62)]">
              {title}
            </p>
          </div>
          <p className="text-hero mt-3 font-mono text-3xl font-bold tracking-tight leading-none">
            {displayValue}
          </p>
          {trend && (
            <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[rgba(255,255,255,0.68)]">
              {trend.value > 0 && (
                <TrendingUp className="h-3 w-3 text-[var(--color-success)]" />
              )}
              {trend.value < 0 && (
                <TrendingDown className="h-3 w-3 text-[var(--color-danger)]" />
              )}
              {trend.value !== 0 && (
                <span
                  className={
                    trend.value > 0
                      ? 'text-[var(--color-success)]'
                      : 'text-[var(--color-danger)]'
                  }
                >
                  {trend.value > 0 ? '+' : ''}
                  {trend.value}
                </span>
              )}
              {trend.label && <span className="leading-snug">{trend.label}</span>}
            </p>
          )}
        </div>

        {sparkData && (
          <div
            className="h-[58px] w-[88px] shrink-0"
            style={{ filter: `drop-shadow(0 0 10px ${sparkShadow})` }}
          >
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <AreaChart data={sparkData} margin={{ top: 5, right: 2, bottom: 5, left: 2 }}>
                <defs>
                  <linearGradient id={sparkId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={sparkColor} stopOpacity={0.55} />
                    <stop offset="72%" stopColor={sparkColor} stopOpacity={0.14} />
                    <stop offset="100%" stopColor={sparkColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={sparkColor}
                  strokeWidth={2.4}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill={`url(#${sparkId})`}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </Card>
  );
}
