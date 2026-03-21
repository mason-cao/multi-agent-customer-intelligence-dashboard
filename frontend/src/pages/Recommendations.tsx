import { Lightbulb } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import EmptyState from '../components/shared/EmptyState';

export default function Recommendations() {
  return (
    <div>
      <PageHeader
        title="Recommendation Center"
        description="AI-generated actionable recommendations for each segment and customer"
      />
      <EmptyState
        icon={Lightbulb}
        title="Recommendations"
        description="Personalized, AI-generated recommendations for retention, upsell, and engagement will appear here once the recommendation agent has been run."
      />
    </div>
  );
}
