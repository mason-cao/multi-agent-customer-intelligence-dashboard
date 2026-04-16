import { useNavigate } from 'react-router-dom';
import { Activity } from 'lucide-react';
import { useActiveWorkspace } from '../../contexts/workspaceContextValue';

export default function Header() {
  const navigate = useNavigate();
  const { activeWorkspace, clearWorkspace } = useActiveWorkspace();

  return (
    <header className="glass-surface flex h-14 items-center justify-between border-b border-[rgba(255,255,255,0.06)] px-8">
      <div>
        <h1 className="text-sm font-semibold text-white">
          {activeWorkspace?.company_name || 'Customer Intelligence Dashboard'}
        </h1>
        {activeWorkspace && (
          <p className="text-[11px] text-[rgba(255,255,255,0.40)]">
            {activeWorkspace.industry} &middot;{' '}
            <span className="font-mono">{activeWorkspace.customer_count.toLocaleString()}</span> customers
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5 rounded-full border border-[rgba(52,211,153,0.20)] bg-[rgba(52,211,153,0.08)] px-2.5 py-1 text-[11px] font-medium text-[var(--color-success)]">
          <Activity className="h-3 w-3" />
          Online
        </span>
        <button
          onClick={() => {
            clearWorkspace();
            navigate('/workspaces');
          }}
          className="btn-secondary py-1 px-3 text-xs"
        >
          Workspaces
        </button>
      </div>
    </header>
  );
}
