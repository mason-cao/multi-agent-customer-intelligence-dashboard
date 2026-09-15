import { CornerDownRight } from 'lucide-react';

export default function FollowupChips({
  items,
  disabled,
  onAsk,
}: {
  items: string[];
  disabled: boolean;
  onAsk: (q: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <span className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-[var(--color-text-tertiary)]">
        <CornerDownRight className="h-3 w-3" />
        Follow up
      </span>
      {items.map((q) => (
        <button
          key={q}
          onClick={() => onAsk(q)}
          disabled={disabled}
          className="rounded-full border border-white/[0.12] bg-white/[0.03] px-2.5 py-1 text-[11px] text-[var(--color-text-secondary)] transition-colors duration-200 hover:border-primary-400/40 hover:bg-primary-400/10 hover:text-[var(--color-text-accent)] disabled:opacity-50"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
