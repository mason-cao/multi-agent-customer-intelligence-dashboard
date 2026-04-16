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
      <div className="panel-title-bar">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {Icon && (
              <Icon className="h-4 w-4 shrink-0 text-[var(--color-primary-400)]" />
            )}
            <h3 className="text-sm font-semibold">{title}</h3>
          </div>
          {description && (
            <p className="mt-1 text-xs">
              {description}
            </p>
          )}
        </div>
      </div>
      {children}
    </Card>
  );
}
