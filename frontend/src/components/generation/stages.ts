import { Users, CreditCard, ShoppingCart, Activity, MessageSquare, Star, Megaphone, BarChart3, PieChart, Heart, TrendingDown, Lightbulb, FileText, Shield, Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface StageMeta {
  icon: LucideIcon;
  label: string;
  description: string;
  group: 'data' | 'analysis';
}

export const STAGE_ORDER: string[] = [
  'Initializing workspace',
  'Customers',
  'Subscriptions',
  'Orders',
  'Events',
  'Tickets',
  'Feedback',
  'Campaigns',
  'Running BehaviorAgent',
  'Running SegmentationAgent',
  'Running SentimentAgent',
  'Running ChurnAgent',
  'Running RecommendationAgent',
  'Running NarrativeAgent',
  'Finalizing workspace',
];

export const STAGE_META: Record<string, StageMeta> = {
  'Initializing workspace': {
    icon: Loader2,
    label: 'Initializing',
    description: 'Preparing workspace environment and database',
    group: 'data',
  },
  Customers: {
    icon: Users,
    label: 'Customers',
    description: 'Generating synthetic customer profiles with demographics and account details',
    group: 'data',
  },
  Subscriptions: {
    icon: CreditCard,
    label: 'Subscriptions',
    description: 'Creating subscription plans, billing histories, and renewal patterns',
    group: 'data',
  },
  Orders: {
    icon: ShoppingCart,
    label: 'Orders',
    description: 'Building purchase transaction records across product categories',
    group: 'data',
  },
  Events: {
    icon: Activity,
    label: 'Events',
    description: 'Simulating behavioral event streams and interaction logs',
    group: 'data',
  },
  Tickets: {
    icon: MessageSquare,
    label: 'Tickets',
    description: 'Generating support ticket histories with resolution data',
    group: 'data',
  },
  Feedback: {
    icon: Star,
    label: 'Feedback',
    description: 'Creating customer satisfaction surveys and feedback responses',
    group: 'data',
  },
  Campaigns: {
    icon: Megaphone,
    label: 'Campaigns',
    description: 'Setting up marketing campaign configurations and targeting rules',
    group: 'data',
  },
  'Running BehaviorAgent': {
    icon: BarChart3,
    label: 'Behavior Analysis',
    description: 'Analyzing purchase patterns and engagement signals to build behavioral profiles',
    group: 'analysis',
  },
  'Running SegmentationAgent': {
    icon: PieChart,
    label: 'Segmentation',
    description: 'Clustering customers into behavioral segments using engagement and value metrics',
    group: 'analysis',
  },
  'Running SentimentAgent': {
    icon: Heart,
    label: 'Sentiment Scoring',
    description: 'Scoring feedback and ticket sentiment to gauge customer satisfaction',
    group: 'analysis',
  },
  'Running ChurnAgent': {
    icon: TrendingDown,
    label: 'Churn Prediction',
    description: 'Training ML model to predict churn risk with explainable factors',
    group: 'analysis',
  },
  'Running RecommendationAgent': {
    icon: Lightbulb,
    label: 'Recommendations',
    description: 'Generating prioritized action plans for each customer segment',
    group: 'analysis',
  },
  'Running NarrativeAgent': {
    icon: FileText,
    label: 'Executive Narrative',
    description: 'Writing executive summary with highlights and concerns',
    group: 'analysis',
  },
  'Finalizing workspace': {
    icon: Shield,
    label: 'Quality Audit',
    description: 'Running validation checks and indexing query capabilities',
    group: 'analysis',
  },
};

export function getStageMeta(stageName: string): StageMeta {
  return (
    STAGE_META[stageName] ?? {
      icon: Loader2,
      label: stageName,
      description: 'Processing...',
      group: 'data' as const,
    }
  );
}
