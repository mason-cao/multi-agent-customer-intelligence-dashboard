/**
 * Single source of truth for the categorical and semantic colors used across
 * the dashboard UI and charts. These hex values are mirrored by CSS tokens in
 * `index.css` (the `@theme` block: `--color-*` and `--color-chart-*`). Keep the
 * two in sync — when a value changes here, change the matching CSS token too.
 *
 * Tuned for the deep, indigo-tinted background (#030712 → #110d25): cool,
 * identity-forward accents, with warm semantic colors reserved for meaning.
 */

/** Core palette. Brand accents are cool; semantic colors carry meaning only. */
export const PALETTE = {
  // Brand accents
  indigo: '#818cf8',
  violet: '#a78bfa',
  cyan: '#22d3ee',
  blue: '#60a5fa',
  purple: '#c084fc',
  // Semantic
  success: '#34d399',
  successSoft: '#6ee7b7',
  warning: '#fbbf24',
  warningStrong: '#fb923c', // escalation step, e.g. churn-risk "high"
  danger: '#f87171',
  dangerSoft: '#fca5a5',
  muted: '#94a3b8',
} as const;

/**
 * Ordered categorical palette for chart series (1..n). Cool, brand-forward hues
 * lead; warm semantic tones provide separation. Mirrors `--color-chart-*`.
 */
export const CATEGORICAL: string[] = [
  PALETTE.indigo,
  PALETTE.success,
  PALETTE.cyan,
  PALETTE.warning,
  PALETTE.violet,
  PALETTE.blue,
  PALETTE.danger,
  PALETTE.purple,
];

/** Customer-value segments. */
export const SEGMENT_COLORS: Record<string, string> = {
  Champions: PALETTE.success,
  'Loyal Customers': PALETTE.blue,
  'At Risk': PALETTE.warning,
  Dormant: PALETTE.muted,
  'Growth Potential': PALETTE.violet,
};

/** Churn-risk tiers — a deliberate green → amber → orange → red escalation. */
export const RISK_COLORS: Record<string, string> = {
  low: PALETTE.success,
  medium: PALETTE.warning,
  high: PALETTE.warningStrong,
  critical: PALETTE.danger,
};

/** Sentiment ramp — derived from success/danger so "positive" reads as success. */
export const SENTIMENT_COLORS: Record<string, string> = {
  very_positive: PALETTE.success,
  positive: PALETTE.successSoft,
  neutral: PALETTE.muted,
  negative: PALETTE.dangerSoft,
  very_negative: PALETTE.danger,
};
