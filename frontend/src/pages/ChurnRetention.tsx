import { TrendingDown } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import EmptyState from '../components/shared/EmptyState';

export default function ChurnRetention() {
  return (
    <div>
      <PageHeader
        title="Churn & Retention Center"
        description="Predict, prevent, and analyze customer churn"
      />
      <EmptyState
        icon={TrendingDown}
        title="Churn predictions"
        description="Risk tier distribution, top churn drivers, and per-customer risk scores will appear here once the churn agent has been run."
      />
    </div>
  );
}
