import { ArrowRight, Loader2, AlertTriangle, CheckCircle2, RefreshCw, Play, Trash2 } from 'lucide-react';
import type { Workspace } from '../../types/workspace';
import { getMeta } from './scenarioMeta';

export default function WorkspaceCard({
  workspace: ws,
  index,
  isPending,
  onEnter,
  onGenerate,
  onDelete,
}: {
  workspace: Workspace;
  index: number;
  isPending: boolean;
  onEnter: () => void;
  onGenerate: () => void;
  onDelete: () => void;
}) {
  const meta = getMeta(ws.scenario);
  const Icon = meta.icon;

  return (
    <div
      className={`animate-fade-in-up stagger-${Math.min(index + 1, 5)} glass-elevated overflow-hidden transition-all duration-300 hover:-translate-y-0.5`}
    >

      <div className={`h-0.5 bg-gradient-to-r ${meta.barGradient}`} style={{ boxShadow: `0 1px 8px ${meta.accentHex}33` }} />

      <div className="p-6">

        <div className="flex items-start gap-3">
          <div
            className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${meta.iconBg}`}
          >
            <Icon className={`h-[18px] w-[18px] ${meta.accentText}`} />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-sm font-semibold text-white">
              {ws.company_name}
            </h3>
            <p className="text-xs text-[rgba(255,255,255,0.5)]">
              {ws.industry} &middot;{' '}
              <span className="font-mono">{ws.customer_count.toLocaleString()}</span> customers
            </p>
          </div>

          {ws.status !== 'generating' && (
            <button
              type="button"
              aria-label={`Delete workspace ${ws.company_name}`}
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-[rgba(255,255,255,0.3)] transition hover:bg-danger/15 hover:text-[var(--color-danger)]"
              title="Delete workspace"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
        </div>

        <div className="mt-4">
          {ws.status === 'ready' && (
            <ReadyStatus ws={ws} onEnter={onEnter} onRegenerate={onGenerate} />
          )}
          {ws.status === 'generating' && (
            <GeneratingStatus ws={ws} isPending={isPending} />
          )}
          {ws.status === 'failed' && (
            <FailedStatus ws={ws} onRetry={onGenerate} />
          )}
          {ws.status === 'created' && (
            <CreatedStatus onGenerate={onGenerate} />
          )}
        </div>
      </div>
    </div>
  );
}

function ReadyStatus({
  ws,
  onEnter,
  onRegenerate,
}: {
  ws: Workspace;
  onEnter: () => void;
  onRegenerate: () => void;
}) {
  return (
    <>
      <p className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-success)]">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Ready
      </p>
      <p className="mt-1 text-[11px] text-[rgba(255,255,255,0.5)]">
        Created{' '}
        {new Date(ws.created_at).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })}
      </p>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={onEnter}
          className="btn-primary flex-1 py-2 text-sm"
        >
          Enter Dashboard
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          aria-label={`Regenerate data for ${ws.company_name}`}
          onClick={onRegenerate}
          className="btn-secondary flex h-9 w-9 items-center justify-center !px-0"
          title="Regenerate data"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>
    </>
  );
}

function GeneratingStatus({
  ws,
  isPending,
}: {
  ws: Workspace;
  isPending: boolean;
}) {
  const progress =
    ws.stage_index != null && ws.total_stages
      ? Math.min(100, Math.max(0, Math.round((ws.stage_index / Math.max(ws.total_stages, 1)) * 100)))
      : 0;

  return (
    <>
      <div className="flex items-center gap-1.5">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--color-primary-400)]" />
        <p className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
          {ws.current_stage || 'Initializing...'}
        </p>
      </div>
      {ws.stage_index != null && ws.total_stages && (
        <div className="mt-2">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-[11px] text-[rgba(255,255,255,0.5)]">
              Stage {ws.stage_index} of {ws.total_stages}
            </p>
            <p className="font-mono text-[11px] text-[rgba(255,255,255,0.5)]">{progress}%</p>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-[rgba(255,255,255,0.06)]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary-500)] to-[var(--color-primary-400)] transition-all duration-700 ease-out"
              style={{ width: `${Math.max(progress, 3)}%`, boxShadow: '0 0 8px rgba(129,140,248,0.4)' }}
            />
          </div>
        </div>
      )}
      {isPending && (
        <p className="mt-2 text-[11px] text-[var(--color-primary-400)]">
          Opening the setup view...
        </p>
      )}
    </>
  );
}

function FailedStatus({
  ws,
  onRetry,
}: {
  ws: Workspace;
  onRetry: () => void;
}) {
  return (
    <>
      <p className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-danger)]">
        <AlertTriangle className="h-3.5 w-3.5" />
        Generation failed
      </p>
      <p className="mt-1 line-clamp-2 text-[11px] text-[rgba(255,255,255,0.5)]">
        {ws.user_message || 'This workspace failed to set up. You can try again.'}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white transition hover:brightness-95"
      >
        <RefreshCw className="h-3.5 w-3.5" />
        Retry Generation
      </button>
    </>
  );
}

function CreatedStatus({ onGenerate }: { onGenerate: () => void }) {
  return (
    <>
      <p className="text-xs text-[rgba(255,255,255,0.5)]">Not generated yet</p>
      <button
        type="button"
        onClick={onGenerate}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-[var(--color-primary-400)] bg-primary-400/10 px-4 py-2 text-sm font-medium text-[var(--color-primary-400)] transition hover:bg-primary-400/20"
      >
        <Play className="h-3.5 w-3.5" />
        Generate Data
      </button>
    </>
  );
}
