import { useState } from 'react';
import type { Key, ReactNode } from 'react';
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
  emptyState?: ReactNode;
  className?: string;
  rowKey?: (row: T, index: number) => Key;
}

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  pageSize,
  emptyState,
  className = '',
  rowKey,
}: DataTableProps<T>) {
  const [page, setPage] = useState(0);

  const totalPages = pageSize ? Math.max(1, Math.ceil(data.length / pageSize)) : 1;
  const safePage = Math.min(page, totalPages - 1);
  const paginated = pageSize
    ? data.slice(safePage * pageSize, (safePage + 1) * pageSize)
    : data;

  if (data.length === 0 && emptyState) {
    return <>{emptyState}</>;
  }

  const alignClass = (align?: string) => {
    if (align === 'right') return 'text-right';
    if (align === 'center') return 'text-center';
    return 'text-left';
  };

  const defaultRowKey = (row: T, absoluteIndex: number): Key => {
    for (const candidate of ['id', 'customer_id', 'order_id', 'ticket_id', 'segment_id']) {
      const value = row[candidate];
      if (typeof value === 'string' || typeof value === 'number') return value;
    }
    return `row-${absoluteIndex}`;
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
            {paginated.map((row, rowIdx) => {
              const absoluteIndex = pageSize ? safePage * pageSize + rowIdx : rowIdx;
              return (
                <tr
                  key={(rowKey ?? defaultRowKey)(row, absoluteIndex)}
                  className={`transition-colors ${
                    rowIdx % 2 === 1 ? 'bg-white/[0.02]' : ''
                  }`}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`text-[var(--color-text-secondary)] ${alignClass(col.align)}`}
                    >
                      {col.render
                        ? col.render(row[col.key], row)
                        : String(row[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pageSize && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] px-4 pt-4">
          <p className="text-xs text-[var(--color-text-tertiary)]">
            Page {safePage + 1} of {totalPages} &middot;{' '}
            <span className="font-mono">{data.length}</span> total
          </p>
          <div className="flex gap-1">
            <button
              type="button"
              aria-label="Previous page"
              onClick={() => setPage(Math.max(0, safePage - 1))}
              disabled={safePage === 0}
              className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--color-text-tertiary)] transition hover:bg-white/5 hover:text-white disabled:opacity-30"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label="Next page"
              onClick={() => setPage(Math.min(totalPages - 1, safePage + 1))}
              disabled={safePage >= totalPages - 1}
              className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--color-text-tertiary)] transition hover:bg-white/5 hover:text-white disabled:opacity-30"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}
