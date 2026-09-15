import { Building2, Rocket, BarChart3, Heart, Sliders, Sparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { PALETTE } from '../../utils/colors';

export interface ScenarioMeta {
  icon: LucideIcon;
  accentHex: string;
  iconBg: string;
  accentText: string;
  barGradient: string;
}

const SCENARIO_META: Record<string, ScenarioMeta> = {
  velocity_saas: {
    icon: Rocket,
    accentHex: PALETTE.success,
    iconBg: 'bg-success/15',
    accentText: 'text-success',
    barGradient: 'from-success to-success/30',
  },
  atlas_enterprise: {
    icon: Building2,
    accentHex: PALETTE.blue,
    iconBg: 'bg-info/15',
    accentText: 'text-info',
    barGradient: 'from-info to-info/30',
  },
  beacon_analytics: {
    icon: BarChart3,
    accentHex: PALETTE.warning,
    iconBg: 'bg-warning/15',
    accentText: 'text-warning',
    barGradient: 'from-warning to-warning/30',
  },
  meridian_data: {
    icon: Heart,
    accentHex: PALETTE.violet,
    iconBg: 'bg-accent-violet/15',
    accentText: 'text-accent-violet',
    barGradient: 'from-accent-violet to-accent-violet/30',
  },
  custom: {
    icon: Sliders,
    accentHex: PALETTE.indigo,
    iconBg: 'bg-primary-400/15',
    accentText: 'text-primary-400',
    barGradient: 'from-primary-400 to-primary-400/30',
  },
  random: {
    icon: Sparkles,
    accentHex: PALETTE.cyan,
    iconBg: 'bg-accent-cyan/15',
    accentText: 'text-accent-cyan',
    barGradient: 'from-accent-cyan to-accent-cyan/30',
  },
};

const DEFAULT_META: ScenarioMeta = {
  icon: Building2,
  accentHex: PALETTE.indigo,
  iconBg: 'bg-primary-400/15',
  accentText: 'text-primary-400',
  barGradient: 'from-primary-400 to-primary-400/30',
};

export function getMeta(scenario: string): ScenarioMeta {
  return SCENARIO_META[scenario] || DEFAULT_META;
}
