import type { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export default function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white/50 px-6 py-20">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
        <Icon className="h-7 w-7 text-slate-400" strokeWidth={1.5} />
      </div>
      <h3 className="mt-5 text-sm font-semibold text-slate-700">{title}</h3>
      <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-slate-400">
        {description}
      </p>
    </div>
  );
}
