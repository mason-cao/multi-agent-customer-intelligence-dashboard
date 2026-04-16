import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  PieChart,
  TrendingDown,
  MessageCircle,
  Lightbulb,
  ShieldCheck,
  Sparkles,
  Building2,
  ArrowLeftRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useActiveWorkspace } from '../../contexts/workspaceContextValue';

interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon;
}

const navigation: NavItem[] = [
  { name: 'Overview', path: '/', icon: LayoutDashboard },
  { name: 'Customer 360', path: '/customers', icon: Users },
  { name: 'Segments', path: '/segments', icon: PieChart },
  { name: 'Churn & Retention', path: '/churn', icon: TrendingDown },
  { name: 'Sentiment & Support', path: '/sentiment', icon: MessageCircle },
  { name: 'Recommendations', path: '/recommendations', icon: Lightbulb },
  { name: 'Agent Audit', path: '/agents', icon: ShieldCheck },
  { name: 'Ask Anything', path: '/ask', icon: Sparkles },
];

export default function Sidebar({ disabled = false }: { disabled?: boolean }) {
  const { activeWorkspace, clearWorkspace } = useActiveWorkspace();
  const navigate = useNavigate();

  function handleSwitch() {
    clearWorkspace();
    navigate('/workspaces');
  }

  return (
    <aside className="glass-surface flex h-screen w-60 flex-col border-r border-[rgba(255,255,255,0.06)]">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-[rgba(255,255,255,0.06)] px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--color-primary-400)] to-[var(--color-primary-600)] shadow-[0_0_12px_rgba(99,102,241,0.3)]">
          <LayoutDashboard className="h-3.5 w-3.5 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="text-[13px] font-bold tracking-tight text-white">
            Luminosity
          </span>
          <span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-[var(--color-text-accent)]">
            Intelligence
          </span>
        </div>
      </div>

      {/* Workspace indicator */}
      {activeWorkspace && (
        <div className="mx-3 mt-3 mb-1">
          <div className="glass-nested rounded-lg px-3 py-2.5">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-[rgba(129,140,248,0.12)]">
                <Building2 className="h-3.5 w-3.5 text-[var(--color-primary-400)]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[12px] font-semibold text-white">
                  {activeWorkspace.company_name}
                </p>
                <div className="flex items-center gap-1.5">
                  <span className="rounded-full bg-[rgba(129,140,248,0.10)] px-1.5 py-0.5 text-[9px] font-medium capitalize text-[var(--color-text-accent)]">
                    {activeWorkspace.industry}
                  </span>
                  <span className="font-mono text-[9px] text-[rgba(255,255,255,0.30)]">
                    {activeWorkspace.customer_count.toLocaleString()} customers
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={handleSwitch}
              className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-md bg-[rgba(255,255,255,0.04)] py-1.5 text-[10px] font-medium text-[rgba(255,255,255,0.40)] transition-colors hover:bg-[rgba(255,255,255,0.07)] hover:text-[rgba(255,255,255,0.60)]"
            >
              <ArrowLeftRight className="h-3 w-3" />
              Switch workspace
            </button>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className={`flex-1 space-y-0.5 px-3 pt-4 ${disabled ? 'pointer-events-none opacity-30' : ''}`}>
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `group flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-[rgba(129,140,248,0.12)] text-white shadow-[inset_0_0_0_1px_rgba(129,140,248,0.15),0_0_12px_rgba(129,140,248,0.06)]'
                    : 'text-[rgba(255,255,255,0.45)] hover:bg-[rgba(255,255,255,0.05)] hover:text-[rgba(255,255,255,0.80)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={`h-4 w-4 flex-shrink-0 transition-colors duration-200 ${
                      isActive
                        ? 'text-[var(--color-primary-400)]'
                        : 'text-[rgba(255,255,255,0.30)] group-hover:text-[rgba(255,255,255,0.55)]'
                    }`}
                    strokeWidth={isActive ? 2 : 1.5}
                  />
                  {item.name}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-[rgba(255,255,255,0.06)] px-5 py-3">
        <div className="flex items-center gap-2">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-success)] opacity-50" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[var(--color-success)]" />
          </span>
          <p className="text-[10px] font-medium text-[rgba(255,255,255,0.30)]">
            System ready
          </p>
        </div>
      </div>
    </aside>
  );
}
