import { LayoutDashboard, LogOut } from 'lucide-react';
import { useWorkspaceHub } from '../hooks/useWorkspaceHub';
import CreateView from '../components/workspaces/CreateView';
import AdminAccessPanel from '../components/workspaces/AdminAccessPanel';
import ListView from '../components/workspaces/ListView';
import DeleteWorkspaceDialog from '../components/workspaces/DeleteWorkspaceDialog';

export default function WorkspaceHub() {
  const hub = useWorkspaceHub();
  return (
    <div className="bg-app-gradient relative min-h-screen">

      <div className="bg-orbs">
        <div className="bg-orb bg-orb--1" />
        <div className="bg-orb bg-orb--2" />
        <div className="bg-orb bg-orb--3" />
        <div className="bg-orb bg-orb--4" />
        <div className="bg-orb bg-orb--5" />
        <div className="bg-orb bg-orb--6" />
      </div>
      <div className="bg-vignette" />

      <header className="glass-surface relative z-10 border-b border-[rgba(255,255,255,0.06)]">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
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
          {hub.showLogout && (
            <button
              type="button"
              onClick={hub.handleLogout}
              className="btn-secondary py-1.5 px-3 text-xs"
            >
              <LogOut className="h-3.5 w-3.5" />
              Log out
            </button>
          )}
        </div>
      </header>

      <div className="relative z-10 mx-auto max-w-5xl px-6 py-12">
        {hub.view === 'create' ? (
          <CreateView {...hub.createProps} />
        ) : hub.adminAccessMessage ? (
          <AdminAccessPanel {...hub.adminProps} />
        ) : (
          <ListView {...hub.listProps} />
        )}
      </div>

      {hub.deleteTarget && <DeleteWorkspaceDialog workspace={hub.deleteTarget} {...hub.deleteProps} />}
    </div>
  );
}
