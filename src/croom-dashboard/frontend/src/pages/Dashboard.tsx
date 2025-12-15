import { useQuery } from '@tanstack/react-query';
import { devicesApi, metricsApi } from '../services/api';

export default function Dashboard() {
  const { data: statusSummary } = useQuery({
    queryKey: ['statusSummary'],
    queryFn: devicesApi.statusSummary,
    refetchInterval: 30000,
  });

  const { data: metricsSummary } = useQuery({
    queryKey: ['metricsSummary'],
    queryFn: () => metricsApi.getSummary('24h'),
    refetchInterval: 60000,
  });

  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: devicesApi.list,
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-gray-400 mt-1">Overview of your Croom fleet</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Devices"
          value={statusSummary?.total || 0}
          icon="📺"
        />
        <StatCard
          title="Online"
          value={statusSummary?.online || 0}
          icon="🟢"
          color="green"
        />
        <StatCard
          title="Offline"
          value={statusSummary?.offline || 0}
          icon="🔴"
          color="red"
        />
        <StatCard
          title="Errors"
          value={statusSummary?.error || 0}
          icon="⚠️"
          color="yellow"
        />
      </div>

      {/* Metrics summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">Meetings Today</h3>
          <p className="text-4xl font-bold">{metricsSummary?.meetings?.total || 0}</p>
          <p className="text-gray-400 text-sm mt-2">Total meeting sessions</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">Average Occupancy</h3>
          <p className="text-4xl font-bold">{metricsSummary?.occupancy?.average || 0}</p>
          <p className="text-gray-400 text-sm mt-2">People per room</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">Peak Occupancy</h3>
          <p className="text-4xl font-bold">{metricsSummary?.occupancy?.peak || 0}</p>
          <p className="text-gray-400 text-sm mt-2">Maximum detected today</p>
        </div>
      </div>

      {/* Device list */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-medium mb-4">Devices</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3">Room</th>
                <th className="pb-3">Status</th>
                <th className="pb-3">Platform</th>
                <th className="pb-3">Version</th>
                <th className="pb-3">Last Seen</th>
              </tr>
            </thead>
            <tbody>
              {devices?.devices?.map((device: any) => (
                <tr key={device.id} className="border-b border-gray-700/50">
                  <td className="py-4">
                    <div>
                      <p className="font-medium">{device.roomName}</p>
                      <p className="text-sm text-gray-400">{device.location}</p>
                    </div>
                  </td>
                  <td className="py-4">
                    <StatusBadge status={device.status} />
                  </td>
                  <td className="py-4 text-gray-300">{device.platform}</td>
                  <td className="py-4 text-gray-300">{device.softwareVersion}</td>
                  <td className="py-4 text-gray-400">
                    {new Date(device.lastSeen).toLocaleString()}
                  </td>
                </tr>
              ))}
              {(!devices?.devices || devices.devices.length === 0) && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-500">
                    No devices registered yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: number;
  icon: string;
  color?: string;
}) {
  const colorClass =
    color === 'green'
      ? 'text-green-400'
      : color === 'red'
      ? 'text-red-400'
      : color === 'yellow'
      ? 'text-yellow-400'
      : 'text-white';

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className={`text-3xl font-bold mt-1 ${colorClass}`}>{value}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    online: 'bg-green-900/50 text-green-400',
    offline: 'bg-gray-700 text-gray-400',
    error: 'bg-red-900/50 text-red-400',
    provisioning: 'bg-yellow-900/50 text-yellow-400',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.offline}`}>
      {status}
    </span>
  );
}
