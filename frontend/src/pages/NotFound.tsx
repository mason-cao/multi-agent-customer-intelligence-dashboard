import { Compass, ArrowLeft, LayoutDashboard } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100">
          <Compass className="h-8 w-8 text-slate-400" strokeWidth={1.5} />
        </div>
        <p className="mt-6 text-sm font-semibold uppercase tracking-wide text-slate-400">
          404
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
          Page not found
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-500">
          This route doesn't exist in Luminosity Intelligence. You may have
          followed an outdated link or typed an incorrect URL.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </button>
          <button
            onClick={() => navigate('/workspaces')}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-emerald-700"
          >
            <LayoutDashboard className="h-4 w-4" />
            Workspace Hub
          </button>
        </div>
      </div>
    </div>
  );
}
