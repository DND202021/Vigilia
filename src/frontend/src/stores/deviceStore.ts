/**
 * IoT Device State Store (Zustand)
 */

import { create } from 'zustand';
import type { IoTDevice, IoTDeviceCreateRequest, IoTDeviceUpdateRequest, DevicePositionUpdate } from '../types';
import { iotDevicesApi } from '../services/api';

interface DeviceStore {
  devices: IoTDevice[];
  selectedDevice: IoTDevice | null;
  totalDevices: number;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchDevices: (params?: {
    building_id?: string;
    floor_plan_id?: string;
    device_type?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }) => Promise<void>;
  fetchDevice: (id: string) => Promise<void>;
  createDevice: (data: IoTDeviceCreateRequest) => Promise<IoTDevice>;
  updateDevice: (id: string, data: IoTDeviceUpdateRequest) => Promise<void>;
  deleteDevice: (id: string) => Promise<void>;
  updatePosition: (id: string, data: DevicePositionUpdate) => Promise<void>;
  setSelectedDevice: (device: IoTDevice | null) => void;
  clearError: () => void;

  // Real-time update handler
  handleDeviceStatusUpdate: (data: {
    device_id: string;
    status: string;
    name?: string;
  }) => void;
}

export const useDeviceStore = create<DeviceStore>((set) => ({
  devices: [],
  selectedDevice: null,
  totalDevices: 0,
  isLoading: false,
  error: null,

  fetchDevices: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await iotDevicesApi.list(params);
      set({ devices: response.items, totalDevices: response.total, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch devices',
        isLoading: false,
      });
    }
  },

  fetchDevice: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const device = await iotDevicesApi.get(id);
      set({ selectedDevice: device, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch device',
        isLoading: false,
      });
    }
  },

  createDevice: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const device = await iotDevicesApi.create(data);
      set((state) => ({
        devices: [device, ...state.devices],
        totalDevices: state.totalDevices + 1,
        isLoading: false,
      }));
      return device;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create device',
        isLoading: false,
      });
      throw error;
    }
  },

  updateDevice: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await iotDevicesApi.update(id, data);
      set((state) => ({
        devices: state.devices.map((d) => (d.id === id ? updated : d)),
        selectedDevice: state.selectedDevice?.id === id ? updated : state.selectedDevice,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update device',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteDevice: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await iotDevicesApi.delete(id);
      set((state) => ({
        devices: state.devices.filter((d) => d.id !== id),
        totalDevices: state.totalDevices - 1,
        selectedDevice: state.selectedDevice?.id === id ? null : state.selectedDevice,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete device',
        isLoading: false,
      });
      throw error;
    }
  },

  updatePosition: async (id, data) => {
    try {
      const updated = await iotDevicesApi.updatePosition(id, data);
      set((state) => ({
        devices: state.devices.map((d) => (d.id === id ? updated : d)),
        selectedDevice: state.selectedDevice?.id === id ? updated : state.selectedDevice,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update device position',
      });
      throw error;
    }
  },

  setSelectedDevice: (device) => set({ selectedDevice: device }),

  clearError: () => set({ error: null }),

  handleDeviceStatusUpdate: (data) => {
    const now = new Date().toISOString();
    set((state) => ({
      devices: state.devices.map((d) =>
        d.id === data.device_id
          ? {
              ...d,
              status: data.status as IoTDevice['status'],
              // Update last_seen when device comes online or has activity
              last_seen: data.status === 'online' || data.status === 'alert' ? now : d.last_seen,
            }
          : d
      ),
      selectedDevice:
        state.selectedDevice?.id === data.device_id
          ? {
              ...state.selectedDevice,
              status: data.status as IoTDevice['status'],
              last_seen: data.status === 'online' || data.status === 'alert' ? now : state.selectedDevice.last_seen,
            }
          : state.selectedDevice,
    }));
  },
}));
