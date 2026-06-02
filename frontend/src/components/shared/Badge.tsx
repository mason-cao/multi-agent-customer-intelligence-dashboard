import type { LucideIcon } from 'lucide-react';

/** Semantic tones map to design tokens (see index.css `@theme`). */
export type BadgeTone = 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'muted';

interface BadgeProps {
  label: string;
  /** Semantic tone — preferred for status/severity/category badges. */
  tone?: BadgeTone;
  /** Explicit color (hex/rgb/rgba) for data-driven categories (segments,
   *  risk tiers, sentiment). Takes precedence over `tone`. */
  color?: string;
  variant?: 'subtle' | 'solid';
  size?: 'sm' | 'md';
  icon?: LucideIcon;
  /** Leading status dot in the badge color. */
  dot?: boolean;
  /** Optional trailing count, rendered monospaced (e.g. category tallies). */
  count?: number | string;
  uppercase?: boolean;
  className?: string;
}

const TONE_VAR: Record<BadgeTone, string> = {
  primary: 'var(--color-primary-400)',
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  danger: 'var(--color-danger)',
  info: 'var(--color-info)',
  muted: 'var(--color-muted)',
};

export default function Badge({
  label,
  tone = 'primary',
  color,
  variant = 'subtle',
  size = 'sm',
  icon: Icon,
  dot = false,
  count,
  uppercase = false,
  className = '',
}: BadgeProps) {
  const c = color ?? TONE_VAR[tone];
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  const style: React.CSSProperties =
    variant === 'solid'
      ? { backgroundColor: c, color: 'var(--color-bg-start)' }
      : { backgroundColor: `color-mix(in oklab, ${c} 15%, transparent)`, color: c };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses} ${
        uppercase ? 'uppercase tracking-wide' : ''
      } ${className}`}
      style={style}
    >
      {dot && (
        <span
          className="h-1.5 w-1.5 shrink-0 rounded-full"
          style={{ backgroundColor: variant === 'solid' ? 'var(--color-bg-start)' : c }}
        />
      )}
      {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
      {label}
      {count != null && <span className="font-mono opacity-70">{count}</span>}
    </span>
  );
}
