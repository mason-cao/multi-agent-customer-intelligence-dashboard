import { useNavigate } from 'react-router-dom';
import { Activity } from 'lucide-react';
import { useActiveWorkspace } from '../../contexts/WorkspaceContext';

export default function Header() {
  const navigate = useNavigate();
  const { activeWorkspace, clearWorkspace } = useActiveWorkspace();

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-8">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">
          {activeWorkspace?.company_name || 'Customer Intelligence Dashboard'}
        </h1>
        {activeWorkspace && (
          <p className="text-xs text-slate-400">
            {activeWorkspace.industry} &middot;{' '}
            {activeWorkspace.customer_count.toLocaleString()} customers
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700">
          <Activity className="h-3.5 w-3.5" />
          System Healthy
        </span>
        <button
          onClick={() => {
            clearWorkspace();
            navigate('/workspaces');
          }}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-50 hover:text-slate-700"
        >
          Workspaces
        </button>
      </div>
    </header>
  );
}
