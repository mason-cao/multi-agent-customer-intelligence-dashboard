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
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[rgba(248,113,113,0.15)]">
              <AlertTriangle className="h-7 w-7 text-[var(--color-danger)]" strokeWidth={1.5} />
            </div>
            <h2 className="mt-5 text-sm font-semibold text-white">
              Something went wrong
            </h2>
            <p className="mt-1.5 text-[13px] leading-relaxed text-[rgba(255,255,255,0.38)]">
              This page encountered an unexpected error. Try navigating back or
              returning to the workspace hub.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                onClick={() => this.setState({ hasError: false })}
                className="btn-secondary"
              >
                Try Again
              </button>
              <a
                href="/workspaces"
                className="btn-primary"
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
