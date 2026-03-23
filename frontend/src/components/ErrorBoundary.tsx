import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full items-center justify-center p-8">
          <div className="max-w-sm text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50">
              <AlertTriangle className="h-7 w-7 text-red-500" strokeWidth={1.5} />
            </div>
            <h2 className="mt-5 text-sm font-semibold text-slate-700">
              Something went wrong
            </h2>
            <p className="mt-1.5 text-[13px] leading-relaxed text-slate-400">
              This page encountered an unexpected error. Try navigating back or
              returning to the workspace hub.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                onClick={() => this.setState({ hasError: false })}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
              >
                Try Again
              </button>
              <a
                href="/workspaces"
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700"
              >
                Back to Workspaces
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
