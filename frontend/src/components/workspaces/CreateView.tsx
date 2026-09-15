import { useId } from 'react';
import { ArrowRight, Loader2, AlertTriangle, CheckCircle2, ChevronLeft, Sliders, Sparkles } from 'lucide-react';
import type { Scenario } from '../../types/workspace';
import ScenarioCard from './ScenarioCard';

const INDUSTRIES = [
  'Technology', 'Healthcare', 'Finance', 'Retail',
  'Manufacturing', 'Education', 'Media', 'Logistics',
];

export default function CreateView({
  scenarios,
  selectedScenario,
  workspaceName,
  isSubmitting,
  errorMessage,
  customCount,
  customChurn,
  customIndustry,
  customOutage,
  customDescription,
  onSelectScenario,
  onChangeName,
  onChangeCount,
  onChangeChurn,
  onChangeIndustry,
  onChangeOutage,
  onChangeDescription,
  onCreate,
  onRandomCreate,
  onBack,
}: {
  scenarios: Scenario[];
  selectedScenario: string | null;
  workspaceName: string;
  isSubmitting: boolean;
  errorMessage: string | null;
  customCount: number;
  customChurn: number;
  customIndustry: string;
  customOutage: boolean;
  customDescription: string;
  onSelectScenario: (key: string) => void;
  onChangeName: (name: string) => void;
  onChangeCount: (n: number) => void;
  onChangeChurn: (n: number) => void;
  onChangeIndustry: (s: string) => void;
  onChangeOutage: (b: boolean) => void;
  onChangeDescription: (s: string) => void;
  onCreate: () => void;
  onRandomCreate: () => void;
  onBack: () => void;
}) {
  const isCustom = selectedScenario === 'custom';
  const customNameId = useId();
  const customCountId = useId();
  const customChurnId = useId();
  const customIndustryId = useId();
  const outageLabelId = useId();
  const outageDescriptionId = useId();
  const customDescriptionId = useId();
  const workspaceNameId = useId();

  return (
    <div className="animate-fade-in-up">

      <button
        type="button"
        onClick={onBack}
        className="mb-8 flex items-center gap-1.5 text-sm font-medium text-[rgba(255,255,255,0.5)] transition hover:text-white"
      >
        <ChevronLeft className="h-4 w-4" />
        Back to workspaces
      </button>

      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--color-primary-400)]">
        New Workspace
      </p>
      <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
        Choose a Company Profile
      </h2>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-[rgba(255,255,255,0.40)]">
        Each scenario generates realistic synthetic data with different industry
        dynamics, customer behavior patterns, and business challenges.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {scenarios.map((scenario, i) => (
          <ScenarioCard
            key={scenario.key}
            scenario={scenario}
            index={i}
            isSelected={selectedScenario === scenario.key}
            onSelect={() => onSelectScenario(scenario.key)}
          />
        ))}

        <button
          type="button"
          aria-pressed={isCustom}
          onClick={() => onSelectScenario('custom')}
          className={`animate-fade-in-up stagger-${scenarios.length + 1} glass glass-hover group rounded-xl border p-6 text-left transition-all duration-300 ${
            isCustom
              ? 'border-[var(--color-primary-400)] shadow-[0_0_20px_rgba(129,140,248,0.12),inset_0_0_0_1px_rgba(129,140,248,0.10)]'
              : 'border-[rgba(255,255,255,0.08)] hover:-translate-y-0.5'
          }`}
        >
          <div className="flex items-start gap-3">
            <div
              className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg transition-colors ${
                isCustom ? 'bg-primary-400/15' : 'bg-[rgba(255,255,255,0.04)] ring-1 ring-[rgba(255,255,255,0.08)] group-hover:bg-[rgba(255,255,255,0.08)]'
              }`}
            >
              <Sliders
                className={`h-5 w-5 transition-colors ${isCustom ? 'text-[var(--color-primary-400)]' : 'text-[rgba(255,255,255,0.40)] group-hover:text-[rgba(255,255,255,0.60)]'}`}
              />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-white">
                Build Your Own
              </h3>
              <p className="mt-0.5 text-xs text-[rgba(255,255,255,0.38)]">
                Custom configuration
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-[rgba(255,255,255,0.45)]">
                Configure customer count, churn rate, industry, and more to
                create a tailored scenario for your analysis.
              </p>
            </div>
          </div>
          {isCustom && (
            <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[var(--color-primary-400)]">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Selected
            </div>
          )}
        </button>

        <button
          type="button"
          onClick={onRandomCreate}
          disabled={isSubmitting}
          className={`animate-fade-in-up stagger-${scenarios.length + 2} glass glass-hover group rounded-xl border border-[rgba(255,255,255,0.08)] p-6 text-left transition-all duration-300 hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0`}
        >
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-accent-cyan/10 ring-1 ring-accent-cyan/15 transition-colors group-hover:bg-accent-cyan/15">
              <Sparkles className="h-5 w-5 text-accent-cyan" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-white">
                Surprise Me
              </h3>
              <p className="mt-0.5 text-xs text-[rgba(255,255,255,0.38)]">
                Random company
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-[rgba(255,255,255,0.45)]">
                Generate a random company with varied size, industry, churn
                profile, and business story.
              </p>
            </div>
          </div>
        </button>
      </div>

      {isCustom && (
        <div className="glass mt-8 animate-fade-in space-y-5 p-6">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-primary-400)]">
            Custom Configuration
          </h3>

          <div>
            <label htmlFor={customNameId} className="block text-xs font-medium text-[rgba(255,255,255,0.7)]">
              Company Name
            </label>
            <input
              id={customNameId}
              type="text"
              value={workspaceName}
              onChange={(e) => onChangeName(e.target.value)}
              placeholder="My Company"
              className="glass-input mt-1.5 w-full max-w-md px-4 py-2.5 text-sm"
            />
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label htmlFor={customCountId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Customer Count
              </label>
              <span className="font-mono text-xs font-semibold text-[var(--color-primary-400)]">
                {customCount.toLocaleString()}
              </span>
            </div>
            <input
              id={customCountId}
              type="range"
              min={100}
              max={10000}
              step={100}
              value={customCount}
              onChange={(e) => onChangeCount(Number(e.target.value))}
              className="mt-2 w-full max-w-md"
              style={{ accentColor: 'var(--color-primary-400)' }}
            />
            <div className="mt-1 flex max-w-md justify-between font-mono text-[10px] text-[rgba(255,255,255,0.45)]">
              <span>100</span>
              <span>10,000</span>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label htmlFor={customChurnId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Churn Rate
              </label>
              <span className="font-mono text-xs font-semibold text-[var(--color-primary-400)]">
                {Math.round(customChurn * 100)}%
              </span>
            </div>
            <input
              id={customChurnId}
              type="range"
              min={5}
              max={30}
              step={1}
              value={Math.round(customChurn * 100)}
              onChange={(e) => onChangeChurn(Number(e.target.value) / 100)}
              className="mt-2 w-full max-w-md"
              style={{ accentColor: 'var(--color-primary-400)' }}
            />
            <div className="mt-1 flex max-w-md justify-between font-mono text-[10px] text-[rgba(255,255,255,0.45)]">
              <span>5%</span>
              <span>30%</span>
            </div>
          </div>

          <div>
            <label htmlFor={customIndustryId} className="block text-xs font-medium text-[rgba(255,255,255,0.7)]">
              Primary Industry
            </label>
            <select
              id={customIndustryId}
              value={customIndustry}
              onChange={(e) => onChangeIndustry(e.target.value)}
              className="glass-input mt-1.5 w-full max-w-md px-4 py-2.5 text-sm"
            >
              {INDUSTRIES.map((ind) => (
                <option key={ind} value={ind} className="bg-[var(--color-bg-end)] text-white">
                  {ind}
                </option>
              ))}
            </select>
          </div>

          <div className="flex max-w-md items-center justify-between">
            <div>
              <p id={outageLabelId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Include Q3 Service Outage
              </p>
              <p id={outageDescriptionId} className="mt-0.5 text-[11px] text-[rgba(255,255,255,0.45)]">
                Simulates spike in tickets and negative feedback Aug-Sep 2024
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={customOutage}
              aria-labelledby={outageLabelId}
              aria-describedby={outageDescriptionId}
              onClick={() => onChangeOutage(!customOutage)}
              className={`relative h-6 w-11 flex-shrink-0 rounded-full transition-colors ${
                customOutage ? 'bg-[var(--color-primary-400)]' : 'bg-[rgba(255,255,255,0.15)]'
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  customOutage ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label htmlFor={customDescriptionId} className="text-xs font-medium text-[rgba(255,255,255,0.7)]">
                Scenario Description
                <span className="ml-1 font-normal text-[rgba(255,255,255,0.45)]">(optional)</span>
              </label>
              <span className="font-mono text-[10px] text-[rgba(255,255,255,0.45)]">
                {customDescription.length}/500
              </span>
            </div>
            <textarea
              id={customDescriptionId}
              value={customDescription}
              onChange={(e) => {
                if (e.target.value.length <= 500) onChangeDescription(e.target.value);
              }}
              placeholder="Describe the business scenario for this workspace..."
              rows={3}
              className="glass-input mt-1.5 w-full max-w-md px-4 py-2.5 text-sm"
            />
          </div>
        </div>
      )}

      {selectedScenario && !isCustom && (
        <div className="mt-8 animate-fade-in">
          <label htmlFor={workspaceNameId} className="block text-xs font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.45)]">
            Workspace Name
          </label>
          <input
            id={workspaceNameId}
            type="text"
            value={workspaceName}
            onChange={(e) => onChangeName(e.target.value)}
            placeholder="Enter a name for this workspace"
            className="glass-input mt-2 w-full max-w-md px-4 py-2.5 text-sm"
          />
        </div>
      )}

      {errorMessage && (
        <div className="mt-4 rounded-lg border border-danger/30 bg-danger/10 p-3">
          <p className="flex items-center gap-2 text-sm text-[var(--color-danger)]">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            {errorMessage}
          </p>
        </div>
      )}

      <div className="mt-8">
        <button
          type="button"
          onClick={onCreate}
          disabled={!selectedScenario || isSubmitting}
          className="btn-primary disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Creating workspace...
            </>
          ) : (
            <>
              Create & Generate
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
