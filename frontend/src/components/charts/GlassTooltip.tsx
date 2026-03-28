interface GlassTooltipProps {
  active?: boolean;
  payload?: Array<{
    color?: string;
    name?: string;
    value?: number;
  }>;
  label?: string;
  formatter?: (value: number) => string;
}

export default function GlassTooltip({ active, payload, label, formatter }: GlassTooltipProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-[rgba(255,255,255,0.15)] bg-[rgba(15,23,42,0.9)] px-3 py-2 shadow-xl backdrop-blur-md">
      {label && (
        <p className="mb-1 text-xs font-semibold text-white">{label}</p>
      )}
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: entry.color }}
          />
          <span className="font-mono text-[11px] text-[rgba(255,255,255,0.7)]">
            {entry.name}:{' '}
            {formatter && typeof entry.value === 'number'
              ? formatter(entry.value)
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}
