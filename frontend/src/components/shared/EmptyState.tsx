import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="glass flex flex-col items-center justify-center px-6 py-20">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[rgba(129,140,248,0.08)] ring-1 ring-[rgba(129,140,248,0.12)]">
        <Icon className="h-7 w-7 text-[var(--color-primary-400)]" strokeWidth={1.5} />
      </div>
      <h3 className="mt-5 text-sm font-semibold text-white">{title}</h3>
      <p className="mt-2 max-w-sm text-center text-[13px] leading-relaxed text-[rgba(255,255,255,0.45)]">
        {description}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          className="btn-primary mt-6"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
