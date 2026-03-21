interface PageHeaderProps {
  title: string;
  description?: string;
}

export default function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <div className="mb-8">
      <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
        {title}
      </h2>
      {description && (
        <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
          {description}
        </p>
      )}
    </div>
  );
}
