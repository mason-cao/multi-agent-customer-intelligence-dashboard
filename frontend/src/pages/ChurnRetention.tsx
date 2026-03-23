import { AlertTriangle, BarChart3 } from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import {
  useChurnDistribution,
  useAtRiskCustomers,
  useFeatureImportance,
} from '../api/hooks';
import { RISK_COLORS } from '../utils/colors';
import { formatCurrency } from '../utils/formatters';

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`rounded bg-slate-200 animate-pulse ${className}`} />;
}

export default function ChurnRetention() {
  const { data: distribution, isLoading: distLoading } = useChurnDistribution();
  const { data: atRisk, isLoading: riskLoading } = useAtRiskCustomers(15);
  const { data: features, isLoading: featLoading } = useFeatureImportance();

  const isLoading = distLoading || riskLoading || featLoading;
  const totalCustomers = distribution?.reduce((s, d) => s + d.count, 0) ?? 0;
  const maxImportance = features?.[0]?.importance ?? 1;

  return (
    <div>
      <PageHeader
        title="Churn & Retention Center"
        description="Predict, prevent, and analyze customer churn"
      />

      {isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}><Skeleton className="h-16 w-full" /></Card>
            ))}
          </div>
          <Card><Skeleton className="h-64 w-full" /></Card>
        </div>
      ) : (
        <>
          {/* Risk tier cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {distribution?.map((tier, i) => {
              const pct = totalCustomers > 0
                ? ((tier.count / totalCustomers) * 100).toFixed(1)
                : '0';
              const colorKey = tier.risk_tier.toLowerCase();
              return (
                <Card key={tier.risk_tier} hover className={`animate-fade-in-up stagger-${i + 1}`}>
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: RISK_COLORS[colorKey] ?? '#6b7280' }}
                    />
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      {tier.risk_tier}
                    </p>
                  </div>
                  <p className="mt-2 text-3xl font-bold text-slate-900">
                    {tier.count.toLocaleString()}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {pct}% of customers · {formatCurrency(tier.mrr_at_risk)} MRR
                  </p>
                </Card>
              );
            })}
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
            {/* Top at-risk customers */}
            <Card className="xl:col-span-2">
              <div className="mb-4 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Highest-Risk Customers
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-xs text-slate-400">
                      <th className="pb-2 font-medium">Customer</th>
                      <th className="pb-2 font-medium">Company</th>
                      <th className="pb-2 font-medium text-right">Churn %</th>
                      <th className="pb-2 font-medium text-right">MRR</th>
                      <th className="pb-2 font-medium">Top Driver</th>
                    </tr>
                  </thead>
                  <tbody>
                    {atRisk?.map((c) => (
                      <tr
                        key={c.customer_id}
                        className="border-b border-slate-50 last:border-0"
                      >
                        <td className="py-2.5 font-medium text-slate-700">
                          {c.name}
                        </td>
                        <td className="py-2.5 text-slate-500">{c.company}</td>
                        <td className="py-2.5 text-right">
                          <span
                            className="inline-block rounded-full px-2 py-0.5 text-xs font-semibold text-white"
                            style={{
                              backgroundColor:
                                RISK_COLORS[c.risk_tier.toLowerCase()] ?? '#6b7280',
                            }}
                          >
                            {(c.churn_probability * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-2.5 text-right text-slate-600">
                          {formatCurrency(c.mrr)}
                        </td>
                        <td className="py-2.5 text-xs text-slate-500">
                          {c.top_risk_factor}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Feature importance */}
            <Card>
              <div className="mb-4 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-emerald-600" />
                <h3 className="text-sm font-semibold text-slate-700">
                  Top Churn Drivers
                </h3>
              </div>
              <div className="space-y-3">
                {features?.slice(0, 8).map((f) => {
                  const widthPct = maxImportance > 0
                    ? (f.importance / maxImportance) * 100
                    : 0;
                  return (
                    <div key={f.feature}>
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-600 capitalize">
                          {f.feature}
                        </span>
                        <span className="text-slate-400">
                          {f.importance.toFixed(3)}
                        </span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-100">
                        <div
                          className="h-2 rounded-full bg-emerald-500 transition-all"
                          style={{ width: `${widthPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
