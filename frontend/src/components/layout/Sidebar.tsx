import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  PieChart,
  TrendingDown,
  MessageCircle,
  Lightbulb,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

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

export default function Sidebar() {
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

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-3 pt-4">
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
