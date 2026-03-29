interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  variant?: 'default' | 'elevated' | 'hero';
  style?: React.CSSProperties;
}

const VARIANT_CLASS = {
  default: 'glass',
  elevated: 'glass-elevated',
  hero: 'glass-hero',
} as const;

export default function Card({ children, className = '', hover = false, variant = 'default', style }: CardProps) {
  return (
    <div
      className={`${VARIANT_CLASS[variant]} p-6 ${
        hover ? 'glass-hover' : ''
      } ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}
