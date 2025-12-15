import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { devicesApi, metricsApi } from '../services/api';

export default function DeviceDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: device, isLoading } = useQuery({
    queryKey: ['device', id],
    queryFn: () => devicesApi.get(id!),
    enabled: !!id,
  });

  const { data: metrics } = useQuery({
    queryKey: ['deviceMetrics', id],
    queryFn: () => metricsApi.getDeviceMetrics(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  if (!device) {
    return <div className="text-gray-400">Device not found</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">{device.roomName}</h1>
        <p className="text-gray-400">{device.location || 'No location set'}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Device Info */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">Device Information</h2>
          <dl className="space-y-4">
            <div className="flex justify-between">
              <dt className="text-gray-400">Status</dt>
              <dd className="capitalize">{device.status}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-400">Platform</dt>
              <dd>{device.platform}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-400">Software Version</dt>
              <dd>{device.softwareVersion}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-400">Last Seen</dt>
              <dd>{new Date(device.lastSeen).toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-400">Device ID</dt>
              <dd className="text-xs font-mono">{device.id}</dd>
            </div>
          </dl>
        </div>

        {/* Capabilities */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">Capabilities</h2>
          {device.capabilities && Object.keys(device.capabilities).length > 0 ? (
            <pre className="text-sm text-gray-300 overflow-auto">
              {JSON.stringify(device.capabilities, null, 2)}
            </pre>
          ) : (
            <p className="text-gray-400">No capabilities reported</p>
          )}
        </div>

        {/* Actions */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">Actions</h2>
          <div className="space-y-3">
            <button className="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
              Restart Device
            </button>
            <button className="w-full py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors">
              Update Configuration
            </button>
            <button className="w-full py-2 bg-red-600 hover:bg-red-700 rounded-lg transition-colors">
              Remove Device
            </button>
          </div>
        </div>

        {/* Recent Metrics */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-medium mb-4">Recent Activity</h2>
          {metrics?.metrics && metrics.metrics.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-auto">
              {metrics.metrics.slice(0, 10).map((m: any) => (
                <div key={m.id} className="text-sm border-b border-gray-700 pb-2">
                  <span className="text-gray-400">
                    {new Date(m.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="ml-2">{m.type}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400">No recent activity</p>
          )}
        </div>
      </div>
    </div>
  );
}
