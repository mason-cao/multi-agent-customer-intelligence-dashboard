interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export default function Card({ children, className = '', hover = false }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-slate-200/60 bg-white p-6 shadow-sm ${
        hover
          ? 'transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md'
          : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}
