import { CheckCircle2 } from 'lucide-react';
import type { Scenario } from '../../types/workspace';
import { getMeta } from './scenarioMeta';

export default function ScenarioCard({
  scenario,
  index,
  isSelected,
  onSelect,
}: {
  scenario: Scenario;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const meta = getMeta(scenario.key);
  const Icon = meta.icon;

  return (
    <button
      type="button"
      aria-pressed={isSelected}
      onClick={onSelect}
      className={`animate-fade-in-up stagger-${index + 1} glass glass-hover group rounded-xl border p-6 text-left transition-all duration-300 ${
        isSelected
          ? 'border-[var(--color-primary-400)] shadow-[0_0_20px_rgba(129,140,248,0.12),inset_0_0_0_1px_rgba(129,140,248,0.10)]'
          : 'border-[rgba(255,255,255,0.08)] hover:-translate-y-0.5'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg transition-colors ${
            isSelected ? meta.iconBg : 'bg-[rgba(255,255,255,0.04)] ring-1 ring-[rgba(255,255,255,0.08)] group-hover:bg-[rgba(255,255,255,0.08)]'
          }`}
        >
          <Icon
            className={`h-5 w-5 transition-colors ${isSelected ? meta.accentText : 'text-[rgba(255,255,255,0.40)] group-hover:text-[rgba(255,255,255,0.60)]'}`}
          />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-white">
            {scenario.company_name}
          </h3>
          <p className="mt-0.5 text-xs text-[rgba(255,255,255,0.38)]">
            {scenario.industry} &middot;{' '}
            <span className="font-mono">{scenario.customer_count.toLocaleString()}</span> customers &middot;{' '}
            <span className="font-mono">{Math.round(scenario.churn_rate * 100)}%</span> churn
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-[rgba(255,255,255,0.45)]">
            {scenario.description}
          </p>
        </div>
      </div>
      {isSelected && (
        <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[var(--color-primary-400)]">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Selected
        </div>
      )}
    </button>
  );
}
