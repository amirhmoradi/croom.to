import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { provisioningApi } from '../services/api';

export default function Provisioning() {
  const [roomName, setRoomName] = useState('');
  const [location, setLocation] = useState('');
  const [generatedToken, setGeneratedToken] = useState<any>(null);

  const queryClient = useQueryClient();

  const { data: pending } = useQuery({
    queryKey: ['pendingEnrollments'],
    queryFn: provisioningApi.getPending,
  });

  const createToken = useMutation({
    mutationFn: () => provisioningApi.createToken(roomName, location),
    onSuccess: (data) => {
      setGeneratedToken(data);
      setRoomName('');
      setLocation('');
      queryClient.invalidateQueries({ queryKey: ['pendingEnrollments'] });
    },
  });

  const cancelEnrollment = useMutation({
    mutationFn: provisioningApi.cancelEnrollment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingEnrollments'] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Device Provisioning</h1>
        <p className="text-gray-400 mt-1">Add new devices to your fleet</p>
      </div>

      {/* Create enrollment token */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Create Enrollment Token</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">Room Name</label>
            <input
              type="text"
              value={roomName}
              onChange={(e) => setRoomName(e.target.value)}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              placeholder="Conference Room A"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Location (optional)</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
              placeholder="Building 1, Floor 2"
            />
          </div>
        </div>
        <button
          onClick={() => createToken.mutate()}
          disabled={!roomName || createToken.isPending}
          className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
        >
          {createToken.isPending ? 'Creating...' : 'Generate Token'}
        </button>
      </div>

      {/* Generated token display */}
      {generatedToken && (
        <div className="bg-green-900/30 border border-green-500 rounded-lg p-6">
          <h3 className="text-lg font-medium text-green-400 mb-4">Token Generated!</h3>
          <div className="space-y-4">
            <div>
              <label className="text-sm text-gray-400">Enrollment Token</label>
              <div className="mt-1 p-3 bg-gray-900 rounded font-mono text-sm break-all">
                {generatedToken.token}
              </div>
            </div>
            <div>
              <label className="text-sm text-gray-400">Enrollment URL</label>
              <div className="mt-1 p-3 bg-gray-900 rounded font-mono text-sm break-all">
                {generatedToken.enrollmentUrl}
              </div>
            </div>
            <p className="text-sm text-gray-400">
              Use this token on the device during setup. Expires: {generatedToken.expiresAt}
            </p>
          </div>
        </div>
      )}

      {/* Pending enrollments */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Pending Enrollments</h2>
        {pending?.pendingDevices && pending.pendingDevices.length > 0 ? (
          <div className="space-y-3">
            {pending.pendingDevices.map((device: any) => (
              <div
                key={device.id}
                className="flex items-center justify-between p-4 bg-gray-700 rounded-lg"
              >
                <div>
                  <p className="font-medium">{device.roomName}</p>
                  <p className="text-sm text-gray-400">
                    Created: {new Date(device.createdAt).toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={() => cancelEnrollment.mutate(device.id)}
                  className="px-3 py-1 text-sm text-red-400 hover:bg-red-900/50 rounded"
                >
                  Cancel
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400">No pending enrollments</p>
        )}
      </div>
    </div>
  );
}
