import { useState } from 'react';
import {
  Sparkles,
  Send,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Database,
} from 'lucide-react';
import PageHeader from '../components/shared/PageHeader';
import Card from '../components/shared/Card';
import { useAskQuestion } from '../api/hooks';
import type { QueryResult } from '../types';

const EXAMPLE_QUESTIONS = [
  'Which segment has the highest churn risk?',
  'Show the top 10 highest-risk customers.',
  'What actions are most common?',
  'How does sentiment vary by segment?',
  'What should we prioritize this week?',
  'Are there any audit warnings?',
];

export default function AskAnything() {
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<QueryResult[]>([]);
  const { mutate, isPending } = useAskQuestion();

  function handleSubmit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || isPending) return;

    mutate(trimmed, {
      onSuccess: (result) => {
        setHistory((prev) => [result, ...prev]);
        setQuestion('');
      },
    });
  }

  return (
    <div>
      <PageHeader
        title="Ask Anything"
        description="Natural language queries powered by AI agents"
      />

      {/* Query input */}
      <Card className="mb-6">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 shrink-0 text-emerald-500" />
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit(question)}
            placeholder="Ask a question about your customers..."
            disabled={isPending}
            className="flex-1 rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:border-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-100 disabled:opacity-50"
          />
          <button
            onClick={() => handleSubmit(question)}
            disabled={isPending || !question.trim()}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-emerald-700 active:scale-[0.98] disabled:opacity-50"
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Ask
          </button>
        </div>

        {/* Example questions */}
        {history.length === 0 && (
          <div className="mt-4">
            <p className="mb-2 text-[11px] font-medium text-slate-400">
              Try one of these:
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setQuestion(q);
                    handleSubmit(q);
                  }}
                  disabled={isPending}
                  className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] text-slate-500 transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Results */}
      {history.length > 0 && (
        <div className="space-y-4">
          {history.map((result, idx) => (
            <Card
              key={result.query_id || idx}
              className={idx === 0 ? 'border-emerald-100 bg-emerald-50/30' : ''}
            >
              <div className="mb-3 flex items-start justify-between gap-4">
                <p className="text-sm font-medium text-slate-700">
                  {result.original_question}
                </p>
                <div className="flex shrink-0 items-center gap-1.5">
                  {result.query_status === 'success' ? (
                    <CheckCircle className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                  )}
                  <span
                    className={`text-[10px] font-semibold uppercase ${
                      result.query_status === 'success'
                        ? 'text-emerald-600'
                        : 'text-amber-600'
                    }`}
                  >
                    {result.query_status}
                  </span>
                </div>
              </div>

              <p className="text-sm leading-relaxed text-slate-600">
                {result.answer_text}
              </p>

              {/* Metadata footer */}
              <div className="mt-3 flex items-center gap-4 border-t border-slate-100 pt-3 text-[10px] text-slate-400">
                <span className="flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  {result.matched_intent.replace(/_/g, ' ')}
                </span>
                {result.execution_ms != null && (
                  <span className="flex items-center gap-1">
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
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
