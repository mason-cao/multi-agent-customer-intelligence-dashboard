import { NavLink } from 'react-router-dom';

const navigation = [
  { name: 'Overview', path: '/', icon: '📊' },
  { name: 'Customer 360', path: '/customers', icon: '👤' },
  { name: 'Segments', path: '/segments', icon: '🎯' },
  { name: 'Churn & Retention', path: '/churn', icon: '⚠️' },
  { name: 'Sentiment & Support', path: '/sentiment', icon: '💬' },
  { name: 'Recommendations', path: '/recommendations', icon: '💡' },
  { name: 'Agent Audit', path: '/agents', icon: '🔍' },
  { name: 'Ask Anything', path: '/ask', icon: '✨' },
];

export default function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-6">
        <span className="text-xl font-bold text-gray-900">Nexus</span>
        <span className="text-sm font-medium text-blue-600">Intelligence</span>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigation.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <span>{item.icon}</span>
            {item.name}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-gray-200 p-4">
        <p className="text-xs text-gray-400">Last analysis: —</p>
      </div>
    </aside>
  );
}
