interface BadgeProps {
  label: string;
  color?: string;
  variant?: 'solid' | 'subtle';
  size?: 'sm' | 'md';
  className?: string;
}

export default function Badge({
  label,
  color = 'rgba(129,140,248,1)',
  variant = 'subtle',
  size = 'sm',
  className = '',
}: BadgeProps) {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  if (variant === 'solid') {
    return (
      <span
        className={`inline-flex items-center rounded-full font-medium ${sizeClasses} ${className}`}
        style={{ backgroundColor: color, color: '#fff' }}
      >
        {label}
      </span>
    );
  }

  // Subtle variant: use the color at low opacity for bg, full for text
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${sizeClasses} ${className}`}
      style={{
        backgroundColor: color.replace(/[\d.]+\)$/, '0.15)').replace(/^#/, ''),
        color: color,
      }}
    >
      {label}
    </span>
  );
}

// Pre-defined color presets for common badge types
export const BADGE_COLORS = {
  success: 'rgba(52,211,153,1)',
  danger: 'rgba(248,113,113,1)',
  warning: 'rgba(251,191,36,1)',
  info: 'rgba(148,163,184,1)',
  primary: 'rgba(129,140,248,1)',
  violet: 'rgba(167,139,250,1)',
} as const;
