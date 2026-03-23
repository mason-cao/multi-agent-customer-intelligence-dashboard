import { Outlet, useLocation, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import ErrorBoundary from '../ErrorBoundary';
import { useActiveWorkspace } from '../../contexts/WorkspaceContext';

export default function Layout() {
  const location = useLocation();
  const { activeWorkspace, isLoading } = useActiveWorkspace();

  // Show loading while rehydrating workspace from localStorage
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-slate-200 border-t-emerald-600" />
      </div>
    );
  }

  // Redirect to workspace hub if no active ready workspace
  if (!activeWorkspace || activeWorkspace.status !== 'ready') {
    return <Navigate to="/workspaces" replace />;
  }

  return (
    <div className="flex h-screen bg-slate-50">
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
  );
}
