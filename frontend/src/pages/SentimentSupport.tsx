import { MessageCircle } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import EmptyState from '../components/shared/EmptyState';

export default function SentimentSupport() {
  return (
    <div>
      <PageHeader
        title="Sentiment & Support Intelligence"
        description="Voice of the customer — sentiment trends, topics, and support analysis"
      />
      <EmptyState
        icon={MessageCircle}
        title="Sentiment analysis"
        description="Sentiment distribution, trend analysis, and support ticket insights will appear here once the sentiment agent has been run."
      />
    </div>
  );
}
