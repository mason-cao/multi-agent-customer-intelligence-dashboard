import { PieChart } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import EmptyState from '../components/shared/EmptyState';

export default function Segments() {
  return (
    <div>
      <PageHeader
        title="Segment Intelligence"
        description="Understand and compare customer segments"
      />
      <EmptyState
        icon={PieChart}
        title="Segment analysis"
        description="Customer segment distribution, characteristics, and cross-segment comparisons will appear here once the segmentation agent has been run."
      />
    </div>
  );
}
