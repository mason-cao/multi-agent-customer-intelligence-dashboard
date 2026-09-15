import { CheckCircle2 } from 'lucide-react';
import { getStageMeta } from './stages';

export default function StageRow({
  stageName,
  status,
  isFirst,
}: {
  stageName: string;
  status: 'completed' | 'current' | 'pending';
  isFirst: boolean;
}) {
  const meta = getStageMeta(stageName);
  const Icon = meta.icon;

  return (
    <div
      className={`flex items-center gap-3 py-2 ${isFirst ? '' : ''} ${
        status === 'completed'
          ? 'opacity-60'
          : status === 'pending'
            ? 'opacity-30'
            : ''
      }`}
    >

      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center">
        {status === 'completed' ? (
          <CheckCircle2 className="h-4 w-4 text-[var(--color-success)]" />
        ) : status === 'current' ? (
          <div className="relative flex h-5 w-5 items-center justify-center">
            <div className="absolute inset-0 animate-ping rounded-full bg-[var(--color-primary-400)] opacity-20" />
            <div className="h-2.5 w-2.5 rounded-full bg-[var(--color-primary-400)] shadow-[0_0_8px_rgba(129,140,248,0.5)]" />
          </div>
        ) : (
          <div className="h-2 w-2 rounded-full bg-[rgba(255,255,255,0.15)]" />
        )}
      </div>

      <div
        className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md ${
          status === 'current'
            ? 'bg-primary-400/15'
            : 'bg-[rgba(255,255,255,0.04)]'
        }`}
      >
        <Icon
          className={`h-3.5 w-3.5 ${
            status === 'current'
              ? 'text-[var(--color-primary-400)]'
              : 'text-[rgba(255,255,255,0.5)]'
          } ${status === 'current' && stageName === 'Initializing workspace' ? 'animate-spin' : ''}`}
        />
      </div>

      <span
        className={`text-sm ${
          status === 'current'
            ? 'font-medium text-white'
            : 'text-[rgba(255,255,255,0.70)]'
        }`}
      >
        {meta.label}
      </span>
    </div>
  );
}
