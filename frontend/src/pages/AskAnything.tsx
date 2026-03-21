import { Sparkles } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import EmptyState from '../components/shared/EmptyState';

export default function AskAnything() {
  return (
    <div>
      <PageHeader
        title="Ask Anything"
        description="Natural language queries powered by AI agents"
      />
      <EmptyState
        icon={Sparkles}
        title="Natural language queries"
        description="Ask questions about your customers in plain English. The AI query agent will translate your question into data lookups and return insights."
      />
    </div>
  );
}
