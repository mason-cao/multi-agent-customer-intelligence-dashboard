import { useState } from 'react';
import { Outlet, useLocation, Navigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import Sidebar from './Sidebar';
import Header from './Header';
import ErrorBoundary from '../ErrorBoundary';
import GenerationView from '../../pages/GenerationView';
import { useActiveWorkspace } from '../../contexts/workspaceContextValue';

function DegradedBanner({ warnings }: { warnings: string | null }) {
  const items = (warnings ?? '').split('\n').filter(Boolean);
  return (
    <div className="mb-6 rounded-lg border border-warning/25 bg-warning/10 px-4 py-3">
      <div className="flex items-center gap-2 text-[var(--color-warning)]">
        <AlertTriangle className="h-4 w-4" />
        <span className="text-xs font-semibold uppercase tracking-wide">
          Some insights are limited
        </span>
      </div>
      <p className="mt-1 text-xs text-[rgba(255,255,255,0.6)]">
        This workspace finished, but one or more non-critical agents had issues.
        Affected sections may be incomplete.
        {items.length > 0 && ` (${items.join('; ')})`}
      </p>
    </div>
  );
}

function BackgroundSystem() {
  return (
    <>
      <div className="bg-orbs">
        <div className="bg-orb bg-orb--1" />
        <div className="bg-orb bg-orb--2" />
        <div className="bg-orb bg-orb--3" />
        <div className="bg-orb bg-orb--4" />
        <div className="bg-orb bg-orb--5" />
        <div className="bg-orb bg-orb--6" />
      </div>
      <div className="bg-vignette" />
    </>
  );
}

export default function Layout() {
  const location = useLocation();
  const { activeWorkspace, isLoading } = useActiveWorkspace();

  // Track whether we were in the generation flow so the completion
  // celebration screen can play before switching to the dashboard.
  // Updated during render (React allows storing information from previous
  // renders this way, which avoids the set-state-in-effect anti-pattern).
  const [wasGenerating, setWasGenerating] = useState(false);
  if (activeWorkspace?.status === 'generating' && !wasGenerating) {
    setWasGenerating(true);
  }
  if (
    wasGenerating &&
    activeWorkspace?.status === 'ready' &&
    location.pathname !== '/'
  ) {
    setWasGenerating(false);
  }

  // Show spinner while workspace data is loading from persisted context.
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-app-gradient">
        <BackgroundSystem />
        <div className="relative z-10 h-8 w-8 animate-spin rounded-full border-[3px] border-[rgba(255,255,255,0.10)] border-t-[var(--color-primary-400)]" />
      </div>
    );
  }

  if (!activeWorkspace) {
    return <Navigate to="/workspaces" replace />;
  }

  // Show GenerationView for generating, failed, or the ready→celebration transition
  const showGeneration =
    activeWorkspace.status === 'generating' ||
    activeWorkspace.status === 'failed' ||
    (activeWorkspace.status === 'ready' && wasGenerating);
  const dashboardPageKey = [
    location.pathname,
    activeWorkspace.id,
    activeWorkspace.completed_at ?? activeWorkspace.status,
  ].join(':');

  return (
    <div className="relative flex h-screen bg-app-gradient">
      <BackgroundSystem />
      <div className="relative z-10 flex h-screen w-full">
        <Sidebar disabled={showGeneration} />
        <div className="flex flex-1 flex-col overflow-hidden">
          {!showGeneration && <Header />}
          <main className="flex-1 overflow-y-auto p-8">
            {showGeneration ? (
              <GenerationView workspace={activeWorkspace} onComplete={() => setWasGenerating(false)} />
            ) : activeWorkspace.status === 'ready' ? (
              <ErrorBoundary key={dashboardPageKey}>
                <div key={dashboardPageKey} className="page-transition">
                  {activeWorkspace.health === 'degraded' && (
                    <DegradedBanner warnings={activeWorkspace.pipeline_warnings} />
                  )}
                  <Outlet />
                </div>
              </ErrorBoundary>
            ) : (
              <Navigate to="/workspaces" replace />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
