interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
}

const sizes = {
  sm: 'h-5 w-5 border-2',
  md: 'h-8 w-8 border-[3px]',
  lg: 'h-12 w-12 border-4',
};

export default function LoadingSpinner({ size = 'md' }: LoadingSpinnerProps) {
  return (
    <div className="flex items-center justify-center py-12">
      <div
        className={`animate-spin rounded-full border-[rgba(255,255,255,0.08)] border-t-[var(--color-primary-400)] ${sizes[size]}`}
      />
    </div>
  );
}
