import PageHeader from '../components/shared/PageHeader';

export default function AskAnything() {
  return (
    <div>
      <PageHeader
        title="Ask Anything"
        description="Natural language queries powered by AI agents"
      />
      <div className="rounded-lg border border-gray-200 bg-white p-6 mt-6 text-sm text-gray-500">
        Coming soon — data pipeline integration pending.
      </div>
    </div>
  );
}
