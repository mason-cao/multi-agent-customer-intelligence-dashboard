import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Plus,
  ArrowRight,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Building2,
  Rocket,
  BarChart3,
  Heart,
  ChevronLeft,
  RefreshCw,
  Play,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useActiveWorkspace } from '../contexts/WorkspaceContext';
import {
  useWorkspaces,
  useScenarios,
  useCreateWorkspace,
  useGenerateWorkspace,
} from '../api/workspaces';
import type { Workspace, Scenario } from '../types/workspace';

// ── Scenario visual config ──────────────────────────────

interface ScenarioMeta {
  icon: LucideIcon;
  accent: string;
  bg: string;
  border: string;
  bar: string;
}

const SCENARIO_META: Record<string, ScenarioMeta> = {
  velocity_saas: {
    icon: Rocket,
    accent: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    bar: 'bg-emerald-500',
  },
  atlas_enterprise: {
    icon: Building2,
    accent: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    bar: 'bg-blue-500',
  },
  beacon_analytics: {
    icon: BarChart3,
    accent: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    bar: 'bg-amber-500',
  },
  meridian_data: {
    icon: Heart,
    accent: 'text-purple-600',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    bar: 'bg-purple-500',
  },
};

const DEFAULT_META: ScenarioMeta = {
  icon: Building2,
  accent: 'text-slate-600',
  bg: 'bg-slate-100',
  border: 'border-slate-200',
  bar: 'bg-slate-400',
};

function getMeta(scenario: string): ScenarioMeta {
  return SCENARIO_META[scenario] || DEFAULT_META;
}

// ── Main component ──────────────────────────────────────

export default function WorkspaceHub() {
  const navigate = useNavigate();
  const { setActiveWorkspace } = useActiveWorkspace();
  const { data: list, isLoading } = useWorkspaces();
  const { data: scenarios } = useScenarios();

  const [view, setView] = useState<'list' | 'create'>('list');
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [pendingId, setPendingId] = useState<string | null>(null);

  const createMutation = useCreateWorkspace();
  const generateMutation = useGenerateWorkspace();

  const workspaces = list?.workspaces ?? [];
  const isSubmitting = createMutation.isPending || generateMutation.isPending;

  // Auto-enter dashboard when the workspace we just created becomes ready
  useEffect(() => {
    if (!pendingId) return;
    const ws = workspaces.find((w) => w.id === pendingId);
    if (ws?.status === 'ready') {
      const timer = setTimeout(() => {
        setActiveWorkspace(ws);
        navigate('/');
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [workspaces, pendingId, setActiveWorkspace, navigate]);

  function handleSelectScenario(key: string) {
    setSelectedScenario(key);
    const scenario = scenarios?.find((s) => s.key === key);
    if (scenario) setWorkspaceName(scenario.company_name);
  }

  async function handleCreate() {
    if (!selectedScenario || isSubmitting) return;
    const scenario = scenarios?.find((s) => s.key === selectedScenario);
    const name =
      workspaceName.trim() || scenario?.company_name || 'My Workspace';

    try {
      const ws = await createMutation.mutateAsync({
        name,
        scenario: selectedScenario,
      });
      setPendingId(ws.id);
      setView('list');
      setSelectedScenario(null);
      setWorkspaceName('');

      try {
        await generateMutation.mutateAsync(ws.id);
      } catch {
        // Generate failed after create — workspace appears in list as "created"
      }
    } catch {
      // Create failed — stay on create view, error shown via mutation state
    }
  }

  function handleEnter(ws: Workspace) {
    setActiveWorkspace(ws);
    navigate('/');
  }

  async function handleGenerate(ws: Workspace) {
    try {
      await generateMutation.mutateAsync(ws.id);
      setPendingId(ws.id);
    } catch {
      // Error handled by mutation state
    }
  }

  function openCreateView() {
    setView('create');
    setSelectedScenario(null);
    setWorkspaceName('');
    createMutation.reset();
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-5xl items-center px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600">
              <LayoutDashboard className="h-4 w-4 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-slate-900">
                Luminosity
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-widest text-emerald-600">
                Intelligence
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Content ─────────────────────────────────────── */}
      <div className="mx-auto max-w-5xl px-6 py-12">
        {view === 'create' ? (
          <CreateView
            scenarios={scenarios ?? []}
            selectedScenario={selectedScenario}
            workspaceName={workspaceName}
            isSubmitting={isSubmitting}
            error={createMutation.isError}
            onSelectScenario={handleSelectScenario}
            onChangeName={setWorkspaceName}
            onCreate={handleCreate}
            onBack={() => setView('list')}
          />
        ) : (
          <ListView
            workspaces={workspaces}
            isLoading={isLoading}
            pendingId={pendingId}
            onEnter={handleEnter}
            onGenerate={handleGenerate}
            onCreateNew={openCreateView}
          />
        )}
      </div>
    </div>
  );
}

// ── List View ───────────────────────────────────────────

function ListView({
  workspaces,
  isLoading,
  pendingId,
  onEnter,
  onGenerate,
  onCreateNew,
}: {
  workspaces: Workspace[];
  isLoading: boolean;
  pendingId: string | null;
  onEnter: (ws: Workspace) => void;
  onGenerate: (ws: Workspace) => void;
  onCreateNew: () => void;
}) {
  return (
    <div className="animate-fade-in-up">
      <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
        Workspaces
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
        Create demo company workspaces with realistic synthetic data. Each
        workspace runs an 8-agent AI pipeline that generates behavioral
        profiles, segments, churn predictions, and executive insights.
      </p>

      {isLoading ? (
        <div className="mt-16 flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-emerald-600" />
        </div>
      ) : workspaces.length === 0 ? (
        <div className="mt-12 flex flex-col items-center rounded-xl border border-dashed border-slate-200 bg-white/50 px-6 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50">
            <LayoutDashboard
              className="h-7 w-7 text-emerald-600"
              strokeWidth={1.5}
            />
          </div>
          <h3 className="mt-5 text-sm font-semibold text-slate-700">
            No workspaces yet
          </h3>
          <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-slate-400">
            Create your first workspace to generate realistic synthetic company
            data and explore AI-driven customer intelligence.
          </p>
          <button
            onClick={onCreateNew}
            className="mt-6 flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm shadow-emerald-200 transition-all duration-200 hover:bg-emerald-700 hover:shadow-md hover:shadow-emerald-200 active:scale-[0.98]"
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
            />
          ))}

          {/* New workspace CTA card */}
          <button
            onClick={onCreateNew}
            className={`animate-fade-in-up stagger-${Math.min(workspaces.length + 1, 5)} flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-white/50 p-6 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white hover:shadow-sm`}
            style={{ minHeight: '180px' }}
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
              <Plus className="h-5 w-5 text-slate-400" />
            </div>
            <p className="mt-3 text-sm font-medium text-slate-600">
              New Workspace
            </p>
          </button>
        </div>
      )}
    </div>
  );
}

// ── Workspace Card ──────────────────────────────────────

function WorkspaceCard({
  workspace: ws,
  index,
  isPending,
  onEnter,
  onGenerate,
}: {
  workspace: Workspace;
  index: number;
  isPending: boolean;
  onEnter: () => void;
  onGenerate: () => void;
}) {
  const meta = getMeta(ws.scenario);
  const Icon = meta.icon;

  return (
    <div
      className={`animate-fade-in-up stagger-${Math.min(index + 1, 5)} overflow-hidden rounded-xl border border-slate-200/60 bg-white shadow-sm`}
    >
      {/* Colored accent bar */}
      <div className={`h-1 ${meta.bar}`} />

      <div className="p-6">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div
            className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${meta.bg}`}
          >
            <Icon className={`h-[18px] w-[18px] ${meta.accent}`} />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-sm font-semibold text-slate-900">
              {ws.company_name}
            </h3>
            <p className="text-xs text-slate-500">
              {ws.industry} &middot;{' '}
              {ws.customer_count.toLocaleString()} customers
            </p>
          </div>
        </div>

        {/* Status content */}
        <div className="mt-4">
          {ws.status === 'ready' && (
            <ReadyStatus ws={ws} onEnter={onEnter} />
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

// ── Card status sections ────────────────────────────────

function ReadyStatus({
  ws,
  onEnter,
}: {
  ws: Workspace;
  onEnter: () => void;
}) {
  return (
    <>
      <p className="flex items-center gap-1.5 text-xs font-medium text-emerald-600">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Ready
      </p>
      <p className="mt-1 text-[11px] text-slate-400">
        Created{' '}
        {new Date(ws.created_at).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })}
      </p>
      <button
        onClick={onEnter}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-emerald-200 transition-all duration-200 hover:bg-emerald-700 hover:shadow-md active:scale-[0.98]"
      >
        Enter Dashboard
        <ArrowRight className="h-3.5 w-3.5" />
      </button>
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
      ? Math.round((ws.stage_index / ws.total_stages) * 100)
      : 0;

  return (
    <>
      <div className="flex items-center gap-1.5">
        <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-600" />
        <p className="text-xs font-medium text-slate-600">
          {ws.current_stage || 'Initializing...'}
        </p>
      </div>
      {ws.stage_index != null && ws.total_stages && (
        <div className="mt-2">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-[11px] text-slate-400">
              Stage {ws.stage_index} of {ws.total_stages}
            </p>
            <p className="text-[11px] text-slate-400">{progress}%</p>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-700 ease-out"
              style={{ width: `${Math.max(progress, 3)}%` }}
            />
          </div>
        </div>
      )}
      {isPending && (
        <p className="mt-2 text-[11px] text-emerald-600">
          You'll be redirected when ready...
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
      <p className="flex items-center gap-1.5 text-xs font-medium text-red-600">
        <AlertTriangle className="h-3.5 w-3.5" />
        Generation failed
      </p>
      {ws.error_message && (
        <p className="mt-1 line-clamp-2 text-[11px] text-red-400">
          {ws.error_message}
        </p>
      )}
      <button
        onClick={onRetry}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
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
      <p className="text-xs text-slate-400">Not generated yet</p>
      <button
        onClick={onGenerate}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-100"
      >
        <Play className="h-3.5 w-3.5" />
        Generate Data
      </button>
    </>
  );
}

// ── Create View ─────────────────────────────────────────

function CreateView({
  scenarios,
  selectedScenario,
  workspaceName,
  isSubmitting,
  error,
  onSelectScenario,
  onChangeName,
  onCreate,
  onBack,
}: {
  scenarios: Scenario[];
  selectedScenario: string | null;
  workspaceName: string;
  isSubmitting: boolean;
  error: boolean;
  onSelectScenario: (key: string) => void;
  onChangeName: (name: string) => void;
  onCreate: () => void;
  onBack: () => void;
}) {
  return (
    <div className="animate-fade-in-up">
      {/* Back */}
      <button
        onClick={onBack}
        className="mb-8 flex items-center gap-1.5 text-sm font-medium text-slate-500 transition hover:text-slate-700"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to workspaces
      </button>

      {/* Title */}
      <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
        Choose a Company Profile
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500">
        Each scenario generates realistic synthetic data with different industry
        dynamics, customer behavior patterns, and business challenges.
      </p>

      {/* Scenario cards */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {scenarios.map((scenario, i) => (
          <ScenarioCard
            key={scenario.key}
            scenario={scenario}
            index={i}
            isSelected={selectedScenario === scenario.key}
            onSelect={() => onSelectScenario(scenario.key)}
          />
        ))}
      </div>

      {/* Name input — appears after scenario selection */}
      {selectedScenario && (
        <div className="mt-8 animate-fade-in">
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-400">
            Workspace Name
          </label>
          <input
            type="text"
            value={workspaceName}
            onChange={(e) => onChangeName(e.target.value)}
            placeholder="Enter a name for this workspace"
            className="mt-2 w-full max-w-md rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition focus:border-emerald-300 focus:ring-2 focus:ring-emerald-100"
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="flex items-center gap-2 text-sm text-red-600">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            Failed to create workspace. Please try again.
          </p>
        </div>
      )}

      {/* Submit */}
      <div className="mt-8">
        <button
          onClick={onCreate}
          disabled={!selectedScenario || isSubmitting}
          className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm shadow-emerald-200 transition-all duration-200 hover:bg-emerald-700 hover:shadow-md hover:shadow-emerald-200 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-emerald-600 disabled:hover:shadow-sm disabled:active:scale-100"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creating workspace...
            </>
          ) : (
            <>
              Create & Generate
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// ── Scenario Card ───────────────────────────────────────

function ScenarioCard({
  scenario,
  index,
  isSelected,
  onSelect,
}: {
  scenario: Scenario;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const meta = getMeta(scenario.key);
  const Icon = meta.icon;

  return (
    <button
      onClick={onSelect}
      className={`animate-fade-in-up stagger-${index + 1} group rounded-xl border-2 p-6 text-left transition-all duration-200 ${
        isSelected
          ? `${meta.border} ${meta.bg} shadow-sm`
          : 'border-slate-200/60 bg-white hover:-translate-y-0.5 hover:shadow-md'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${
            isSelected ? meta.bg : 'bg-slate-100 group-hover:bg-slate-200/60'
          }`}
        >
          <Icon
            className={`h-5 w-5 ${isSelected ? meta.accent : 'text-slate-500'}`}
          />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-slate-900">
            {scenario.company_name}
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            {scenario.industry} &middot;{' '}
            {scenario.customer_count.toLocaleString()} customers &middot;{' '}
            {Math.round(scenario.churn_rate * 100)}% churn
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-slate-600">
            {scenario.description}
          </p>
        </div>
      </div>
      {isSelected && (
        <div
          className={`mt-3 flex items-center gap-1.5 text-xs font-medium ${meta.accent}`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          Selected
        </div>
      )}
    </button>
  );
}
