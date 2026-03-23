import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { WorkspaceProvider } from './contexts/WorkspaceContext';
import Layout from './components/layout/Layout';
import WorkspaceHub from './pages/WorkspaceHub';
import Overview from './pages/Overview';
import Customer360 from './pages/Customer360';
import Segments from './pages/Segments';
import ChurnRetention from './pages/ChurnRetention';
import SentimentSupport from './pages/SentimentSupport';
import Recommendations from './pages/Recommendations';
import AgentAudit from './pages/AgentAudit';
import AskAnything from './pages/AskAnything';
import NotFound from './pages/NotFound';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <WorkspaceProvider>
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
        </WorkspaceProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
