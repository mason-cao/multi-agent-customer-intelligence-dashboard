import { useState, useRef, useEffect } from 'react';
import type { AxiosError } from 'axios';
import {
  Sparkles,
  Send,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Database,
  Trash2,
} from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import { useAskQuestion } from '../api/hooks';
import type { QueryResult } from '../types';

const SUGGESTED_PROMPTS = [
  'Which segment has the highest churn risk?',
  'Show the top 10 highest-risk customers.',
  'What actions are most common?',
  'How does sentiment vary by segment?',
];

interface Message {
  role: 'user' | 'ai';
  content: string;
  result?: QueryResult;
  tone?: 'default' | 'error';
}

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

function getQueryErrorMessage(error: Error): string {
  const axiosError = error as AxiosError<ApiErrorBody>;
  const detail = axiosError.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    const message = detail.find((item) => typeof item.msg === 'string')?.msg;
    if (message) return message;
  }

  if (axiosError.response?.status === 404) {
    return 'This workspace data is no longer available. Return to Workspaces and choose an active workspace.';
  }

  return 'I could not complete that query. Check that the workspace data is ready and try again.';
}

export default function AskAnything() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const { mutate, isPending } = useAskQuestion();
  const threadEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isPending]);

  function handleSubmit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || isPending) return;

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setQuestion('');

    mutate(trimmed, {
      onSuccess: (result) => {
        setMessages((prev) => [
          ...prev,
          { role: 'ai', content: result.answer_text, result },
        ]);
      },
      onError: (error) => {
        setMessages((prev) => [
          ...prev,
          {
            role: 'ai',
            content: getQueryErrorMessage(error),
            tone: 'error',
          },
        ]);
      },
    });
  }

  function clearThread() {
    setMessages([]);
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <PageHeader
          title="Ask Anything"
          description="AI-powered intelligence queries"
        />
        {hasMessages && (
          <button
            onClick={clearThread}
            className="flex items-center gap-1.5 text-xs text-[rgba(255,255,255,0.35)] transition hover:text-[rgba(255,255,255,0.6)]"
          >
            <Trash2 className="h-3 w-3" />
            Clear thread
          </button>
        )}
      </div>

      {/* Conversation thread */}
      <div className="flex-1 overflow-y-auto pb-4">
        {!hasMessages && !isPending ? (
          // Empty state with sparkles
          <div className="flex flex-col items-center justify-center py-20">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[rgba(129,140,248,0.08)] ring-1 ring-[rgba(129,140,248,0.12)]">
              <Sparkles className="h-7 w-7 text-[var(--color-primary-400)]" />
            </div>
            <h3 className="mt-5 text-sm font-semibold text-white">
              Ask a question about your data
            </h3>
            <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-[rgba(255,255,255,0.38)]">
              Query your customer intelligence data using natural language.
              Try one of the suggestions below.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, idx) =>
              msg.role === 'user' ? (
                <UserBubble key={idx} content={msg.content} />
              ) : (
                <AiBubble key={idx} message={msg} />
              )
            )}

            {/* Loading indicator */}
            {isPending && (
              <div className="flex items-start gap-3">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[rgba(129,140,248,0.12)]">
                  <Sparkles className="h-3.5 w-3.5 text-[var(--color-primary-400)]" />
                </div>
                <Card className="max-w-lg">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-[var(--color-primary-400)]" />
                    <span className="text-sm text-[rgba(255,255,255,0.5)]">
                      Thinking...
                    </span>
                  </div>
                </Card>
              </div>
            )}

            <div ref={threadEndRef} />
          </div>
        )}
      </div>

      {/* Input area — pinned at bottom */}
      <div className="mt-auto border-t border-[rgba(255,255,255,0.06)] pt-4">
        {/* Suggested prompts */}
        {!hasMessages && (
          <div className="mb-3 flex flex-wrap gap-2">
            {SUGGESTED_PROMPTS.map((q) => (
              <button
                key={q}
                onClick={() => handleSubmit(q)}
                disabled={isPending}
                className="rounded-full border border-[rgba(255,255,255,0.08)] px-3 py-1.5 text-[11px] text-[rgba(255,255,255,0.40)] transition-all duration-200 hover:border-[rgba(129,140,248,0.30)] hover:bg-[rgba(129,140,248,0.08)] hover:text-[var(--color-primary-400)] disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <Card variant="hero">
          <div className="flex items-center gap-3">
            <Sparkles className="h-5 w-5 shrink-0 text-[var(--color-primary-400)]" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit(question)}
              placeholder="Ask a question about your customers..."
              disabled={isPending}
              className="glass-input flex-1 disabled:opacity-50"
            />
            <button
              onClick={() => handleSubmit(question)}
              disabled={isPending || !question.trim()}
              aria-label="Send question"
              className="btn-primary py-2.5 disabled:opacity-50 disabled:shadow-none disabled:hover:translate-y-0"
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Message bubbles ────────────────────────────────────

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="glass-surface max-w-md rounded-2xl rounded-br-md px-4 py-3">
        <p className="text-sm text-white">{content}</p>
      </div>
    </div>
  );
}

function AiBubble({ message }: { message: Message }) {
  const result = message.result;
  const isError = message.tone === 'error' || result?.query_status === 'error';

  return (
    <div className="flex items-start gap-3">
      {/* AI avatar */}
      <div
        className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full ${
          isError ? 'bg-[rgba(248,113,113,0.12)]' : 'bg-[rgba(129,140,248,0.12)]'
        }`}
      >
        {isError ? (
          <AlertCircle className="h-3.5 w-3.5 text-[var(--color-danger)]" />
        ) : (
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-primary-400)]" />
        )}
      </div>

      <Card
        className={`max-w-xl ${
          isError ? 'border-[rgba(248,113,113,0.20)] bg-[rgba(248,113,113,0.08)]' : ''
        }`}
      >
        {/* Answer */}
        <p
          className={`text-sm leading-relaxed ${
            isError ? 'text-[rgba(254,202,202,0.92)]' : 'text-[rgba(255,255,255,0.7)]'
          }`}
        >
          {message.content}
        </p>

        {/* Metadata footer */}
        {result && (
          <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-[rgba(255,255,255,0.06)] pt-3 text-[10px] text-[rgba(255,255,255,0.35)]">
            {/* Status */}
            <span className="flex items-center gap-1">
              {result.query_status === 'success' ? (
                <CheckCircle className="h-3 w-3 text-[var(--color-success)]" />
              ) : (
                <AlertCircle className="h-3 w-3 text-[var(--color-warning)]" />
              )}
              {result.matched_intent.replace(/_/g, ' ')}
            </span>
            {result.execution_ms != null && (
              <span className="flex items-center gap-1 font-mono">
                <Clock className="h-3 w-3" />
                {result.execution_ms}ms
              </span>
            )}
            {result.source_tables && (
              <span className="flex items-center gap-1">
                <Database className="h-3 w-3" />
                {result.source_tables}
              </span>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
