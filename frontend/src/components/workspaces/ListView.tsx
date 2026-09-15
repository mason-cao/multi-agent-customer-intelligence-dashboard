import { LayoutDashboard, Plus, AlertTriangle } from 'lucide-react';
import type { Workspace } from '../../types/workspace';
import WorkspaceCard from './WorkspaceCard';

export default function ListView({
  workspaces,
  isLoading,
  pendingId,
  errorMessage,
  onEnter,
  onGenerate,
  onDelete,
  onCreateNew,
}: {
  workspaces: Workspace[];
  isLoading: boolean;
  pendingId: string | null;
  errorMessage: string | null;
  onEnter: (ws: Workspace) => void;
  onGenerate: (ws: Workspace) => void;
  onDelete: (ws: Workspace) => void;
  onCreateNew: () => void;
}) {
  return (
    <div className="animate-fade-in-up">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--color-primary-400)]">
        Command Center
      </p>
      <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
        Workspaces
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-[rgba(255,255,255,0.40)]">
        Create company workspaces with realistic synthetic data. Each
        workspace runs an 8-agent intelligence pipeline that generates behavioral
        profiles, segments, churn predictions, and executive insights.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onCreateNew}
          className="btn-primary"
        >
          <Plus className="h-4 w-4" />
          New Workspace
        </button>
      </div>

      {errorMessage && (
        <div className="mt-4 max-w-xl rounded-lg border border-danger/30 bg-danger/10 p-3">
          <p className="flex items-center gap-2 text-sm text-[var(--color-danger)]">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {errorMessage}
          </p>
        </div>
      )}

      {isLoading ? (
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className={`glass-elevated animate-fade-in-up stagger-${i + 1} overflow-hidden rounded-xl`}>
              <div className="h-1 shimmer" />
              <div className="p-6 space-y-4">
                <div className="flex items-start gap-3">
                  <div className="h-9 w-9 rounded-lg shimmer" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 rounded shimmer" />
                    <div className="h-3 w-24 rounded shimmer" />
                  </div>
                </div>
                <div className="h-3 w-16 rounded shimmer" />
                <div className="h-9 w-full rounded-lg shimmer" />
              </div>
            </div>
          ))}
        </div>
      ) : workspaces.length === 0 ? (
        <div className="glass-elevated mt-12 flex flex-col items-center px-6 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary-400/10 ring-1 ring-primary-400/15">
            <LayoutDashboard
              className="h-7 w-7 text-[var(--color-primary-400)]"
              strokeWidth={1.5}
            />
          </div>
          <h3 className="mt-5 text-sm font-semibold text-white">
            No workspaces yet
          </h3>
          <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-[rgba(255,255,255,0.38)]">
            Create your first workspace to generate realistic synthetic company
            data and explore customer intelligence.
          </p>
          <button
            type="button"
            onClick={onCreateNew}
            className="btn-primary mt-6"
          >
            <Plus className="h-4 w-4" />
            Create Your First Workspace
          </button>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((ws, i) => (
            <WorkspaceCard
              key={ws.id}
              workspace={ws}
              index={i}
              isPending={ws.id === pendingId}
              onEnter={() => onEnter(ws)}
              onGenerate={() => onGenerate(ws)}
              onDelete={() => onDelete(ws)}
            />
          ))}

          <button
            type="button"
            onClick={onCreateNew}
            className={`animate-fade-in-up stagger-${Math.min(workspaces.length + 1, 5)} group flex flex-col items-center justify-center rounded-xl border border-dashed border-[rgba(255,255,255,0.10)] p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-[var(--color-primary-400)] hover:bg-primary-400/[0.06] hover:shadow-[0_0_20px_rgba(129,140,248,0.08)]`}
            style={{ minHeight: '180px' }}
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[rgba(255,255,255,0.04)] ring-1 ring-[rgba(255,255,255,0.08)] transition-all group-hover:bg-primary-400/10 group-hover:ring-primary-400/20">
              <Plus className="h-5 w-5 text-[rgba(255,255,255,0.30)] transition-colors group-hover:text-[var(--color-primary-400)]" />
            </div>
            <p className="mt-3 text-sm font-medium text-[rgba(255,255,255,0.30)] transition-colors group-hover:text-[var(--color-primary-400)]">
              New Workspace
            </p>
          </button>
        </div>
      )}
    </div>
  );
}
