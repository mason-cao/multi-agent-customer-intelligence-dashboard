interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  variant?: 'default' | 'elevated';
}

export default function Card({ children, className = '', hover = false, variant = 'default' }: CardProps) {
  const base = variant === 'elevated' ? 'glass-elevated' : 'glass';
  return (
    <div
      className={`${base} p-6 ${
        hover ? 'glass-hover' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}
