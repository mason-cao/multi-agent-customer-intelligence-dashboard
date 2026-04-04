import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Users,
  CreditCard,
  ShoppingCart,
  Activity,
  MessageSquare,
  Star,
  Megaphone,
  Brain,
  PieChart,
  Heart,
  TrendingDown,
  Lightbulb,
  FileText,
  Shield,
  CheckCircle2,
  Loader2,
  Sparkles,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Workspace } from '../types/workspace';

// ── Stage metadata ─────────────────────────────────────

interface StageMeta {
  icon: LucideIcon;
  label: string;
  description: string;
  group: 'data' | 'ai';
}

const STAGE_ORDER: string[] = [
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

const STAGE_META: Record<string, StageMeta> = {
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
    icon: Brain,
    label: 'Behavior Analysis',
    description: 'Analyzing purchase patterns and engagement signals to build behavioral profiles',
    group: 'ai',
  },
  'Running SegmentationAgent': {
    icon: PieChart,
    label: 'Segmentation',
    description: 'Clustering customers into behavioral segments using engagement and value metrics',
    group: 'ai',
  },
  'Running SentimentAgent': {
    icon: Heart,
    label: 'Sentiment Scoring',
    description: 'Scoring feedback and ticket sentiment to gauge customer satisfaction',
    group: 'ai',
  },
  'Running ChurnAgent': {
    icon: TrendingDown,
    label: 'Churn Prediction',
    description: 'Training ML model to predict churn risk with explainable factors',
    group: 'ai',
  },
  'Running RecommendationAgent': {
    icon: Lightbulb,
    label: 'Recommendations',
    description: 'Generating prioritized action plans for each customer segment',
    group: 'ai',
  },
  'Running NarrativeAgent': {
    icon: FileText,
    label: 'Executive Narrative',
    description: 'Writing AI-generated executive summary with highlights and concerns',
    group: 'ai',
  },
  'Finalizing workspace': {
    icon: Shield,
    label: 'Quality Audit',
    description: 'Running validation checks and indexing query capabilities',
    group: 'ai',
  },
};

function getStageMeta(stageName: string): StageMeta {
  return (
    STAGE_META[stageName] ?? {
      icon: Loader2,
      label: stageName,
      description: 'Processing...',
      group: 'data' as const,
    }
  );
}

// ── Progress Ring SVG ──────────────────────────────────

function ProgressRing({
  progress,
  isComplete,
}: {
  progress: number;
  isComplete: boolean;
}) {
  const radius = 68;
  const stroke = 6;
  const center = 80;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  const strokeColor = isComplete
    ? 'var(--color-success)'
    : 'var(--color-primary-400)';
  const glowColor = isComplete
    ? 'rgba(52,211,153,0.4)'
    : 'rgba(129,140,248,0.3)';

  return (
    <svg
      width={center * 2}
      height={center * 2}
      className="drop-shadow-lg"
    >
      {/* Glow filter */}
      <defs>
        <filter id="ring-glow">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {/* Background track */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={stroke}
      />
      {/* Progress arc */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={strokeColor}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${center} ${center})`}
        style={{
          transition: 'stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1), stroke 0.4s ease',
          filter: `drop-shadow(0 0 8px ${glowColor})`,
        }}
      />
    </svg>
  );
}

// ── Timeline Stage Row ─────────────────────────────────

function StageRow({
  stageName,
  status,
  isFirst,
}: {
  stageName: string;
  status: 'completed' | 'current' | 'pending';
  isFirst: boolean;
}) {
  const meta = getStageMeta(stageName);
  const Icon = meta.icon;

  return (
    <div
      className={`flex items-center gap-3 py-2 ${isFirst ? '' : ''} ${
        status === 'completed'
          ? 'opacity-60'
          : status === 'pending'
            ? 'opacity-30'
            : ''
      }`}
    >
      {/* Status indicator */}
      <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center">
        {status === 'completed' ? (
          <CheckCircle2 className="h-4 w-4 text-[var(--color-success)]" />
        ) : status === 'current' ? (
          <div className="relative flex h-5 w-5 items-center justify-center">
            <div className="absolute inset-0 animate-ping rounded-full bg-[var(--color-primary-400)] opacity-20" />
            <div className="h-2.5 w-2.5 rounded-full bg-[var(--color-primary-400)] shadow-[0_0_8px_rgba(129,140,248,0.5)]" />
          </div>
        ) : (
          <div className="h-2 w-2 rounded-full bg-[rgba(255,255,255,0.15)]" />
        )}
      </div>

      {/* Icon */}
      <div
        className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md ${
          status === 'current'
            ? 'bg-[rgba(129,140,248,0.12)]'
            : 'bg-[rgba(255,255,255,0.04)]'
        }`}
      >
        <Icon
          className={`h-3.5 w-3.5 ${
            status === 'current'
              ? 'text-[var(--color-primary-400)]'
              : 'text-[rgba(255,255,255,0.5)]'
          } ${status === 'current' && stageName === 'Initializing workspace' ? 'animate-spin' : ''}`}
        />
      </div>

      {/* Label */}
      <span
        className={`text-sm ${
          status === 'current'
            ? 'font-medium text-white'
            : 'text-[rgba(255,255,255,0.70)]'
        }`}
      >
        {meta.label}
      </span>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────

export default function GenerationView({
  workspace,
}: {
  workspace: Workspace;
}) {
  const navigate = useNavigate();
  const [isComplete, setIsComplete] = useState(false);
  const [countdown, setCountdown] = useState(3);
  const startTimeRef = useRef<number>(
    workspace.generation_started_at
      ? new Date(workspace.generation_started_at).getTime()
      : Date.now()
  );
  const [elapsed, setElapsed] = useState(0);

  // Elapsed time counter
  useEffect(() => {
    const start = startTimeRef.current;
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Completion detection
  useEffect(() => {
    if (workspace.status === 'ready' && !isComplete) {
      setIsComplete(true);
    }
  }, [workspace.status, isComplete]);

  // Countdown + redirect after completion
  useEffect(() => {
    if (!isComplete) return;
    if (countdown <= 0) {
      navigate('/');
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [isComplete, countdown, navigate]);

  const stageIndex = workspace.stage_index ?? 0;
  const totalStages = workspace.total_stages ?? 14;
  const progress = isComplete
    ? 100
    : Math.round((stageIndex / totalStages) * 100);
  const currentStage = workspace.current_stage ?? 'Initializing workspace';
  const currentMeta = getStageMeta(currentStage);

  // Determine which index in STAGE_ORDER matches current_stage
  const currentOrderIndex = STAGE_ORDER.indexOf(currentStage);

  const dataStages = STAGE_ORDER.filter(
    (s) => getStageMeta(s).group === 'data'
  );
  const aiStages = STAGE_ORDER.filter(
    (s) => getStageMeta(s).group === 'ai'
  );

  function getStageStatus(
    stageName: string
  ): 'completed' | 'current' | 'pending' {
    if (isComplete) return 'completed';
    const idx = STAGE_ORDER.indexOf(stageName);
    if (idx < currentOrderIndex) return 'completed';
    if (idx === currentOrderIndex) return 'current';
    return 'pending';
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  // ── Failed state ─────────────────────────────────────
  if (workspace.status === 'failed') {
    return (
      <div className="flex min-h-full flex-col items-center justify-center px-8 py-12">
        <div className="w-full max-w-lg text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[rgba(248,113,113,0.1)] ring-1 ring-[rgba(248,113,113,0.2)]">
            <Shield className="h-8 w-8 text-[var(--color-danger)]" />
          </div>
          <h2 className="mt-5 text-xl font-bold text-white">
            Generation Failed
          </h2>
          <p className="mt-2 text-sm text-[rgba(255,255,255,0.5)]">
            {workspace.user_message ||
              'Something went wrong during data generation. You can retry from the workspace list.'}
          </p>
          <button
            onClick={() => navigate('/workspaces')}
            className="btn-primary mt-6"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Workspaces
          </button>
        </div>
      </div>
    );
  }

  // ── Completion celebration ───────────────────────────
  if (isComplete) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center px-8 py-12">
        <div className="w-full max-w-lg text-center">
          {/* Sparkle accents */}
          <div className="relative mx-auto w-fit">
            <Sparkles className="absolute -left-8 -top-4 h-5 w-5 animate-pulse text-[var(--color-primary-400)] opacity-60" />
            <Sparkles className="absolute -right-8 top-0 h-4 w-4 animate-pulse text-[var(--color-success)] opacity-50 [animation-delay:0.3s]" />
            <Sparkles className="absolute -bottom-2 -left-4 h-3 w-3 animate-pulse text-[#a78bfa] opacity-40 [animation-delay:0.6s]" />

            <div className="relative">
              <ProgressRing progress={100} isComplete />
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <CheckCircle2 className="h-10 w-10 text-[var(--color-success)]" />
              </div>
            </div>
          </div>

          <h2 className="mt-6 text-2xl font-bold text-white">
            Your Intelligence Dashboard is Ready
          </h2>
          <p className="mt-2 text-sm text-[rgba(255,255,255,0.5)]">
            {workspace.company_name} &middot;{' '}
            <span className="font-mono">
              {workspace.customer_count.toLocaleString()}
            </span>{' '}
            customers &middot; Generated in {formatTime(elapsed)}
          </p>

          <button
            onClick={() => navigate('/')}
            className="btn-primary mt-6"
          >
            Enter Dashboard
            <Sparkles className="h-4 w-4" />
          </button>

          <p className="mt-3 text-xs text-[rgba(255,255,255,0.3)]">
            Redirecting in {countdown}...
          </p>
        </div>
      </div>
    );
  }

  // ── Generating state ─────────────────────────────────
  return (
    <div className="flex min-h-full flex-col px-8 py-6">
      {/* Top bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/workspaces')}
          className="flex items-center gap-1.5 text-sm text-[rgba(255,255,255,0.5)] transition hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Workspaces
        </button>
        <div className="flex items-center gap-2 text-sm text-[rgba(255,255,255,0.4)]">
          <span className="font-medium text-[rgba(255,255,255,0.7)]">
            {workspace.company_name}
          </span>
          <span>&middot;</span>
          <span>{workspace.industry}</span>
          <span>&middot;</span>
          <span className="font-mono">
            {workspace.customer_count.toLocaleString()}
          </span>
          <span>customers</span>
        </div>
      </div>

      {/* Hero section */}
      <div className="mt-8 flex flex-col items-center">
        <div className="flex items-center gap-8">
          {/* Progress ring */}
          <div className="relative">
            <ProgressRing progress={progress} isComplete={false} />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono text-3xl font-bold text-white">
                {progress}%
              </span>
              <span className="mt-0.5 text-xs text-[rgba(255,255,255,0.4)]">
                {stageIndex} of {totalStages}
              </span>
            </div>
          </div>

          {/* Current stage info */}
          <div className="max-w-sm">
            <div className="flex items-center gap-2">
              <currentMeta.icon className="h-5 w-5 text-[var(--color-primary-400)]" />
              <h2 className="text-lg font-semibold text-white">
                {currentMeta.label}
              </h2>
            </div>
            <p className="mt-1.5 text-sm leading-relaxed text-[rgba(255,255,255,0.5)]">
              {currentMeta.description}
            </p>
            <p className="mt-3 font-mono text-xs text-[rgba(255,255,255,0.3)]">
              Elapsed: {formatTime(elapsed)}
            </p>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="mx-auto mt-10 w-full max-w-lg">
        <div className="glass rounded-xl p-6">
          {/* Data Generation group */}
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[rgba(255,255,255,0.3)]">
            Data Generation
          </p>
          <div className="mt-2">
            {dataStages.map((stage, i) => (
              <StageRow
                key={stage}
                stageName={stage}
                status={getStageStatus(stage)}
                isFirst={i === 0}
              />
            ))}
          </div>

          {/* Divider */}
          <div className="my-3 h-px bg-[rgba(255,255,255,0.06)]" />

          {/* AI Analysis group */}
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[rgba(255,255,255,0.3)]">
            AI Analysis
          </p>
          <div className="mt-2">
            {aiStages.map((stage, i) => (
              <StageRow
                key={stage}
                stageName={stage}
                status={getStageStatus(stage)}
                isFirst={i === 0}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Bottom message */}
      <p className="mt-6 text-center text-xs text-[rgba(255,255,255,0.25)]">
        You'll be redirected to the dashboard when complete
      </p>
    </div>
  );
}
