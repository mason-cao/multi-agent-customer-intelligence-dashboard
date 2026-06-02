import { useNavigate } from 'react-router-dom';
import { Activity } from 'lucide-react';
import { useActiveWorkspace } from '../../contexts/workspaceContextValue';
import Badge from '../shared/Badge';

export default function Header() {
  const navigate = useNavigate();
  const { activeWorkspace, clearWorkspace } = useActiveWorkspace();

  return (
    <header className="glass-surface flex h-14 items-center justify-between border-b border-white/[0.06] px-8">
      <div>
        <h1 className="text-sm font-semibold text-white">
          {activeWorkspace?.company_name || 'Customer Intelligence Dashboard'}
        </h1>
        {activeWorkspace && (
          <p className="text-[11px] text-[var(--color-text-tertiary)]">
            {activeWorkspace.industry} &middot;{' '}
            <span className="font-mono">{activeWorkspace.customer_count.toLocaleString()}</span> customers
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Badge tone="success" icon={Activity} label="Online" size="md" />
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
