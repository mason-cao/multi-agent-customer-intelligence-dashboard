import PageHeader from '../components/shared/PageHeader';

export default function Recommendations() {
  return (
    <div>
      <PageHeader
        title="Recommendation Center"
        description="AI-generated actionable recommendations for each segment and customer"
      />
      <div className="rounded-lg border border-gray-200 bg-white p-6 mt-6 text-sm text-gray-500">
        Coming soon — data pipeline integration pending.
      </div>
    </div>
  );
}
