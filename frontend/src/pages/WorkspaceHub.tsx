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
  Trash2,
  Sliders,
  Sparkles,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useActiveWorkspace } from '../contexts/WorkspaceContext';
import {
  useWorkspaces,
  useScenarios,
  useCreateWorkspace,
  useGenerateWorkspace,
  useDeleteWorkspace,
} from '../api/workspaces';
import type { Workspace, Scenario, CreateWorkspaceInput } from '../types/workspace';

// ── Constants ────────────────────────────────────────────

const INDUSTRIES = [
  'Technology', 'Healthcare', 'Finance', 'Retail',
  'Manufacturing', 'Education', 'Media', 'Logistics',
];

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
  custom: {
    icon: Sliders,
    accent: 'text-indigo-600',
    bg: 'bg-indigo-50',
    border: 'border-indigo-200',
    bar: 'bg-indigo-500',
  },
  random: {
    icon: Sparkles,
    accent: 'text-rose-600',
    bg: 'bg-rose-50',
    border: 'border-rose-200',
    bar: 'bg-rose-500',
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
  const { activeWorkspace, setActiveWorkspace, clearWorkspace } = useActiveWorkspace();
  const { data: list, isLoading } = useWorkspaces();
  const { data: scenarios } = useScenarios();

  const [view, setView] = useState<'list' | 'create'>('list');
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Workspace | null>(null);

  // Custom scenario state
  const [customCount, setCustomCount] = useState(2000);
  const [customChurn, setCustomChurn] = useState(0.14);
  const [customIndustry, setCustomIndustry] = useState('Technology');
  const [customOutage, setCustomOutage] = useState(true);
  const [customDescription, setCustomDescription] = useState('');

  const createMutation = useCreateWorkspace();
  const generateMutation = useGenerateWorkspace();
  const deleteMutation = useDeleteWorkspace();

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
    if (key === 'custom') {
      setWorkspaceName('');
    } else {
      const scenario = scenarios?.find((s) => s.key === key);
      if (scenario) setWorkspaceName(scenario.company_name);
    }
  }

  async function handleCreateAndGenerate(body: CreateWorkspaceInput) {
    try {
      const ws = await createMutation.mutateAsync(body);
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

  async function handleCreate() {
    if (!selectedScenario || isSubmitting) return;

    let body: CreateWorkspaceInput;

    if (selectedScenario === 'custom') {
      const name = workspaceName.trim() || 'My Company';
      body = {
        name,
        scenario: 'custom',
        industry: customIndustry,
        customer_count: customCount,
        churn_rate: customChurn,
        include_outage: customOutage,
        scenario_description: customDescription.trim() || undefined,
      };
    } else {
      const scenario = scenarios?.find((s) => s.key === selectedScenario);
      const name = workspaceName.trim() || scenario?.company_name || 'My Workspace';
      body = { name, scenario: selectedScenario };
    }

    await handleCreateAndGenerate(body);
  }

  async function handleRandomCreate() {
    if (isSubmitting) return;
    await handleCreateAndGenerate({ name: 'Random', scenario: 'random' });
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

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      const deletedId = deleteTarget.id;
      await deleteMutation.mutateAsync(deletedId);
      setDeleteTarget(null);

      // If we just deleted the active workspace, clear it
      if (activeWorkspace?.id === deletedId) {
        clearWorkspace();
      }
    } catch {
      // Error handled by mutation state
    }
  }

  function openCreateView() {
    setView('create');
    setSelectedScenario(null);
    setWorkspaceName('');
    setCustomCount(2000);
    setCustomChurn(0.14);
    setCustomIndustry('Technology');
    setCustomOutage(true);
    setCustomDescription('');
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
            customCount={customCount}
            customChurn={customChurn}
            customIndustry={customIndustry}
            customOutage={customOutage}
            customDescription={customDescription}
            onSelectScenario={handleSelectScenario}
            onChangeName={setWorkspaceName}
            onChangeCount={setCustomCount}
            onChangeChurn={setCustomChurn}
            onChangeIndustry={setCustomIndustry}
            onChangeOutage={setCustomOutage}
            onChangeDescription={setCustomDescription}
            onCreate={handleCreate}
            onRandomCreate={handleRandomCreate}
            onBack={() => setView('list')}
          />
        ) : (
          <ListView
            workspaces={workspaces}
            isLoading={isLoading}
            pendingId={pendingId}
            onEnter={handleEnter}
            onGenerate={handleGenerate}
            onDelete={setDeleteTarget}
            onCreateNew={openCreateView}
          />
        )}
      </div>

      {/* ── Delete Confirmation Modal ───────────────────── */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-red-50">
                <Trash2 className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Delete workspace
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  Are you sure you want to delete{' '}
                  <span className="font-medium text-slate-700">
                    {deleteTarget.company_name}
                  </span>
                  ? This will permanently remove all generated data.
                </p>
              </div>
            </div>
            <div className="mt-5 flex gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" />
                )}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
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
  onDelete,
  onCreateNew,
}: {
  workspaces: Workspace[];
  isLoading: boolean;
  pendingId: string | null;
  onEnter: (ws: Workspace) => void;
  onGenerate: (ws: Workspace) => void;
  onDelete: (ws: Workspace) => void;
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
              onDelete={() => onDelete(ws)}
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
          {/* Delete button — hidden during generation */}
          {ws.status !== 'generating' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-slate-300 transition hover:bg-red-50 hover:text-red-500"
              title="Delete workspace"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* Status content */}
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

// ── Card status sections ────────────────────────────────

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
      <div className="mt-4 flex gap-2">
        <button
          onClick={onEnter}
          className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-emerald-200 transition-all duration-200 hover:bg-emerald-700 hover:shadow-md active:scale-[0.98]"
        >
          Enter Dashboard
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={onRegenerate}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-400 transition hover:bg-slate-50 hover:text-slate-600"
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
  customCount,
  customChurn,
  customIndustry,
  customOutage,
  customDescription,
  onSelectScenario,
  onChangeName,
  onChangeCount,
  onChangeChurn,
  onChangeIndustry,
  onChangeOutage,
  onChangeDescription,
  onCreate,
  onRandomCreate,
  onBack,
}: {
  scenarios: Scenario[];
  selectedScenario: string | null;
  workspaceName: string;
  isSubmitting: boolean;
  error: boolean;
  customCount: number;
  customChurn: number;
  customIndustry: string;
  customOutage: boolean;
  customDescription: string;
  onSelectScenario: (key: string) => void;
  onChangeName: (name: string) => void;
  onChangeCount: (n: number) => void;
  onChangeChurn: (n: number) => void;
  onChangeIndustry: (s: string) => void;
  onChangeOutage: (b: boolean) => void;
  onChangeDescription: (s: string) => void;
  onCreate: () => void;
  onRandomCreate: () => void;
  onBack: () => void;
}) {
  const isCustom = selectedScenario === 'custom';

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

        {/* Custom scenario card */}
        <button
          onClick={() => onSelectScenario('custom')}
          className={`animate-fade-in-up stagger-${scenarios.length + 1} group rounded-xl border-2 p-6 text-left transition-all duration-200 ${
            isCustom
              ? 'border-indigo-200 bg-indigo-50 shadow-sm'
              : 'border-slate-200/60 bg-white hover:-translate-y-0.5 hover:shadow-md'
          }`}
        >
          <div className="flex items-start gap-3">
            <div
              className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${
                isCustom ? 'bg-indigo-50' : 'bg-slate-100 group-hover:bg-slate-200/60'
              }`}
            >
              <Sliders
                className={`h-5 w-5 ${isCustom ? 'text-indigo-600' : 'text-slate-500'}`}
              />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-slate-900">
                Build Your Own
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Custom configuration
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-600">
                Configure customer count, churn rate, industry, and more to
                create a tailored scenario for your analysis.
              </p>
            </div>
          </div>
          {isCustom && (
            <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-indigo-600">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Selected
            </div>
          )}
        </button>

        {/* Surprise Me card — immediate create+generate */}
        <button
          onClick={onRandomCreate}
          disabled={isSubmitting}
          className={`animate-fade-in-up stagger-${scenarios.length + 2} group rounded-xl border-2 border-slate-200/60 bg-white p-6 text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50`}
        >
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-rose-50 group-hover:bg-rose-100">
              <Sparkles className="h-5 w-5 text-rose-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-slate-900">
                Surprise Me
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Random company
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-600">
                Generate a random company with varied size, industry, churn
                profile, and business story. Great for quick demos.
              </p>
            </div>
          </div>
        </button>
      </div>

      {/* Custom scenario controls */}
      {isCustom && (
        <div className="mt-8 animate-fade-in space-y-5 rounded-xl border border-indigo-100 bg-indigo-50/30 p-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
            Custom Configuration
          </h3>

          {/* Company name */}
          <div>
            <label className="block text-xs font-medium text-slate-600">
              Company Name
            </label>
            <input
              type="text"
              value={workspaceName}
              onChange={(e) => onChangeName(e.target.value)}
              placeholder="My Company"
              className="mt-1.5 w-full max-w-md rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
            />
          </div>

          {/* Customer count slider */}
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-600">
                Customer Count
              </label>
              <span className="text-xs font-semibold text-indigo-600">
                {customCount.toLocaleString()}
              </span>
            </div>
            <input
              type="range"
              min={100}
              max={10000}
              step={100}
              value={customCount}
              onChange={(e) => onChangeCount(Number(e.target.value))}
              className="mt-2 w-full max-w-md accent-indigo-600"
            />
            <div className="mt-1 flex max-w-md justify-between text-[10px] text-slate-400">
              <span>100</span>
              <span>10,000</span>
            </div>
          </div>

          {/* Churn rate slider */}
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-600">
                Churn Rate
              </label>
              <span className="text-xs font-semibold text-indigo-600">
                {Math.round(customChurn * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={5}
              max={30}
              step={1}
              value={Math.round(customChurn * 100)}
              onChange={(e) => onChangeChurn(Number(e.target.value) / 100)}
              className="mt-2 w-full max-w-md accent-indigo-600"
            />
            <div className="mt-1 flex max-w-md justify-between text-[10px] text-slate-400">
              <span>5%</span>
              <span>30%</span>
            </div>
          </div>

          {/* Industry dropdown */}
          <div>
            <label className="block text-xs font-medium text-slate-600">
              Primary Industry
            </label>
            <select
              value={customIndustry}
              onChange={(e) => onChangeIndustry(e.target.value)}
              className="mt-1.5 w-full max-w-md rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
            >
              {INDUSTRIES.map((ind) => (
                <option key={ind} value={ind}>
                  {ind}
                </option>
              ))}
            </select>
          </div>

          {/* Outage toggle */}
          <div className="flex items-center justify-between max-w-md">
            <div>
              <label className="text-xs font-medium text-slate-600">
                Include Q3 Service Outage
              </label>
              <p className="mt-0.5 text-[11px] text-slate-400">
                Simulates spike in tickets and negative feedback Aug-Sep 2024
              </p>
            </div>
            <button
              type="button"
              onClick={() => onChangeOutage(!customOutage)}
              className={`relative h-6 w-11 flex-shrink-0 rounded-full transition-colors ${
                customOutage ? 'bg-indigo-600' : 'bg-slate-200'
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  customOutage ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Scenario description */}
          <div>
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-600">
                Scenario Description
                <span className="ml-1 font-normal text-slate-400">(optional)</span>
              </label>
              <span className="text-[10px] text-slate-400">
                {customDescription.length}/500
              </span>
            </div>
            <textarea
              value={customDescription}
              onChange={(e) => {
                if (e.target.value.length <= 500) onChangeDescription(e.target.value);
              }}
              placeholder="Describe the business scenario for this workspace..."
              rows={3}
              className="mt-1.5 w-full max-w-md rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
            />
          </div>
        </div>
      )}

      {/* Name input — appears for archetype scenarios (not custom, which has its own) */}
      {selectedScenario && !isCustom && (
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
          className={`flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-all duration-200 hover:shadow-md active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 ${
            isCustom
              ? 'bg-indigo-600 shadow-indigo-200 hover:bg-indigo-700 hover:shadow-indigo-200 disabled:hover:bg-indigo-600'
              : 'bg-emerald-600 shadow-emerald-200 hover:bg-emerald-700 hover:shadow-emerald-200 disabled:hover:bg-emerald-600'
          }`}
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
