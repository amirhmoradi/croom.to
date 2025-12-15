import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

interface LayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/devices', label: 'Devices', icon: '📺' },
  { path: '/analytics', label: 'Analytics', icon: '📈' },
  { path: '/provisioning', label: 'Provisioning', icon: '➕' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-gray-800 border-r border-gray-700">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-gray-700">
            <h1 className="text-2xl font-bold text-white">Croom</h1>
            <p className="text-sm text-gray-400">Enterprise Dashboard</p>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 rounded-lg transition-colors ${
                  location.pathname === item.path
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                <span className="mr-3">{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </nav>

          {/* User menu */}
          <div className="p-4 border-t border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{user?.name}</p>
                <p className="text-sm text-gray-400">{user?.role}</p>
              </div>
              <button
                onClick={handleLogout}
                className="px-3 py-1 text-sm text-gray-400 hover:text-white"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
