import { Users } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import EmptyState from '../components/shared/EmptyState';

export default function Customer360() {
  return (
    <div>
      <PageHeader
        title="Customer 360 Explorer"
        description="Deep-dive into individual customer profiles, behavior, and AI analysis"
      />
      <EmptyState
        icon={Users}
        title="Customer profiles"
        description="Individual customer profiles with behavioral features, churn risk, sentiment, and AI-generated insights will appear here once the data pipeline is connected."
      />
    </div>
  );
}
