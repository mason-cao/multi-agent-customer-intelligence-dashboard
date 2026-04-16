import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import Card from './Card';

export interface Column<T> {
  key: string;
  label: string;
  align?: 'left' | 'right' | 'center';
  render?: (value: unknown, row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  emptyState?: React.ReactNode;
  className?: string;
}

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  pageSize,
  emptyState,
  className = '',
}: DataTableProps<T>) {
  const [page, setPage] = useState(0);

  const paginated = pageSize ? data.slice(page * pageSize, (page + 1) * pageSize) : data;
  const totalPages = pageSize ? Math.ceil(data.length / pageSize) : 1;

  if (data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  const alignClass = (align?: string) => {
    if (align === 'right') return 'text-right';
    if (align === 'center') return 'text-center';
    return 'text-left';
  };

  return (
    <Card className={className}>
      <div className="overflow-x-auto">
        <table className="metric-table text-sm">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`sticky top-0 z-10 ${alignClass(col.align)}`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className={`transition-colors ${
                  rowIdx % 2 === 1 ? 'bg-[rgba(255,255,255,0.02)]' : ''
                }`}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`text-[rgba(255,255,255,0.7)] ${alignClass(col.align)}`}
                  >
                    {col.render
                      ? col.render(row[col.key], row)
                      : String(row[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pageSize && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between border-t border-[rgba(255,255,255,0.06)] px-4 pt-4">
          <p className="text-xs text-[rgba(255,255,255,0.4)]">
            Page {page + 1} of {totalPages} &middot;{' '}
            <span className="font-mono">{data.length}</span> total
          </p>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="flex h-7 w-7 items-center justify-center rounded-md text-[rgba(255,255,255,0.4)] transition hover:bg-[rgba(255,255,255,0.06)] hover:text-white disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="flex h-7 w-7 items-center justify-center rounded-md text-[rgba(255,255,255,0.4)] transition hover:bg-[rgba(255,255,255,0.06)] hover:text-white disabled:opacity-30"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}
