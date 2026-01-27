/**
 * Building Detail Page Store (Zustand)
 *
 * Manages state for the BuildingDetailPage: building data, floor plans,
 * floor selection, devices for the current floor, placement mode, and alerts.
 */

import { create } from 'zustand';
import { buildingsApi, iotDevicesApi, soundAlertsApi } from '../services/api';
import type { Building, FloorPlan, IoTDevice, SoundAlert } from '../types';

interface BuildingDetailStore {
  // Data
  building: Building | null;
  floorPlans: FloorPlan[];
  selectedFloor: FloorPlan | null;
  devices: IoTDevice[];
  alerts: SoundAlert[];
  alertCount: number;

  // UI state
  selectedDevice: IoTDevice | null;
  isPlacementMode: boolean;
  placementDeviceId: string | null;
  isLoading: boolean;
  isLoadingDevices: boolean;
  isLoadingAlerts: boolean;
  error: string | null;

  // Actions
  fetchBuilding: (id: string) => Promise<void>;
  fetchFloorPlans: (buildingId: string) => Promise<void>;
  selectFloor: (floor: FloorPlan | null) => void;
  fetchDevicesForFloor: (floorPlanId: string) => Promise<void>;
  fetchAlertsForFloor: (floorPlanId: string) => Promise<void>;
  fetchBuildingAlerts: (buildingId: string) => Promise<void>;
  setSelectedDevice: (device: IoTDevice | null) => void;
  enterPlacementMode: (deviceId: string) => void;
  exitPlacementMode: () => void;
  placeDevice: (deviceId: string, posX: number, posY: number, floorPlanId: string) => Promise<void>;
  addFloorPlan: (floorPlan: FloorPlan) => void;
  reset: () => void;
  clearError: () => void;
}

const initialState = {
  building: null,
  floorPlans: [],
  selectedFloor: null,
  devices: [],
  alerts: [],
  alertCount: 0,
  selectedDevice: null,
  isPlacementMode: false,
  placementDeviceId: null,
  isLoading: false,
  isLoadingDevices: false,
  isLoadingAlerts: false,
  error: null,
};

export const useBuildingDetailStore = create<BuildingDetailStore>((set, get) => ({
  ...initialState,

  fetchBuilding: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const building = await buildingsApi.get(id);
      set({ building, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch building',
        isLoading: false,
      });
    }
  },

  fetchFloorPlans: async (buildingId) => {
    try {
      const plans = await buildingsApi.getFloorPlans(buildingId);
      const sorted = plans.sort((a, b) => a.floor_number - b.floor_number);
      set({ floorPlans: sorted });

      // Auto-select first floor if none selected
      if (!get().selectedFloor && sorted.length > 0) {
        const ground = sorted.find((p) => p.floor_number === 0) || sorted[0];
        set({ selectedFloor: ground });
        // Fetch devices/alerts for auto-selected floor
        get().fetchDevicesForFloor(ground.id);
        get().fetchAlertsForFloor(ground.id);
      }
    } catch (error) {
      console.error('Failed to load floor plans:', error);
    }
  },

  selectFloor: (floor) => {
    set({ selectedFloor: floor, selectedDevice: null });
    if (floor) {
      get().fetchDevicesForFloor(floor.id);
      get().fetchAlertsForFloor(floor.id);
    } else {
      set({ devices: [], alerts: [] });
    }
  },

  fetchDevicesForFloor: async (floorPlanId) => {
    set({ isLoadingDevices: true });
    try {
      const response = await iotDevicesApi.list({
        floor_plan_id: floorPlanId,
        page_size: 100,
      });
      set({ devices: response.items, isLoadingDevices: false });
    } catch (error) {
      console.error('Failed to fetch devices:', error);
      set({ devices: [], isLoadingDevices: false });
    }
  },

  fetchAlertsForFloor: async (floorPlanId) => {
    set({ isLoadingAlerts: true });
    try {
      const response = await soundAlertsApi.getFloorAlerts(floorPlanId, {
        page_size: 50,
      });
      set({ alerts: response.items, isLoadingAlerts: false });
    } catch (error) {
      console.error('Failed to fetch floor alerts:', error);
      set({ alerts: [], isLoadingAlerts: false });
    }
  },

  fetchBuildingAlerts: async (buildingId) => {
    try {
      const countData = await soundAlertsApi.getBuildingAlertCount(buildingId);
      set({ alertCount: countData.active_alert_count });
    } catch {
      // Non-critical, ignore
    }
  },

  setSelectedDevice: (device) => set({ selectedDevice: device }),

  enterPlacementMode: (deviceId) => {
    set({ isPlacementMode: true, placementDeviceId: deviceId });
  },

  exitPlacementMode: () => {
    set({ isPlacementMode: false, placementDeviceId: null });
  },

  placeDevice: async (deviceId, posX, posY, floorPlanId) => {
    try {
      const updated = await iotDevicesApi.updatePosition(deviceId, {
        position_x: posX,
        position_y: posY,
        floor_plan_id: floorPlanId,
      });
      set((state) => ({
        devices: state.devices.map((d) => (d.id === deviceId ? updated : d)),
        isPlacementMode: false,
        placementDeviceId: null,
        selectedDevice: updated,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to place device',
      });
      throw error;
    }
  },

  addFloorPlan: (floorPlan) => {
    set((state) => ({
      floorPlans: [...state.floorPlans, floorPlan].sort((a, b) => a.floor_number - b.floor_number),
      selectedFloor: floorPlan,
    }));
  },

  reset: () => set(initialState),

  clearError: () => set({ error: null }),
}));
