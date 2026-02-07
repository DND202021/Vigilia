/**
 * Telemetry Real-Time State Store (Zustand)
 *
 * Manages rolling buffers of telemetry data points per device+metric.
 * Designed for real-time dashboard with max 1000 points per buffer.
 */
import { create } from 'zustand';
import type { TelemetryDataPoint } from '../types';
import { telemetryApi } from '../services/api';

const MAX_BUFFER_SIZE = 1000;

interface TelemetryBuffer {
  [deviceId: string]: {
    [metricName: string]: TelemetryDataPoint[];
  };
}

interface ActiveSubscription {
  deviceId: string;
  metricName: string;
}

interface TelemetryStore {
  // State
  buffers: TelemetryBuffer;
  activeSubscriptions: ActiveSubscription[];
  availableMetrics: { [deviceId: string]: string[] };
  isLoadingMetrics: boolean;
  isLoadingHistory: boolean;
  error: string | null;

  // Actions - Real-time data
  addDataPoint: (deviceId: string, metricName: string, point: TelemetryDataPoint) => void;
  addDataPoints: (deviceId: string, metricName: string, points: TelemetryDataPoint[]) => void;
  getDeviceMetricData: (deviceId: string, metricName: string) => TelemetryDataPoint[];
  clearBuffer: (deviceId: string, metricName?: string) => void;
  clearAllBuffers: () => void;

  // Actions - Subscriptions
  addSubscription: (deviceId: string, metricName: string) => void;
  removeSubscription: (deviceId: string, metricName: string) => void;

  // Actions - API calls
  fetchAvailableMetrics: (deviceId: string) => Promise<void>;
  fetchHistoricalData: (
    deviceId: string,
    metricName: string,
    startTime?: string,
    endTime?: string,
    aggregation?: string
  ) => Promise<void>;

  // Utility
  clearError: () => void;
}

export const useTelemetryStore = create<TelemetryStore>((set, get) => ({
  buffers: {},
  activeSubscriptions: [],
  availableMetrics: {},
  isLoadingMetrics: false,
  isLoadingHistory: false,
  error: null,

  addDataPoint: (deviceId, metricName, point) => set((state) => {
    const newBuffers = { ...state.buffers };
    if (!newBuffers[deviceId]) {
      newBuffers[deviceId] = {};
    }
    const currentBuffer = newBuffers[deviceId][metricName] || [];
    const updatedBuffer = [...currentBuffer, point];
    // Maintain rolling window
    if (updatedBuffer.length > MAX_BUFFER_SIZE) {
      updatedBuffer.splice(0, updatedBuffer.length - MAX_BUFFER_SIZE);
    }
    newBuffers[deviceId] = { ...newBuffers[deviceId], [metricName]: updatedBuffer };
    return { buffers: newBuffers };
  }),

  addDataPoints: (deviceId, metricName, points) => set((state) => {
    const newBuffers = { ...state.buffers };
    if (!newBuffers[deviceId]) {
      newBuffers[deviceId] = {};
    }
    const currentBuffer = newBuffers[deviceId][metricName] || [];
    const updatedBuffer = [...currentBuffer, ...points];
    if (updatedBuffer.length > MAX_BUFFER_SIZE) {
      updatedBuffer.splice(0, updatedBuffer.length - MAX_BUFFER_SIZE);
    }
    newBuffers[deviceId] = { ...newBuffers[deviceId], [metricName]: updatedBuffer };
    return { buffers: newBuffers };
  }),

  getDeviceMetricData: (deviceId, metricName) => {
    const state = get();
    return state.buffers[deviceId]?.[metricName] || [];
  },

  clearBuffer: (deviceId, metricName) => set((state) => {
    const newBuffers = { ...state.buffers };
    if (metricName) {
      if (newBuffers[deviceId]) {
        const { [metricName]: _, ...rest } = newBuffers[deviceId];
        newBuffers[deviceId] = rest;
      }
    } else {
      delete newBuffers[deviceId];
    }
    return { buffers: newBuffers };
  }),

  clearAllBuffers: () => set({ buffers: {} }),

  addSubscription: (deviceId, metricName) => set((state) => {
    const exists = state.activeSubscriptions.some(
      (s) => s.deviceId === deviceId && s.metricName === metricName
    );
    if (exists) return state;
    return {
      activeSubscriptions: [...state.activeSubscriptions, { deviceId, metricName }],
    };
  }),

  removeSubscription: (deviceId, metricName) => set((state) => ({
    activeSubscriptions: state.activeSubscriptions.filter(
      (s) => !(s.deviceId === deviceId && s.metricName === metricName)
    ),
  })),

  fetchAvailableMetrics: async (deviceId) => {
    set({ isLoadingMetrics: true, error: null });
    try {
      const response = await telemetryApi.getAvailableMetrics(deviceId);
      set((state) => ({
        availableMetrics: { ...state.availableMetrics, [deviceId]: response.metrics },
        isLoadingMetrics: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch available metrics',
        isLoadingMetrics: false,
      });
    }
  },

  fetchHistoricalData: async (deviceId, metricName, startTime, endTime, aggregation) => {
    set({ isLoadingHistory: true, error: null });
    try {
      const response = await telemetryApi.queryTelemetry(deviceId, {
        metric_name: metricName,
        start_time: startTime,
        end_time: endTime,
        aggregation,
      });
      // Load historical data into buffer (replace existing)
      const points: TelemetryDataPoint[] = response.data.map((d: any) => ({
        time: d.time,
        value: d.value ?? d.avg ?? null,
      }));
      set((state) => {
        const newBuffers = { ...state.buffers };
        if (!newBuffers[deviceId]) {
          newBuffers[deviceId] = {};
        }
        newBuffers[deviceId] = { ...newBuffers[deviceId], [metricName]: points };
        return { buffers: newBuffers, isLoadingHistory: false };
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch telemetry data',
        isLoadingHistory: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));
