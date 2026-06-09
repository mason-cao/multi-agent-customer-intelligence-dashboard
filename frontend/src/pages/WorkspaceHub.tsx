import { useState, useEffect, useId, useMemo } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import type { AxiosError } from 'axios';
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
import { useActiveWorkspace } from '../contexts/workspaceContextValue';
import {
  useWorkspaces,
  useScenarios,
  useCreateWorkspace,
  useGenerateWorkspace,
  useRotateWorkspaceToken,
  useDeleteWorkspace,
} from '../api/workspaces';
import type { Workspace, Scenario, CreateWorkspaceInput } from '../types/workspace';
import { PALETTE } from '../utils/colors';
import { ADMIN_TOKEN_STORAGE_KEY } from '../constants/workspace';

// ── Constants ────────────────────────────────────────────

const INDUSTRIES = [
  'Technology', 'Healthcare', 'Finance', 'Retail',
  'Manufacturing', 'Education', 'Media', 'Logistics',
];

// ── Scenario visual config ──────────────────────────────

interface ScenarioMeta {
  icon: LucideIcon;
  accentHex: string;
  iconBg: string;
  accentText: string;
  barGradient: string;
}

const SCENARIO_META: Record<string, ScenarioMeta> = {
  velocity_saas: {
    icon: Rocket,
    accentHex: PALETTE.success,
    iconBg: 'bg-success/15',
    accentText: 'text-success',
    barGradient: 'from-success to-success/30',
  },
  atlas_enterprise: {
    icon: Building2,
    accentHex: PALETTE.blue,
    iconBg: 'bg-info/15',
    accentText: 'text-info',
    barGradient: 'from-info to-info/30',
  },
  beacon_analytics: {
    icon: BarChart3,
    accentHex: PALETTE.warning,
    iconBg: 'bg-warning/15',
    accentText: 'text-warning',
    barGradient: 'from-warning to-warning/30',
  },
  meridian_data: {
    icon: Heart,
    accentHex: PALETTE.violet,
    iconBg: 'bg-accent-violet/15',
    accentText: 'text-accent-violet',
    barGradient: 'from-accent-violet to-accent-violet/30',
  },
  custom: {
    icon: Sliders,
    accentHex: PALETTE.indigo,
    iconBg: 'bg-primary-400/15',
    accentText: 'text-primary-400',
    barGradient: 'from-primary-400 to-primary-400/30',
  },
  random: {
    icon: Sparkles,
    accentHex: PALETTE.cyan,
    iconBg: 'bg-accent-cyan/15',
    accentText: 'text-accent-cyan',
    barGradient: 'from-accent-cyan to-accent-cyan/30',
  },
};

const DEFAULT_META: ScenarioMeta = {
  icon: Building2,
  accentHex: PALETTE.indigo,
  iconBg: 'bg-primary-400/15',
  accentText: 'text-primary-400',
  barGradient: 'from-primary-400 to-primary-400/30',
};

function getMeta(scenario: string): ScenarioMeta {
  return SCENARIO_META[scenario] || DEFAULT_META;
}

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

function getApiErrorStatus(error: unknown): number | undefined {
  return (error as AxiosError<ApiErrorBody> | null)?.response?.status;
}

function getApiErrorDetail(error: unknown): string | null {
  const detail = (error as AxiosError<ApiErrorBody> | null)?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.find((item) => typeof item.msg === 'string')?.msg ?? null;
  }
  return null;
}

function getAdminAccessMessage(error: unknown): string | null {
  const status = getApiErrorStatus(error);
  const detail = getApiErrorDetail(error);

  if (status === 401) {
    return 'Workspace management requires an admin token.';
  }
  if (status === 403) {
    return 'The stored admin token was rejected. Enter the current token and retry.';
  }
  if (status === 503) {
    return 'The backend admin token is not configured. Set ADMIN_API_TOKEN on the backend and restart or redeploy it.';
  }
  return detail;
}

function getCreateErrorMessage(error: unknown): string {
  const status = getApiErrorStatus(error);
  const detail = getApiErrorDetail(error);

  if (status === 401) {
    return 'Workspace creation needs an admin token. Enter it on the Workspaces screen and retry.';
  }
  if (status === 403) {
    return 'The admin token was rejected. Update the stored token and retry.';
  }
  if (status === 503) {
    return 'The backend admin token is not configured. Set ADMIN_API_TOKEN on the backend and restart or redeploy it.';
  }
  if (status === 409 && detail) {
    return detail;
  }
  return detail ?? 'Failed to create workspace. Please try again.';
}

// ── Main component ──────────────────────────────────────

export default function WorkspaceHub() {
  const navigate = useNavigate();
  const { activeWorkspace, setActiveWorkspace, clearWorkspace } = useActiveWorkspace();
  const {
    data: list,
    isLoading,
    isError: workspacesIsError,
    error: workspacesError,
    refetch: refetchWorkspaces,
  } = useWorkspaces();
  const { data: scenarios } = useScenarios();

  const [view, setView] = useState<'list' | 'create'>('list');
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Workspace | null>(null);
  const [adminTokenInput, setAdminTokenInput] = useState(() => {
    return localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ?? '';
  });

  // Custom scenario state
  const [customCount, setCustomCount] = useState(2000);
  const [customChurn, setCustomChurn] = useState(0.14);
  const [customIndustry, setCustomIndustry] = useState('Technology');
  const [customOutage, setCustomOutage] = useState(true);
  const [customDescription, setCustomDescription] = useState('');

  const createMutation = useCreateWorkspace();
  const generateMutation = useGenerateWorkspace();
  const rotateTokenMutation = useRotateWorkspaceToken();
  const deleteMutation = useDeleteWorkspace();
  const isDeleting = deleteMutation.isPending;

  const workspaces = useMemo(() => list?.workspaces ?? [], [list?.workspaces]);
  const isSubmitting =
    createMutation.isPending ||
    generateMutation.isPending ||
    rotateTokenMutation.isPending;
  const adminAccessMessage = workspacesIsError
    ? getAdminAccessMessage(workspacesError)
    : null;
  const adminAccessNeedsBackendConfig = getApiErrorStatus(workspacesError) === 503;
  const createErrorMessage = createMutation.isError
    ? getCreateErrorMessage(createMutation.error)
    : null;

  // When generation starts, set workspace as active and navigate to generation view
  useEffect(() => {
    if (!pendingId) return;
    const ws = workspaces.find((w) => w.id === pendingId);
    if (ws?.status === 'generating') {
      setActiveWorkspace(ws);
      navigate('/');
    }
  }, [workspaces, pendingId, setActiveWorkspace, navigate]);

  useEffect(() => {
    if (!deleteTarget) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isDeleting) {
        setDeleteTarget(null);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [deleteTarget, isDeleting]);

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
      setActiveWorkspace(ws);
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

  async function ensureWorkspaceAccess(ws: Workspace): Promise<Workspace> {
    if (ws.access_token) return ws;
    const token = await rotateTokenMutation.mutateAsync(ws.id);
    return { ...ws, access_token: token.access_token };
  }

  async function handleEnter(ws: Workspace) {
    try {
      const authorizedWorkspace = await ensureWorkspaceAccess(ws);
      setActiveWorkspace(authorizedWorkspace);
      navigate('/');
    } catch {
      // Error handled by mutation state
    }
  }

  async function handleGenerate(ws: Workspace) {
    try {
      const authorizedWorkspace = await ensureWorkspaceAccess(ws);
      setActiveWorkspace(authorizedWorkspace);
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

  function handleAdminTokenSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = adminTokenInput.trim();
    if (!token) return;
    localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
    void refetchWorkspaces();
  }

  function handleClearAdminToken() {
    localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
    setAdminTokenInput('');
    void refetchWorkspaces();
  }

  return (
    <div className="bg-app-gradient relative min-h-screen">
      {/* ── Background System ────────────────────────────── */}
      <div className="bg-orbs">
        <div className="bg-orb bg-orb--1" />
        <div className="bg-orb bg-orb--2" />
        <div className="bg-orb bg-orb--3" />
        <div className="bg-orb bg-orb--4" />
        <div className="bg-orb bg-orb--5" />
        <div className="bg-orb bg-orb--6" />
      </div>
      <div className="bg-vignette" />

      {/* ── Header ──────────────────────────────────────── */}
      <header className="glass-surface relative z-10 border-b border-[rgba(255,255,255,0.06)]">
        <div className="mx-auto flex h-14 max-w-5xl items-center px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--color-primary-400)] to-[var(--color-primary-600)] shadow-[0_0_12px_rgba(99,102,241,0.3)]">
              <LayoutDashboard className="h-3.5 w-3.5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-[13px] font-bold tracking-tight text-white">
                Nova
              </span>
              <span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-accent)]">
                Core
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Content ─────────────────────────────────────── */}
      <div className="relative z-10 mx-auto max-w-5xl px-6 py-12">
        {view === 'create' ? (
          <CreateView
            scenarios={scenarios ?? []}
            selectedScenario={selectedScenario}
            workspaceName={workspaceName}
            isSubmitting={isSubmitting}
            errorMessage={createErrorMessage}
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
        ) : adminAccessMessage ? (
          <AdminAccessPanel
            message={adminAccessMessage}
            token={adminTokenInput}
            disableTokenEntry={adminAccessNeedsBackendConfig}
            onChangeToken={setAdminTokenInput}
            onSubmit={handleAdminTokenSubmit}
            onClear={handleClearAdminToken}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,0.6)] p-4 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-workspace-title"
            aria-describedby="delete-workspace-description"
            className="glass-strong w-full max-w-sm rounded-xl p-6"
          >
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-danger/15">
                <Trash2 className="h-5 w-5 text-[var(--color-danger)]" />
              </div>
              <div>
                <h3 id="delete-workspace-title" className="text-sm font-semibold text-white">
                  Delete workspace
                </h3>
                <p id="delete-workspace-description" className="mt-1 text-sm text-[rgba(255,255,255,0.5)]">
                  Are you sure you want to delete{' '}
                  <span className="font-medium text-[rgba(255,255,255,0.7)]">
                    {deleteTarget.company_name}
                  </span>
                  ? This will permanently remove all generated data.
                </p>
              </div>
            </div>
            <div className="mt-5 flex gap-3">
              <button
                type="button"
                autoFocus
                onClick={() => setDeleteTarget(null)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="button"
                aria-label={`Confirm deleting ${deleteTarget.company_name}`}
                onClick={handleDelete}
                disabled={isDeleting}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white transition hover:brightness-95 disabled:opacity-50"
              >
                {isDeleting ? (
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

// ── Admin Access Panel ─────────────────────────────────

function AdminAccessPanel({
  message,
  token,
  disableTokenEntry,
  onChangeToken,
  onSubmit,
  onClear,
}: {
  message: string;
  token: string;
  disableTokenEntry: boolean;
  onChangeToken: (token: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClear: () => void;
}) {
  return (
    <div className="animate-fade-in-up">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--color-primary-400)]">
        Workspace Access
      </p>
      <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
        Admin token required
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-[rgba(255,255,255,0.45)]">
        {message}
      </p>

      <form
        onSubmit={onSubmit}
        className="glass-elevated mt-8 max-w-xl space-y-4 rounded-xl p-6"
      >
        <div>
          <label
            htmlFor="workspace-admin-token"
            className="block text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.48)]"
          >
            Admin token
          </label>
          <input
            id="workspace-admin-token"
            type="password"
            value={token}
            onChange={(event) => onChangeToken(event.target.value)}
            disabled={disableTokenEntry}
            autoComplete="off"
            placeholder={
              disableTokenEntry
                ? 'Configure ADMIN_API_TOKEN on the backend first'
                : 'Enter the workspace admin token'
            }
            className="glass-input mt-2 w-full px-4 py-2.5 text-sm disabled:opacity-50"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={disableTokenEntry || !token.trim()}
            className="btn-primary disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0"
          >
            Save token
            <ArrowRight className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onClear}
            className="btn-secondary"
          >
            Clear stored token
          </button>
        </div>

        <p className="text-xs leading-5 text-[rgba(255,255,255,0.40)]">
          The token is stored only in this browser and sent as the
          <span className="font-mono"> X-Admin-Token</span> header for workspace
          management actions.
        </p>
      </form>
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
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--color-primary-400)]">
        Command Center
      </p>
      <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
        Workspaces
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-[rgba(255,255,255,0.40)]">
        Create company workspaces with realistic synthetic data. Each
        workspace runs an 8-stage intelligence pipeline that generates behavioral
        profiles, segments, churn predictions, and executive insights.
      </p>

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

          {/* New workspace CTA card */}
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
      className={`animate-fade-in-up stagger-${Math.min(index + 1, 5)} glass-elevated overflow-hidden transition-all duration-300 hover:-translate-y-0.5`}
    >
      {/* Colored accent bar */}
      <div className={`h-0.5 bg-gradient-to-r ${meta.barGradient}`} style={{ boxShadow: `0 1px 8px ${meta.accentHex}33` }} />

      <div className="p-6">
        {/* Header */}
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
          {/* Delete button — hidden during generation */}
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

// ── Create View ─────────────────────────────────────────

function CreateView({
  scenarios,
  selectedScenario,
  workspaceName,
  isSubmitting,
  errorMessage,
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
  errorMessage: string | null;
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
  const customNameId = useId();
  const customCountId = useId();
  const customChurnId = useId();
  const customIndustryId = useId();
  const outageLabelId = useId();
  const outageDescriptionId = useId();
  const customDescriptionId = useId();
  const workspaceNameId = useId();

  return (
    <div className="animate-fade-in-up">
      {/* Back */}
      <button
        type="button"
        onClick={onBack}
        className="mb-8 flex items-center gap-1.5 text-sm font-medium text-[rgba(255,255,255,0.5)] transition hover:text-white"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to workspaces
      </button>

      {/* Title */}
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--color-primary-400)]">
        New Workspace
      </p>
      <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
        Choose a Company Profile
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-[rgba(255,255,255,0.40)]">
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
          type="button"
          aria-pressed={isCustom}
          onClick={() => onSelectScenario('custom')}
          className={`animate-fade-in-up stagger-${scenarios.length + 1} glass glass-hover group rounded-xl border p-6 text-left transition-all duration-300 ${
            isCustom
              ? 'border-[var(--color-primary-400)] shadow-[0_0_20px_rgba(129,140,248,0.12),inset_0_0_0_1px_rgba(129,140,248,0.10)]'
              : 'border-[rgba(255,255,255,0.08)] hover:-translate-y-0.5'
          }`}
        >
          <div className="flex items-start gap-3">
            <div
              className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg transition-colors ${
                isCustom ? 'bg-primary-400/15' : 'bg-[rgba(255,255,255,0.04)] ring-1 ring-[rgba(255,255,255,0.08)] group-hover:bg-[rgba(255,255,255,0.08)]'
              }`}
            >
              <Sliders
                className={`h-5 w-5 transition-colors ${isCustom ? 'text-[var(--color-primary-400)]' : 'text-[rgba(255,255,255,0.40)] group-hover:text-[rgba(255,255,255,0.60)]'}`}
              />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-white">
                Build Your Own
              </h3>
              <p className="mt-0.5 text-xs text-[rgba(255,255,255,0.38)]">
                Custom configuration
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-[rgba(255,255,255,0.45)]">
                Configure customer count, churn rate, industry, and more to
                create a tailored scenario for your analysis.
              </p>
            </div>
          </div>
          {isCustom && (
            <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[var(--color-primary-400)]">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Selected
            </div>
          )}
        </button>

        {/* Surprise Me card — immediate create+generate */}
        <button
          type="button"
          onClick={onRandomCreate}
          disabled={isSubmitting}
          className={`animate-fade-in-up stagger-${scenarios.length + 2} glass glass-hover group rounded-xl border border-[rgba(255,255,255,0.08)] p-6 text-left transition-all duration-300 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0`}
        >
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-accent-cyan/10 ring-1 ring-accent-cyan/15 transition-colors group-hover:bg-accent-cyan/15">
              <Sparkles className="h-5 w-5 text-accent-cyan" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-white">
                Surprise Me
              </h3>
              <p className="mt-0.5 text-xs text-[rgba(255,255,255,0.38)]">
                Random company
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-[rgba(255,255,255,0.45)]">
                Generate a random company with varied size, industry, churn
                profile, and business story.
              </p>
            </div>
          </div>
        </button>
      </div>

      {/* Custom scenario controls */}
      {isCustom && (
        <div className="glass mt-8 animate-fade-in space-y-5 p-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-primary-400)]">
            Custom Configuration
          </h3>

          {/* Company name */}
          <div>
            <label htmlFor={customNameId} className="block text-xs font-medium text-[rgba(255,255,255,0.7)]">
              Company Name
            </label>
            <input
              id={customNameId}
              type="text"
              value={workspaceName}
              onChange={(e) => onChangeName(e.target.value)}
              placeholder="My Company"
              className="glass-input mt-1.5 w-full max-w-md px-4 py-2.5 text-sm"
            />
          </div>

          {/* Customer count slider */}
          <div>
            <div className="flex items-center justify-between">
              <label htmlFor={customCountId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Customer Count
              </label>
              <span className="font-mono text-xs font-semibold text-[var(--color-primary-400)]">
                {customCount.toLocaleString()}
              </span>
            </div>
            <input
              id={customCountId}
              type="range"
              min={100}
              max={10000}
              step={100}
              value={customCount}
              onChange={(e) => onChangeCount(Number(e.target.value))}
              className="mt-2 w-full max-w-md"
              style={{ accentColor: 'var(--color-primary-400)' }}
            />
            <div className="mt-1 flex max-w-md justify-between font-mono text-[10px] text-[rgba(255,255,255,0.45)]">
              <span>100</span>
              <span>10,000</span>
            </div>
          </div>

          {/* Churn rate slider */}
          <div>
            <div className="flex items-center justify-between">
              <label htmlFor={customChurnId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Churn Rate
              </label>
              <span className="font-mono text-xs font-semibold text-[var(--color-primary-400)]">
                {Math.round(customChurn * 100)}%
              </span>
            </div>
            <input
              id={customChurnId}
              type="range"
              min={5}
              max={30}
              step={1}
              value={Math.round(customChurn * 100)}
              onChange={(e) => onChangeChurn(Number(e.target.value) / 100)}
              className="mt-2 w-full max-w-md"
              style={{ accentColor: 'var(--color-primary-400)' }}
            />
            <div className="mt-1 flex max-w-md justify-between font-mono text-[10px] text-[rgba(255,255,255,0.45)]">
              <span>5%</span>
              <span>30%</span>
            </div>
          </div>

          {/* Industry dropdown */}
          <div>
            <label htmlFor={customIndustryId} className="block text-xs font-medium text-[rgba(255,255,255,0.7)]">
              Primary Industry
            </label>
            <select
              id={customIndustryId}
              value={customIndustry}
              onChange={(e) => onChangeIndustry(e.target.value)}
              className="glass-input mt-1.5 w-full max-w-md px-4 py-2.5 text-sm"
            >
              {INDUSTRIES.map((ind) => (
                <option key={ind} value={ind} className="bg-[var(--color-bg-end)] text-white">
                  {ind}
                </option>
              ))}
            </select>
          </div>

          {/* Outage toggle */}
          <div className="flex max-w-md items-center justify-between">
            <div>
              <p id={outageLabelId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Include Q3 Service Outage
              </p>
              <p id={outageDescriptionId} className="mt-0.5 text-[11px] text-[rgba(255,255,255,0.45)]">
                Simulates spike in tickets and negative feedback Aug-Sep 2024
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={customOutage}
              aria-labelledby={outageLabelId}
              aria-describedby={outageDescriptionId}
              onClick={() => onChangeOutage(!customOutage)}
              className={`relative h-6 w-11 flex-shrink-0 rounded-full transition-colors ${
                customOutage ? 'bg-[var(--color-primary-400)]' : 'bg-[rgba(255,255,255,0.15)]'
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
              <label htmlFor={customDescriptionId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Scenario Description
                <span className="ml-1 font-normal text-[rgba(255,255,255,0.45)]">(optional)</span>
              </label>
              <span className="font-mono text-[10px] text-[rgba(255,255,255,0.45)]">
                {customDescription.length}/500
              </span>
            </div>
            <textarea
              id={customDescriptionId}
              value={customDescription}
              onChange={(e) => {
                if (e.target.value.length <= 500) onChangeDescription(e.target.value);
              }}
              placeholder="Describe the business scenario for this workspace..."
              rows={3}
              className="glass-input mt-1.5 w-full max-w-md px-4 py-2.5 text-sm"
            />
          </div>
        </div>
      )}

      {/* Name input — appears for archetype scenarios (not custom, which has its own) */}
      {selectedScenario && !isCustom && (
        <div className="mt-8 animate-fade-in">
          <label htmlFor={workspaceNameId} className="block text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
            Workspace Name
          </label>
          <input
            id={workspaceNameId}
            type="text"
            value={workspaceName}
            onChange={(e) => onChangeName(e.target.value)}
            placeholder="Enter a name for this workspace"
            className="glass-input mt-2 w-full max-w-md px-4 py-2.5 text-sm"
          />
        </div>
      )}

      {/* Error */}
      {errorMessage && (
        <div className="mt-4 rounded-lg border border-danger/30 bg-danger/10 p-3">
          <p className="flex items-center gap-2 text-sm text-[var(--color-danger)]">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {errorMessage}
          </p>
        </div>
      )}

      {/* Submit */}
      <div className="mt-8">
        <button
          type="button"
          onClick={onCreate}
          disabled={!selectedScenario || isSubmitting}
          className="btn-primary disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0"
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
      type="button"
      aria-pressed={isSelected}
      onClick={onSelect}
      className={`animate-fade-in-up stagger-${index + 1} glass glass-hover group rounded-xl border p-6 text-left transition-all duration-300 ${
        isSelected
          ? 'border-[var(--color-primary-400)] shadow-[0_0_20px_rgba(129,140,248,0.12),inset_0_0_0_1px_rgba(129,140,248,0.10)]'
          : 'border-[rgba(255,255,255,0.08)] hover:-translate-y-0.5'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg transition-colors ${
            isSelected ? meta.iconBg : 'bg-[rgba(255,255,255,0.04)] ring-1 ring-[rgba(255,255,255,0.08)] group-hover:bg-[rgba(255,255,255,0.08)]'
          }`}
        >
          <Icon
            className={`h-5 w-5 transition-colors ${isSelected ? meta.accentText : 'text-[rgba(255,255,255,0.40)] group-hover:text-[rgba(255,255,255,0.60)]'}`}
          />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-white">
            {scenario.company_name}
          </h3>
          <p className="mt-0.5 text-xs text-[rgba(255,255,255,0.38)]">
            {scenario.industry} &middot;{' '}
            <span className="font-mono">{scenario.customer_count.toLocaleString()}</span> customers &middot;{' '}
            <span className="font-mono">{Math.round(scenario.churn_rate * 100)}%</span> churn
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-[rgba(255,255,255,0.45)]">
            {scenario.description}
          </p>
        </div>
      </div>
      {isSelected && (
        <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[var(--color-primary-400)]">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Selected
        </div>
      )}
    </button>
  );
}
