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
        className={`animate-spin rounded-full border-slate-200 border-t-emerald-600 ${sizes[size]}`}
      />
    </div>
  );
}
