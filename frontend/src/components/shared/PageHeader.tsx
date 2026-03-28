interface PageHeaderProps {
  title: string;
  description?: string;
}

export default function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold tracking-tight text-white">
        {title}
      </h2>
      {description && (
        <p className="mt-1.5 text-sm leading-relaxed text-[rgba(255,255,255,0.45)]">
          {description}
        </p>
      )}
    </div>
  );
}
