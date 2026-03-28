import { Compass, ArrowLeft, LayoutDashboard } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-app-gradient p-8">
      <div className="bg-orbs">
        <div className="bg-orb bg-orb--1" />
        <div className="bg-orb bg-orb--2" />
        <div className="bg-orb bg-orb--3" />
      </div>
      <div className="bg-vignette" />
      <div className="relative z-10 w-full max-w-md text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[rgba(255,255,255,0.04)] ring-1 ring-[rgba(255,255,255,0.08)]">
          <Compass
            className="h-8 w-8 text-[rgba(255,255,255,0.38)]"
            strokeWidth={1.5}
          />
        </div>
        <p className="mt-6 font-mono text-sm font-semibold uppercase tracking-wide text-[rgba(255,255,255,0.25)]">
          404
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-white">
          Page not found
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-[rgba(255,255,255,0.45)]">
          This route doesn't exist in Luminosity Intelligence. You may have
          followed an outdated link or typed an incorrect URL.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="btn-secondary"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </button>
          <button
            onClick={() => navigate('/workspaces')}
            className="btn-primary"
          >
            <LayoutDashboard className="h-4 w-4" />
            Workspace Hub
          </button>
        </div>
      </div>
    </div>
  );
}
