import { Outlet, useLocation, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import ErrorBoundary from '../ErrorBoundary';
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

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-app-gradient">
        <BackgroundSystem />
        <div className="relative z-10 h-8 w-8 animate-spin rounded-full border-[3px] border-[rgba(255,255,255,0.10)] border-t-[var(--color-primary-400)]" />
      </div>
    );
  }

  if (!activeWorkspace || activeWorkspace.status !== 'ready') {
    return <Navigate to="/workspaces" replace />;
  }

  return (
    <div className="relative flex h-screen bg-app-gradient">
      <BackgroundSystem />
      <div className="relative z-10 flex h-screen w-full">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto p-8">
            <ErrorBoundary key={location.pathname}>
              <div className="animate-fade-in-up">
                <Outlet />
              </div>
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </div>
  );
}
