import { useEffect } from 'react';
import { Loader2, AlertTriangle, Trash2 } from 'lucide-react';
import type { Workspace } from '../../types/workspace';

export default function DeleteWorkspaceDialog({workspace, isDeleting, errorMessage, onCancel, onDelete}: {
  workspace: Workspace; isDeleting: boolean; errorMessage: string | null;
  onCancel: () => void; onDelete: () => void;
}) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isDeleting) onCancel();
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isDeleting, onCancel]);
  return (
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
                    {workspace.company_name}
                  </span>
                  ? This will permanently remove all generated data.
                </p>
              </div>
            </div>
            {errorMessage && (
              <p className="mt-3 flex items-center gap-2 text-sm text-[var(--color-danger)]">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                {errorMessage}
              </p>
            )}
            <div className="mt-5 flex gap-3">
              <button
                type="button"
                autoFocus
                onClick={onCancel}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                type="button"
                aria-label={`Confirm deleting ${workspace.company_name}`}
                onClick={onDelete}
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
  );
}
