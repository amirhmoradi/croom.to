import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const stored = localStorage.getItem('pimeet-auth');
  if (stored) {
    const { state } = JSON.parse(stored);
    if (state?.token) {
      config.headers.Authorization = `Bearer ${state.token}`;
    }
  }
  return config;
});

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const { data } = await api.post('/auth/login', { email, password });
    return data;
  },
  me: async () => {
    const { data } = await api.get('/auth/me');
    return data;
  },
};

// Devices API
export const devicesApi = {
  list: async () => {
    const { data } = await api.get('/devices');
    return data;
  },
  get: async (id: string) => {
    const { data } = await api.get(`/devices/${id}`);
    return data;
  },
  update: async (id: string, updates: any) => {
    const { data } = await api.put(`/devices/${id}`, updates);
    return data;
  },
  delete: async (id: string) => {
    const { data } = await api.delete(`/devices/${id}`);
    return data;
  },
  sendCommand: async (id: string, command: string, params?: any) => {
    const { data } = await api.post(`/devices/${id}/command`, { command, params });
    return data;
  },
  statusSummary: async () => {
    const { data } = await api.get('/devices/summary/status');
    return data;
  },
};

// Metrics API
export const metricsApi = {
  getSummary: async (period: string = '24h') => {
    const { data } = await api.get('/metrics/summary', { params: { period } });
    return data;
  },
  getDeviceMetrics: async (deviceId: string, type?: string) => {
    const { data } = await api.get(`/metrics/device/${deviceId}`, { params: { type } });
    return data;
  },
  getMeetings: async (from?: string, to?: string) => {
    const { data } = await api.get('/metrics/meetings', { params: { from, to } });
    return data;
  },
};

// Provisioning API
export const provisioningApi = {
  createToken: async (roomName: string, location?: string) => {
    const { data } = await api.post('/provisioning/token', { roomName, location });
    return data;
  },
  getPending: async () => {
    const { data } = await api.get('/provisioning/pending');
    return data;
  },
  cancelEnrollment: async (deviceId: string) => {
    const { data } = await api.delete(`/provisioning/token/${deviceId}`);
    return data;
  },
};

export default api;
