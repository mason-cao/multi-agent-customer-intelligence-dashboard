import type { FormEvent } from 'react';
import { ArrowRight, Loader2, AlertTriangle, Sparkles } from 'lucide-react';

export default function AdminAccessPanel({
  message,
  setupRequired,
  mode,
  token,
  onChangeToken,
  onSubmit,
  onClear,
  onStartSynthetic,
  isSavingOwnerAccess,
  isStartingSynthetic,
  ownerAccessErrorMessage,
  syntheticErrorMessage,
}: {
  message: string;
  setupRequired: boolean;
  mode: 'deployment_token' | 'owner_passcode' | 'setup_required' | null;
  token: string;
  onChangeToken: (token: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClear: () => void;
  onStartSynthetic: () => void;
  isSavingOwnerAccess: boolean;
  isStartingSynthetic: boolean;
  ownerAccessErrorMessage: string | null;
  syntheticErrorMessage: string | null;
}) {
  const title = setupRequired ? 'Create owner access' : 'Enter owner passcode';
  const submitLabel = setupRequired ? 'Create owner access' : 'Unlock owner mode';
  const inputLabel = setupRequired ? 'New owner passcode' : 'Owner passcode';
  const placeholder = setupRequired
    ? 'Choose a passcode, 8+ characters'
    : 'Enter the owner passcode';
  const helperText = setupRequired
    ? 'Choose a passcode for the person who can create, delete, and manage every workspace. The app stores a protected hash, not the passcode itself.'
    : 'Owner access unlocks workspace management. Use the passcode chosen during setup, or the passcode configured by the site owner.';

  return (
    <div className="animate-fade-in-up">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--color-primary-400)]">
        Workspace Access
      </p>
      <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
        {title}
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-[rgba(255,255,255,0.45)]">
        {message}
      </p>

      <div className="glass mt-8 max-w-xl rounded-xl p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-primary-400)]">
          Just exploring?
        </p>
        <h3 className="mt-2 text-lg font-semibold text-white">
          Start a demo workspace
        </h3>
        <p className="mt-2 text-sm leading-6 text-[rgba(255,255,255,0.48)]">
          Create a sample workspace with generated customer data. No owner
          passcode or setup is needed.
        </p>
        <button
          type="button"
          onClick={onStartSynthetic}
          disabled={isStartingSynthetic}
          className="btn-primary mt-5 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0"
        >
          {isStartingSynthetic ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Starting demo workspace...
            </>
          ) : (
            <>
              Start Demo Workspace
              <Sparkles className="h-4 w-4" />
            </>
          )}
        </button>
        {syntheticErrorMessage && (
          <p className="mt-3 flex items-center gap-2 text-sm text-[var(--color-danger)]">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {syntheticErrorMessage}
          </p>
        )}
      </div>

      <form
        onSubmit={onSubmit}
        className="glass-elevated mt-5 max-w-xl space-y-4 rounded-xl p-6"
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.48)]">
            Owner mode
          </p>
          <p className="mt-2 text-sm leading-6 text-[rgba(255,255,255,0.48)]">
            {helperText}
          </p>
        </div>

        <div>
          <label
            htmlFor="workspace-admin-token"
            className="block text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.48)]"
          >
            {inputLabel}
          </label>
          <input
            id="workspace-admin-token"
            type="password"
            value={token}
            onChange={(event) => onChangeToken(event.target.value)}
            autoComplete="off"
            placeholder={placeholder}
            className="glass-input mt-2 w-full px-4 py-2.5 text-sm disabled:opacity-50"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={!token.trim() || isSavingOwnerAccess}
            className="btn-primary disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0"
          >
            {isSavingOwnerAccess ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            {submitLabel}
          </button>
          <button
            type="button"
            onClick={onClear}
            className="btn-secondary"
          >
            Clear saved passcode
          </button>
        </div>

        <p className="text-xs leading-5 text-[rgba(255,255,255,0.40)]">
          The passcode is stored only in this browser after you enter it. For
          advanced private deployments, the site owner can pre-set{' '}
          <span className="font-mono">ADMIN_API_TOKEN</span> instead of using
          first-run setup.
        </p>
        {mode === 'deployment_token' && (
          <p className="text-xs leading-5 text-[rgba(255,255,255,0.40)]">
            This deployment already has owner access configured by the site
            owner.
          </p>
        )}
        {ownerAccessErrorMessage && (
          <p className="flex items-center gap-2 text-sm text-[var(--color-danger)]">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {ownerAccessErrorMessage}
          </p>
        )}
      </form>
    </div>
  );
}
