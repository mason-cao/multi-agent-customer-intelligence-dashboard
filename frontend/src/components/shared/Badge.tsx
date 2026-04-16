interface BadgeProps {
  label: string;
  color?: string;
  variant?: 'solid' | 'subtle';
  size?: 'sm' | 'md';
  className?: string;
}

function getSubtleBackground(color: string) {
  const rgbaMatch = color.match(/^rgba\((.+),\s*[\d.]+\)$/i);
  if (rgbaMatch) return `rgba(${rgbaMatch[1]}, 0.15)`;

  const rgbMatch = color.match(/^rgb\((.+)\)$/i);
  if (rgbMatch) return `rgba(${rgbMatch[1]}, 0.15)`;

  const hexMatch = color.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hexMatch) {
    const raw = hexMatch[1];
    const hex = raw.length === 3
      ? raw.split('').map((char) => char + char).join('')
      : raw;
    const value = Number.parseInt(hex, 16);
    const r = (value >> 16) & 255;
    const g = (value >> 8) & 255;
    const b = value & 255;
    return `rgba(${r}, ${g}, ${b}, 0.15)`;
  }

  return color;
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
        backgroundColor: getSubtleBackground(color),
        color: color,
      }}
    >
      {label}
    </span>
  );
}
