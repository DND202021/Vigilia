/**
 * ERIOP API Client
 * Centralized HTTP client for backend communication
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  AuthTokens,
  User,
  LoginCredentials,
  Incident,
  IncidentCreateRequest,
  IncidentUpdateRequest,
  Resource,
  ResourceCreateRequest,
  ResourceStatusUpdate,
  Alert,
  AlertAcknowledgeRequest,
  AlertCreateIncidentRequest,
  PaginatedResponse,
  DashboardStats,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Token storage keys
const ACCESS_TOKEN_KEY = 'eriop_access_token';
const REFRESH_TOKEN_KEY = 'eriop_refresh_token';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Token management
export const tokenStorage = {
  getAccessToken: (): string | null => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: (): string | null => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (tokens: AuthTokens) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  clearTokens: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

// Request interceptor - add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = tokenStorage.getRefreshToken();
      if (refreshToken) {
        try {
          const response = await axios.post<AuthTokens>(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          tokenStorage.setTokens(response.data);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          tokenStorage.clearTokens();
          window.location.href = '/login';
        }
      } else {
        tokenStorage.clearTokens();
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthTokens> => {
    const response = await api.post<AuthTokens>('/auth/login', {
      email: credentials.username,
      password: credentials.password,
    });
    tokenStorage.setTokens(response.data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    try {
      await api.post('/auth/logout');
    } finally {
      tokenStorage.clearTokens();
    }
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  refreshToken: async (): Promise<AuthTokens> => {
    const refreshToken = tokenStorage.getRefreshToken();
    const response = await api.post<AuthTokens>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    tokenStorage.setTokens(response.data);
    return response.data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },
};

// Helper to transform incident data (flatten location)
interface ApiIncident extends Omit<Incident, 'latitude' | 'longitude' | 'address'> {
  location?: {
    latitude: number;
    longitude: number;
    address?: string;
    building_info?: string;
  };
  latitude?: number;
  longitude?: number;
  address?: string;
}

const transformIncident = (data: ApiIncident): Incident => ({
  ...data,
  latitude: data.location?.latitude ?? data.latitude,
  longitude: data.location?.longitude ?? data.longitude,
  address: data.location?.address ?? data.address,
});

// Incidents API
export const incidentsApi = {
  list: async (params?: {
    status?: string;
    priority?: number;
    incident_type?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Incident>> => {
    const response = await api.get<PaginatedResponse<ApiIncident>>('/incidents', { params });
    return {
      ...response.data,
      items: response.data.items.map(transformIncident),
    };
  },

  getActive: async (): Promise<Incident[]> => {
    const response = await api.get<ApiIncident[]>('/incidents/active');
    return response.data.map(transformIncident);
  },

  get: async (id: string): Promise<Incident> => {
    const response = await api.get<ApiIncident>(`/incidents/${id}`);
    return transformIncident(response.data);
  },

  create: async (data: IncidentCreateRequest): Promise<Incident> => {
    const response = await api.post<ApiIncident>('/incidents', data);
    return transformIncident(response.data);
  },

  update: async (id: string, data: IncidentUpdateRequest): Promise<Incident> => {
    const response = await api.patch<ApiIncident>(`/incidents/${id}`, data);
    return transformIncident(response.data);
  },

  updateStatus: async (id: string, status: string, notes?: string): Promise<Incident> => {
    const response = await api.post<ApiIncident>(`/incidents/${id}/status`, { status, notes });
    return transformIncident(response.data);
  },

  assignUnit: async (id: string, unitId: string): Promise<Incident> => {
    const response = await api.post<ApiIncident>(`/incidents/${id}/assign`, { unit_id: unitId });
    return transformIncident(response.data);
  },

  addTimeline: async (id: string, eventType: string, description: string): Promise<Incident> => {
    const response = await api.post<ApiIncident>(`/incidents/${id}/timeline`, {
      event_type: eventType,
      description,
    });
    return transformIncident(response.data);
  },
};

// Resources API
export const resourcesApi = {
  list: async (params?: {
    resource_type?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Resource>> => {
    const response = await api.get<PaginatedResponse<Resource>>('/resources', { params });
    return response.data;
  },

  getAvailable: async (resourceType?: string): Promise<Resource[]> => {
    const response = await api.get<Resource[]>('/resources/available', {
      params: resourceType ? { resource_type: resourceType } : undefined,
    });
    return response.data;
  },

  get: async (id: string): Promise<Resource> => {
    const response = await api.get<Resource>(`/resources/${id}`);
    return response.data;
  },

  create: async (data: ResourceCreateRequest): Promise<Resource> => {
    const response = await api.post<Resource>('/resources', data);
    return response.data;
  },

  updateStatus: async (id: string, data: ResourceStatusUpdate): Promise<Resource> => {
    const response = await api.patch<Resource>(`/resources/${id}/status`, data);
    return response.data;
  },

  updateLocation: async (id: string, latitude: number, longitude: number): Promise<Resource> => {
    const response = await api.patch<Resource>(`/resources/${id}/location`, {
      latitude,
      longitude,
    });
    return response.data;
  },
};

// Alerts API
export const alertsApi = {
  list: async (params?: {
    status?: string;
    severity?: string;
    alert_type?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Alert>> => {
    const response = await api.get<PaginatedResponse<Alert>>('/alerts', { params });
    return response.data;
  },

  getPending: async (): Promise<Alert[]> => {
    const response = await api.get<Alert[]>('/alerts/pending');
    return response.data;
  },

  get: async (id: string): Promise<Alert> => {
    const response = await api.get<Alert>(`/alerts/${id}`);
    return response.data;
  },

  acknowledge: async (id: string, data?: AlertAcknowledgeRequest): Promise<Alert> => {
    const response = await api.post<Alert>(`/alerts/${id}/acknowledge`, data);
    return response.data;
  },

  createIncident: async (id: string, data: AlertCreateIncidentRequest): Promise<Incident> => {
    const response = await api.post<Incident>(`/alerts/${id}/create-incident`, data);
    return response.data;
  },

  resolve: async (id: string, isFalseAlarm?: boolean): Promise<Alert> => {
    const response = await api.post<Alert>(`/alerts/${id}/resolve`, {
      is_false_alarm: isFalseAlarm,
    });
    return response.data;
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await api.get<DashboardStats>('/dashboard/stats');
    return response.data;
  },
};

// Health API
export const healthApi = {
  check: async (): Promise<{ status: string; timestamp: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
