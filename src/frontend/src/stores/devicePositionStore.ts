/**
 * Device Position Store (Zustand)
 *
 * Manages device positions on floor plans for real-time monitoring.
 */

import { create } from 'zustand';
import { iotDevicesApi } from '../services/api';
import type { DeviceFloorPosition, DeviceStatus } from '../types';

interface DevicePositionStore {
  // State
  positions: Record<string, DeviceFloorPosition>;
  currentFloorPlanId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setCurrentFloorPlan: (floorPlanId: string | null) => void;
  loadDevicesForFloorPlan: (floorPlanId: string) => Promise<void>;
  updateDevicePosition: (deviceId: string, x: number, y: number) => Promise<void>;
  handleRemotePositionUpdate: (deviceId: string, x: number, y: number, timestamp: string) => void;
  handleRemoteStatusChange: (deviceId: string, status: DeviceStatus, timestamp: string) => void;
  clearPositions: () => void;
  clearError: () => void;
}

const initialState = {
  positions: {} as Record<string, DeviceFloorPosition>,
  currentFloorPlanId: null as string | null,
  isLoading: false,
  error: null as string | null,
};

export const useDevicePositionStore = create<DevicePositionStore>((set, get) => ({
  ...initialState,

  setCurrentFloorPlan: (floorPlanId) => {
    set({ currentFloorPlanId: floorPlanId });
    if (!floorPlanId) {
      set({ positions: {} });
    }
  },

  loadDevicesForFloorPlan: async (floorPlanId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await iotDevicesApi.list({ floor_plan_id: floorPlanId });
      const positions: Record<string, DeviceFloorPosition> = {};

      for (const device of response.items) {
        if (device.position_x != null && device.position_y != null) {
          positions[device.id] = {
            device_id: device.id,
            floor_plan_id: floorPlanId,
            position_x: device.position_x,
            position_y: device.position_y,
            status: device.status,
            last_seen: device.last_seen,
            timestamp: new Date().toISOString(),
          };
        }
      }

      set({ positions, currentFloorPlanId: floorPlanId, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load devices',
        isLoading: false,
      });
    }
  },

  updateDevicePosition: async (deviceId, x, y) => {
    const { currentFloorPlanId, positions } = get();
    if (!currentFloorPlanId) return;

    // Optimistic update
    const timestamp = new Date().toISOString();
    set((state) => ({
      positions: {
        ...state.positions,
        [deviceId]: {
          ...state.positions[deviceId],
          device_id: deviceId,
          floor_plan_id: currentFloorPlanId,
          position_x: x,
          position_y: y,
          timestamp,
        },
      },
    }));

    try {
      await iotDevicesApi.updatePosition(deviceId, {
        position_x: x,
        position_y: y,
        floor_plan_id: currentFloorPlanId,
      });
    } catch (error) {
      // Rollback on error
      set((state) => ({
        positions: {
          ...state.positions,
          [deviceId]: positions[deviceId],
        },
        error: error instanceof Error ? error.message : 'Failed to update device position',
      }));
    }
  },

  handleRemotePositionUpdate: (deviceId, x, y, timestamp) => {
    const { currentFloorPlanId, positions } = get();

    // Only update if timestamp is newer
    const existing = positions[deviceId];
    if (existing && existing.timestamp > timestamp) {
      return; // Ignore older update
    }

    set((state) => ({
      positions: {
        ...state.positions,
        [deviceId]: {
          ...state.positions[deviceId],
          device_id: deviceId,
          floor_plan_id: currentFloorPlanId || '',
          position_x: x,
          position_y: y,
          timestamp,
        },
      },
    }));
  },

  handleRemoteStatusChange: (deviceId, status, timestamp) => {
    const { positions } = get();

    // Only update if device exists in our positions
    if (!positions[deviceId]) return;

    // Only update if timestamp is newer
    if (positions[deviceId].timestamp > timestamp) {
      return; // Ignore older update
    }

    set((state) => ({
      positions: {
        ...state.positions,
        [deviceId]: {
          ...state.positions[deviceId],
          status,
          timestamp,
        },
      },
    }));
  },

  clearPositions: () => {
    set({ positions: {}, currentFloorPlanId: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));
