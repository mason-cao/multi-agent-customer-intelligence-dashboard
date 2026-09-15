

export default function ProgressRing({
  progress,
  isComplete,
}: {
  progress: number;
  isComplete: boolean;
}) {
  const radius = 68;
  const stroke = 6;
  const center = 80;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  const strokeColor = isComplete
    ? 'var(--color-success)'
    : 'var(--color-primary-400)';
  const glowColor = isComplete
    ? 'color-mix(in oklab, var(--color-success) 40%, transparent)'
    : 'color-mix(in oklab, var(--color-primary-400) 30%, transparent)';

  return (
    <svg
      width={center * 2}
      height={center * 2}
      className="drop-shadow-lg"
    >

      <defs>
        <filter id="ring-glow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={stroke}
      />

      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={strokeColor}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${center} ${center})`}
        style={{
          transition: 'stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.4s ease',
          filter: `drop-shadow(0 0 8px ${glowColor})`,
        }}
      />
    </svg>
  );
}
