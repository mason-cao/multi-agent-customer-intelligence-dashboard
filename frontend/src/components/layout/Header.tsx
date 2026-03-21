import { Activity, Play } from 'lucide-react';

export default function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-8">
      <h1 className="text-lg font-semibold text-slate-800">
        Customer Intelligence Dashboard
      </h1>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700">
          <Activity className="h-3.5 w-3.5" />
          System Healthy
        </span>
        <button className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm shadow-emerald-200 transition-all duration-200 hover:bg-emerald-700 hover:shadow-md hover:shadow-emerald-200 active:scale-[0.98]">
          <Play className="h-3.5 w-3.5" />
          Run Analysis
        </button>
      </div>
    </header>
  );
}
