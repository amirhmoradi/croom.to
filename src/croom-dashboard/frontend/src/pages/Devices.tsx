import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { devicesApi } from '../services/api';

export default function Devices() {
  const { data, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: devicesApi.list,
    refetchInterval: 30000,
  });

  if (isLoading) {
    return <div className="text-gray-400">Loading devices...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Devices</h1>
          <p className="text-gray-400 mt-1">{data?.total || 0} devices registered</p>
        </div>
        <Link
          to="/provisioning"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          Add Device
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data?.devices?.map((device: any) => (
          <DeviceCard key={device.id} device={device} />
        ))}
      </div>

      {(!data?.devices || data.devices.length === 0) && (
        <div className="text-center py-12 bg-gray-800 rounded-lg">
          <p className="text-gray-400">No devices registered</p>
          <Link
            to="/provisioning"
            className="inline-block mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
          >
            Add Your First Device
          </Link>
        </div>
      )}
    </div>
  );
}

function DeviceCard({ device }: { device: any }) {
  const statusColors: Record<string, string> = {
    online: 'border-green-500',
    offline: 'border-gray-500',
    error: 'border-red-500',
    provisioning: 'border-yellow-500',
  };

  return (
    <Link
      to={`/devices/${device.id}`}
      className={`block bg-gray-800 rounded-lg p-6 border-l-4 ${
        statusColors[device.status] || statusColors.offline
      } hover:bg-gray-700 transition-colors`}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-medium">{device.roomName}</h3>
          <p className="text-sm text-gray-400">{device.location || 'No location'}</p>
        </div>
        <StatusIndicator status={device.status} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-400">Platform</p>
          <p>{device.platform}</p>
        </div>
        <div>
          <p className="text-gray-400">Version</p>
          <p>{device.softwareVersion}</p>
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-500">
        Last seen: {new Date(device.lastSeen).toLocaleString()}
      </div>
    </Link>
  );
}

function StatusIndicator({ status }: { status: string }) {
  const colors: Record<string, string> = {
    online: 'bg-green-500',
    offline: 'bg-gray-500',
    error: 'bg-red-500',
    provisioning: 'bg-yellow-500',
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`w-3 h-3 rounded-full ${colors[status]}`} />
      <span className="text-sm capitalize">{status}</span>
    </div>
  );
}
