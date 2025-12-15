import { useAuthStore } from '../store/auth';

export default function Settings() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-gray-400 mt-1">Dashboard configuration</p>
      </div>

      {/* Account */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Account</h2>
        <dl className="space-y-4">
          <div className="flex justify-between">
            <dt className="text-gray-400">Name</dt>
            <dd>{user?.name}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Email</dt>
            <dd>{user?.email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">Role</dt>
            <dd className="capitalize">{user?.role}</dd>
          </div>
        </dl>
        <button className="mt-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors">
          Change Password
        </button>
      </div>

      {/* Dashboard Settings */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Dashboard Settings</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p>Auto-refresh</p>
              <p className="text-sm text-gray-400">Automatically refresh device status</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-gray-600 rounded-full peer peer-checked:bg-blue-600"></div>
            </label>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p>Notifications</p>
              <p className="text-sm text-gray-400">Receive alerts for device issues</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" className="sr-only peer" defaultChecked />
              <div className="w-11 h-6 bg-gray-600 rounded-full peer peer-checked:bg-blue-600"></div>
            </label>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">System Information</h2>
        <dl className="space-y-4">
          <div className="flex justify-between">
            <dt className="text-gray-400">Dashboard Version</dt>
            <dd>2.0.0-dev</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-400">API Endpoint</dt>
            <dd className="text-xs font-mono">{window.location.origin}/api</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
