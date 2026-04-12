import { useState } from 'react';
import { Outlet, useLocation, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import ErrorBoundary from '../ErrorBoundary';
import GenerationView from '../../pages/GenerationView';
import { useActiveWorkspace } from '../../contexts/WorkspaceContext';

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

  // Show spinner while workspace data is loading, or if localStorage says a
  // workspace is active but the context hasn't hydrated it yet (prevents a
  // flash-redirect to /workspaces during the Vercel→Railway proxy round-trip).
  const hasStoredWorkspace = !!localStorage.getItem('luminosity_active_workspace');
  if (isLoading || (!activeWorkspace && hasStoredWorkspace)) {
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
              <ErrorBoundary key={location.pathname}>
                <div key={location.pathname} className="page-transition">
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
