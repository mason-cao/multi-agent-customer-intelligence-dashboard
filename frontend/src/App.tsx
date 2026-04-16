import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WorkspaceProvider } from './contexts/WorkspaceContext';
import Layout from './components/layout/Layout';
import LoadingSpinner from './components/shared/LoadingSpinner';

const WorkspaceHub = lazy(() => import('./pages/WorkspaceHub'));
const Overview = lazy(() => import('./pages/Overview'));
const Customer360 = lazy(() => import('./pages/Customer360'));
const Segments = lazy(() => import('./pages/Segments'));
const ChurnRetention = lazy(() => import('./pages/ChurnRetention'));
const SentimentSupport = lazy(() => import('./pages/SentimentSupport'));
const Recommendations = lazy(() => import('./pages/Recommendations'));
const AgentAudit = lazy(() => import('./pages/AgentAudit'));
const AskAnything = lazy(() => import('./pages/AskAnything'));
const NotFound = lazy(() => import('./pages/NotFound'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-app-gradient">
      <LoadingSpinner />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <WorkspaceProvider>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              <Route path="/workspaces" element={<WorkspaceHub />} />
              <Route element={<Layout />}>
                <Route path="/" element={<Overview />} />
                <Route path="/customers" element={<Customer360 />} />
                <Route path="/customers/:id" element={<Customer360 />} />
                <Route path="/segments" element={<Segments />} />
                <Route path="/churn" element={<ChurnRetention />} />
                <Route path="/sentiment" element={<SentimentSupport />} />
                <Route path="/recommendations" element={<Recommendations />} />
                <Route path="/agents" element={<AgentAudit />} />
                <Route path="/ask" element={<AskAnything />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </WorkspaceProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
