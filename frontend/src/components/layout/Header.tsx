export default function Header() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-8">
      <h1 className="text-lg font-semibold text-gray-900">
        Customer Intelligence Dashboard
      </h1>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5 text-sm text-gray-500">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          System Healthy
        </span>
        <button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors">
          Run Analysis
        </button>
      </div>
    </header>
  );
}
