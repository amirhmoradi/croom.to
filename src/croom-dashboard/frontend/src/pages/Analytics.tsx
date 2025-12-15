import { useQuery } from '@tanstack/react-query';
import { metricsApi } from '../services/api';

export default function Analytics() {
  const { data: summary } = useQuery({
    queryKey: ['metricsSummary', '7d'],
    queryFn: () => metricsApi.getSummary('7d'),
  });

  const { data: meetings } = useQuery({
    queryKey: ['meetings'],
    queryFn: () => metricsApi.getMeetings(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-gray-400 mt-1">Usage statistics and insights</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-gray-400 text-sm">Total Meetings (7d)</h3>
          <p className="text-4xl font-bold mt-2">{meetings?.totalMeetings || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-gray-400 text-sm">Total Minutes (7d)</h3>
          <p className="text-4xl font-bold mt-2">{meetings?.totalMinutes || 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-gray-400 text-sm">Avg. Occupancy</h3>
          <p className="text-4xl font-bold mt-2">{summary?.occupancy?.average || 0}</p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-medium mb-4">Recent Meetings</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-700">
                <th className="pb-3">Platform</th>
                <th className="pb-3">Started</th>
                <th className="pb-3">Duration</th>
                <th className="pb-3">Device</th>
              </tr>
            </thead>
            <tbody>
              {meetings?.meetings?.slice(0, 20).map((meeting: any, i: number) => (
                <tr key={i} className="border-b border-gray-700/50">
                  <td className="py-3 capitalize">{meeting.platform}</td>
                  <td className="py-3">{new Date(meeting.joinedAt).toLocaleString()}</td>
                  <td className="py-3">{meeting.durationMinutes} min</td>
                  <td className="py-3 text-xs font-mono text-gray-400">
                    {meeting.deviceId.slice(0, 8)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
