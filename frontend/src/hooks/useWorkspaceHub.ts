import { useState, useEffect, useMemo } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { getApiErrorStatus } from '../api/errors';
import { useActiveWorkspace } from '../contexts/workspaceContextValue';
import { useWorkspaces, useScenarios, useOwnerAccessStatus, useCreateOwnerAccess, useCreateWorkspace, useStartSyntheticWorkspace, useGenerateWorkspace, useRotateWorkspaceToken, useDeleteWorkspace } from '../api/workspaces';
import type { Workspace, CreateWorkspaceInput } from '../types/workspace';
import { shouldShowWorkspaceHubLogout } from '../utils/session';
import { ADMIN_TOKEN_STORAGE_KEY } from '../constants/workspace';
import { getAdminAccessMessage, getCreateErrorMessage, getOwnerAccessErrorMessage, getListActionErrorMessage, getSyntheticErrorMessage } from '../components/workspaces/errors';

export function useWorkspaceHub() {
  const navigate = useNavigate();
  const { activeWorkspace, setActiveWorkspace, clearWorkspace, logout } = useActiveWorkspace();
  const {
    data: list,
    isLoading,
    isError: workspacesIsError,
    error: workspacesError,
    refetch: refetchWorkspaces,
  } = useWorkspaces();
  const { data: scenarios } = useScenarios();
  const { data: ownerAccessStatus } = useOwnerAccessStatus();

  const [view, setView] = useState<'list' | 'create'>('list');
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Workspace | null>(null);
  const [adminTokenInput, setAdminTokenInput] = useState(() => {
    return localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ?? '';
  });

  const [customCount, setCustomCount] = useState(2000);
  const [customChurn, setCustomChurn] = useState(0.14);
  const [customIndustry, setCustomIndustry] = useState('Technology');
  const [customOutage, setCustomOutage] = useState(true);
  const [customDescription, setCustomDescription] = useState('');

  const createMutation = useCreateWorkspace();
  const createOwnerAccessMutation = useCreateOwnerAccess();
  const syntheticMutation = useStartSyntheticWorkspace();
  const generateMutation = useGenerateWorkspace();
  const rotateTokenMutation = useRotateWorkspaceToken();
  const deleteMutation = useDeleteWorkspace();
  const isDeleting = deleteMutation.isPending;

  const workspaces = useMemo(() => list?.workspaces ?? [], [list?.workspaces]);
  const isSubmitting =
    createMutation.isPending ||
    createOwnerAccessMutation.isPending ||
    syntheticMutation.isPending ||
    generateMutation.isPending ||
    rotateTokenMutation.isPending;
  const adminAccessMessage = workspacesIsError
    ? getAdminAccessMessage(workspacesError)
    : null;
  const createErrorMessage = createMutation.isError
    ? getCreateErrorMessage(createMutation.error)
    : null;
  const ownerAccessErrorMessage = createOwnerAccessMutation.isError
    ? getOwnerAccessErrorMessage(createOwnerAccessMutation.error)
    : null;
  const syntheticErrorMessage = syntheticMutation.isError
    ? getSyntheticErrorMessage(syntheticMutation.error)
    : null;
  // Start/enter failures happen from the list view (e.g. 429 capacity), so
  // they need a visible home there — silent failure looks like a dead button.
  const listErrorMessage = generateMutation.isError
    ? getListActionErrorMessage(generateMutation.error)
    : rotateTokenMutation.isError
      ? getListActionErrorMessage(rotateTokenMutation.error)
      : null;
  const deleteErrorMessage = deleteMutation.isError
    ? getListActionErrorMessage(deleteMutation.error)
    : null;
  const ownerSetupRequired =
    ownerAccessStatus?.setup_required ||
    (getApiErrorStatus(workspacesError) === 503 && !ownerAccessStatus?.owner_access_enabled);
  const showLogout = shouldShowWorkspaceHubLogout({
    workspacesIsLoading: isLoading,
    workspacesIsError,
  });

  useEffect(() => {
    if (!pendingId) return;
    const ws = workspaces.find((w) => w.id === pendingId);
    if (ws?.status === 'generating') {
      setActiveWorkspace(ws);
      navigate('/');
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

  async function handleStartSynthetic() {
    if (isSubmitting) return;
    try {
      const ws = await syntheticMutation.mutateAsync();
      setActiveWorkspace(ws);
      setPendingId(ws.id);
      navigate('/');
    } catch {
      // Error shown where the synthetic entry point is rendered.
    }
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

  async function handleOwnerAccessSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = adminTokenInput.trim();
    if (!token) return;
    try {
      if (ownerSetupRequired) {
        await createOwnerAccessMutation.mutateAsync(token);
      }
      localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
      void refetchWorkspaces();
    } catch {
      // Error shown by createOwnerAccessMutation or workspace query state.
    }
  }

  function handleClearOwnerAccess() {
    localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
    setAdminTokenInput('');
    void refetchWorkspaces();
  }

  function handleLogout() {
    logout();
    setAdminTokenInput('');
    setPendingId(null);
    setDeleteTarget(null);
    setView('list');
    void refetchWorkspaces();
  }

  return {
    view, showLogout, handleLogout,
    createProps: {
      scenarios: scenarios ?? [], selectedScenario, workspaceName, isSubmitting,
      errorMessage: createErrorMessage, customCount, customChurn, customIndustry,
      customOutage, customDescription, onSelectScenario: handleSelectScenario,
      onChangeName: setWorkspaceName, onChangeCount: setCustomCount,
      onChangeChurn: setCustomChurn, onChangeIndustry: setCustomIndustry,
      onChangeOutage: setCustomOutage, onChangeDescription: setCustomDescription,
      onCreate: handleCreate, onRandomCreate: handleRandomCreate,
      onBack: () => setView('list'),
    },
    adminAccessMessage,
    adminProps: {
      message: adminAccessMessage ?? '', setupRequired: !!ownerSetupRequired,
      mode: ownerAccessStatus?.mode ?? null, token: adminTokenInput,
      onChangeToken: setAdminTokenInput, onSubmit: handleOwnerAccessSubmit,
      onClear: handleClearOwnerAccess, onStartSynthetic: handleStartSynthetic,
      isSavingOwnerAccess: createOwnerAccessMutation.isPending,
      isStartingSynthetic: syntheticMutation.isPending,
      ownerAccessErrorMessage, syntheticErrorMessage,
    },
    listProps: {
      workspaces, isLoading, pendingId, errorMessage: listErrorMessage,
      onEnter: handleEnter, onGenerate: handleGenerate, onDelete: setDeleteTarget,
      onCreateNew: openCreateView,
    },
    deleteTarget,
    deleteProps: {
      isDeleting, errorMessage: deleteErrorMessage,
      onCancel: () => setDeleteTarget(null), onDelete: handleDelete,
    },
  };
}
