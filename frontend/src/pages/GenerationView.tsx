import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Shield, CheckCircle2, Sparkles, AlertTriangle } from 'lucide-react';
import type { Workspace } from '../types/workspace';
import { STAGE_ORDER, getStageMeta } from '../components/generation/stages';
import ProgressRing from '../components/generation/ProgressRing';
import StageRow from '../components/generation/StageRow';

export default function GenerationView({
  workspace,
  onComplete,
}: {
  workspace: Workspace;
  onComplete?: () => void;
}) {
  const navigate = useNavigate();
  const isComplete = workspace.status === 'ready';
  const [countdown, setCountdown] = useState(3);
  const [startTime] = useState(() =>
    workspace.generation_started_at
      ? new Date(workspace.generation_started_at).getTime()
      : Date.now()
  );
  const [elapsed, setElapsed] = useState(0);

  // Elapsed time counter
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(Math.max(0, Math.floor((Date.now() - startTime) / 1000)));
    }, 1000);
    return () => clearInterval(timer);
  }, [startTime]);

  // Countdown + redirect after completion
  useEffect(() => {
    if (!isComplete) return;
    if (countdown <= 0) {
      if (onComplete) {
        onComplete();
      } else {
        navigate('/');
      }
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [isComplete, countdown, navigate, onComplete]);

  const stageIndex = workspace.stage_index ?? 0;
  const totalStages = workspace.total_stages ?? 14;
  const progress = isComplete
    ? 100
    : Math.min(100, Math.max(0, Math.round((stageIndex / Math.max(totalStages, 1)) * 100)));
  const currentStage = workspace.current_stage ?? 'Initializing workspace';
  const currentMeta = getStageMeta(currentStage);

  // Determine which index in STAGE_ORDER matches current_stage
  const currentOrderIndex = STAGE_ORDER.indexOf(currentStage);

  const dataStages = STAGE_ORDER.filter(
    (s) => getStageMeta(s).group === 'data'
  );
  const analysisStages = STAGE_ORDER.filter(
    (s) => getStageMeta(s).group === 'analysis'
  );

  function getStageStatus(
    stageName: string
  ): 'completed' | 'current' | 'pending' {
    if (isComplete) return 'completed';
    const idx = STAGE_ORDER.indexOf(stageName);
    if (idx < currentOrderIndex) return 'completed';
    if (idx === currentOrderIndex) return 'current';
    return 'pending';
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  // Final duration is derived from the recorded timestamps (accurate) rather
  // than the live counter, which can drift if the tab was backgrounded.
  const generatedSeconds =
    workspace.completed_at && workspace.generation_started_at
      ? Math.max(
          0,
          Math.round(
            (new Date(workspace.completed_at).getTime() -
              new Date(workspace.generation_started_at).getTime()) /
              1000
          )
        )
      : elapsed;

  if (workspace.status === 'failed') {
    return (
      <div className="flex min-h-full flex-col items-center justify-center px-8 py-12">
        <div className="w-full max-w-lg text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-danger/10 ring-1 ring-danger/20">
            <Shield className="h-8 w-8 text-[var(--color-danger)]" />
          </div>
          <h2 className="mt-5 text-xl font-bold text-white">
            Generation Failed
          </h2>
          <p className="mt-2 text-sm text-[rgba(255,255,255,0.5)]">
            {workspace.user_message ||
              'Something went wrong during data generation. You can retry from the workspace list.'}
          </p>
          <button
            onClick={() => navigate('/workspaces')}
            className="btn-primary mt-6"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Workspaces
          </button>
        </div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center px-8 py-12">
        <div className="w-full max-w-lg text-center">

          <div className="relative mx-auto w-fit">
            <Sparkles className="absolute -left-8 -top-4 h-5 w-5 animate-pulse text-[var(--color-primary-400)] opacity-60" />
            <Sparkles className="absolute -right-8 top-0 h-4 w-4 animate-pulse text-[var(--color-success)] opacity-50 [animation-delay:0.3s]" />
            <Sparkles className="absolute -bottom-2 -left-4 h-3 w-3 animate-pulse text-accent-violet opacity-40 [animation-delay:0.6s]" />

            <div className="relative">
              <ProgressRing progress={100} isComplete />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <CheckCircle2 className="h-10 w-10 text-[var(--color-success)]" />
              </div>
            </div>
          </div>

          <h2 className="mt-6 text-2xl font-bold text-white">
            Your Intelligence Dashboard is Ready
          </h2>
          <p className="mt-2 text-sm text-[rgba(255,255,255,0.5)]">
            {workspace.company_name} &middot;{' '}
            <span className="font-mono">
              {workspace.customer_count.toLocaleString()}
            </span>{' '}
            customers &middot; Generated in {formatTime(generatedSeconds)}
          </p>

          {workspace.pipeline_warnings && (
            <div className="mx-auto mt-5 max-w-sm rounded-lg border border-warning/25 bg-warning/10 px-4 py-3 text-left">
              <div className="flex items-center gap-2 text-[var(--color-warning)]">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-xs font-semibold uppercase tracking-wide">
                  Completed with warnings
                </span>
              </div>
              <ul className="mt-2 space-y-1 text-xs text-[rgba(255,255,255,0.6)]">
                {workspace.pipeline_warnings
                  .split('\n')
                  .filter(Boolean)
                  .map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
              </ul>
            </div>
          )}

          <button
            onClick={() => {
              // Clear the "was generating" flag so Layout swaps to the
              // dashboard; navigate('/') alone is a no-op when already at '/'.
              onComplete?.();
              navigate('/');
            }}
            className="btn-primary mt-6"
          >
            Enter Dashboard
            <Sparkles className="h-4 w-4" />
          </button>

          <p className="mt-3 text-xs text-[rgba(255,255,255,0.3)]">
            Redirecting in {countdown}...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-full flex-col px-8 py-6">

      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/workspaces')}
          className="flex items-center gap-1.5 text-sm text-[rgba(255,255,255,0.5)] transition hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Workspaces
        </button>
        <div className="flex items-center gap-2 text-sm text-[rgba(255,255,255,0.4)]">
          <span className="font-medium text-[rgba(255,255,255,0.7)]">
            {workspace.company_name}
          </span>
          <span>&middot;</span>
          <span>{workspace.industry}</span>
          <span>&middot;</span>
          <span className="font-mono">
            {workspace.customer_count.toLocaleString()}
          </span>
          <span>customers</span>
        </div>
      </div>

      <div className="mt-8 flex flex-col items-center">
        <div className="flex items-center gap-8">

          <div className="relative">
            <ProgressRing progress={progress} isComplete={false} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono text-3xl font-bold text-white">
                {progress}%
              </span>
              <span className="mt-0.5 text-xs text-[rgba(255,255,255,0.4)]">
                {stageIndex} of {totalStages}
              </span>
            </div>
          </div>

          <div className="max-w-sm">
            <div className="flex items-center gap-2">
              <currentMeta.icon className="h-5 w-5 text-[var(--color-primary-400)]" />
              <h2 className="text-lg font-semibold text-white">
                {currentMeta.label}
              </h2>
            </div>
            <p className="mt-1.5 text-sm leading-relaxed text-[rgba(255,255,255,0.5)]">
              {currentMeta.description}
            </p>
            <p className="mt-3 font-mono text-xs text-[rgba(255,255,255,0.3)]">
              Elapsed: {formatTime(elapsed)}
            </p>
          </div>
        </div>
      </div>

      <div className="mx-auto mt-10 w-full max-w-lg">
        <div className="glass rounded-xl p-6">

          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[rgba(255,255,255,0.3)]">
            Data Generation
          </p>
          <div className="mt-2">
            {dataStages.map((stage, i) => (
              <StageRow
                key={stage}
                stageName={stage}
                status={getStageStatus(stage)}
                isFirst={i === 0}
              />
            ))}
          </div>

          <div className="my-3 h-px bg-[rgba(255,255,255,0.06)]" />

          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[rgba(255,255,255,0.3)]">
            Modeling & Analysis
          </p>
          <div className="mt-2">
            {analysisStages.map((stage, i) => (
              <StageRow
                key={stage}
                stageName={stage}
                status={getStageStatus(stage)}
                isFirst={i === 0}
              />
            ))}
          </div>
        </div>
      </div>

      <p className="mt-6 text-center text-xs text-[rgba(255,255,255,0.25)]">
        You'll be redirected to the dashboard when complete
      </p>
    </div>
  );
}
