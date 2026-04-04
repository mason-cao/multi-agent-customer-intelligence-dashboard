import type { LucideIcon } from 'lucide-react';
import Card from './Card';

interface ChartCardProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  children: React.ReactNode;
  variant?: 'default' | 'elevated' | 'hero';
  className?: string;
}

export default function ChartCard({
  title,
  description,
  icon: Icon,
  children,
  variant = 'default',
  className = '',
}: ChartCardProps) {
  return (
    <Card variant={variant} className={className}>
      <div className="mb-4">
        <div className="flex items-center gap-2">
          {Icon && (
            <Icon className="h-4 w-4 text-[var(--color-primary-400)]" />
          )}
          <h3 className="text-sm font-semibold text-white">{title}</h3>
        </div>
        {description && (
          <p className="mt-1 text-xs text-[rgba(255,255,255,0.4)]">
            {description}
          </p>
        )}
      </div>
      {children}
    </Card>
  );
}
