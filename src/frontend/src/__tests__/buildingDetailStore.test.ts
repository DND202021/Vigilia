/**
 * Building Detail Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useBuildingDetailStore } from '../stores/buildingDetailStore';
import { buildingsApi, iotDevicesApi, soundAlertsApi } from '../services/api';
import type { Building, FloorPlan, IoTDevice } from '../types';

// Mock API
vi.mock('../services/api', () => ({
  buildingsApi: {
    get: vi.fn(),
    getFloorPlans: vi.fn(),
  },
  iotDevicesApi: {
    list: vi.fn(),
    updatePosition: vi.fn(),
  },
  soundAlertsApi: {
    getFloorAlerts: vi.fn(),
    getBuildingAlertCount: vi.fn(),
  },
}));

const mockBuilding: Building = {
  id: 'bldg-1',
  name: 'Test Building',
  building_type: 'commercial',
  address: '123 Main St',
  latitude: 45.5,
  longitude: -73.5,
  agency_id: 'agency-1',
  total_floors: 5,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockFloorPlan: FloorPlan = {
  id: 'floor-1',
  building_id: 'bldg-1',
  floor_number: 0,
  floor_name: 'Ground Floor',
  plan_file_url: '/floor-plans/ground.png',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockDevice: IoTDevice = {
  id: 'dev-1',
  device_type: 'microphone',
  name: 'Mic 1',
  status: 'active',
  building_id: 'bldg-1',
  floor_plan_id: 'floor-1',
  position_x: 100,
  position_y: 200,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('useBuildingDetailStore', () => {
  beforeEach(() => {
    useBuildingDetailStore.getState().reset();
    vi.clearAllMocks();
  });

  describe('fetchBuilding', () => {
    it('should fetch building successfully', async () => {
      vi.mocked(buildingsApi.get).mockResolvedValue(mockBuilding);

      await useBuildingDetailStore.getState().fetchBuilding('bldg-1');

      const state = useBuildingDetailStore.getState();
      expect(state.building).toEqual(mockBuilding);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(buildingsApi.get).toHaveBeenCalledWith('bldg-1');
    });

    it('should handle fetch error', async () => {
      vi.mocked(buildingsApi.get).mockRejectedValue(new Error('Not found'));

      await useBuildingDetailStore.getState().fetchBuilding('bldg-999');

      const state = useBuildingDetailStore.getState();
      expect(state.building).toBeNull();
      expect(state.error).toBe('Not found');
      expect(state.isLoading).toBe(false);
    });
  });

  describe('fetchFloorPlans', () => {
    it('should fetch and sort floor plans', async () => {
      const floor1 = { ...mockFloorPlan, id: 'floor-1', floor_number: 1 };
      const floor0 = { ...mockFloorPlan, id: 'floor-0', floor_number: 0 };

      vi.mocked(buildingsApi.getFloorPlans).mockResolvedValue([floor1, floor0]);

      await useBuildingDetailStore.getState().fetchFloorPlans('bldg-1');

      const state = useBuildingDetailStore.getState();
      expect(state.floorPlans).toHaveLength(2);
      expect(state.floorPlans[0].floor_number).toBe(0); // Ground floor first
      expect(state.floorPlans[1].floor_number).toBe(1);
    });

    it('should auto-select ground floor', async () => {
      const floor0 = { ...mockFloorPlan, floor_number: 0 };
      const floor1 = { ...mockFloorPlan, id: 'floor-1', floor_number: 1 };

      vi.mocked(buildingsApi.getFloorPlans).mockResolvedValue([floor1, floor0]);
      vi.mocked(iotDevicesApi.list).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100, total_pages: 0 });
      vi.mocked(soundAlertsApi.getFloorAlerts).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50, total_pages: 0 });

      await useBuildingDetailStore.getState().fetchFloorPlans('bldg-1');

      const state = useBuildingDetailStore.getState();
      expect(state.selectedFloor?.floor_number).toBe(0);
    });

    it('should handle network error gracefully', async () => {
      vi.mocked(buildingsApi.getFloorPlans).mockRejectedValue(new Error('Network Error'));

      await useBuildingDetailStore.getState().fetchFloorPlans('bldg-1');

      const state = useBuildingDetailStore.getState();
      expect(state.error).toBe('Unable to connect to server. Please check your connection.');
    });
  });

  describe('selectFloor', () => {
    it('should select floor and fetch devices/alerts', async () => {
      vi.mocked(iotDevicesApi.list).mockResolvedValue({ items: [mockDevice], total: 1, page: 1, page_size: 100, total_pages: 1 });
      vi.mocked(soundAlertsApi.getFloorAlerts).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50, total_pages: 0 });

      useBuildingDetailStore.getState().selectFloor(mockFloorPlan);

      // Allow async operations to complete
      await new Promise(resolve => setTimeout(resolve, 0));

      const state = useBuildingDetailStore.getState();
      expect(state.selectedFloor).toEqual(mockFloorPlan);
      expect(iotDevicesApi.list).toHaveBeenCalledWith({ floor_plan_id: 'floor-1', page_size: 100 });
    });

    it('should clear devices when floor is null', () => {
      useBuildingDetailStore.setState({
        selectedFloor: mockFloorPlan,
        devices: [mockDevice],
      });

      useBuildingDetailStore.getState().selectFloor(null);

      const state = useBuildingDetailStore.getState();
      expect(state.selectedFloor).toBeNull();
      expect(state.devices).toEqual([]);
    });
  });

  describe('fetchDevicesForFloor', () => {
    it('should fetch devices for floor', async () => {
      vi.mocked(iotDevicesApi.list).mockResolvedValue({
        items: [mockDevice],
        total: 1,
        page: 1,
        page_size: 100,
        total_pages: 1,
      });

      await useBuildingDetailStore.getState().fetchDevicesForFloor('floor-1');

      const state = useBuildingDetailStore.getState();
      expect(state.devices).toEqual([mockDevice]);
      expect(state.isLoadingDevices).toBe(false);
    });

    it('should handle network error', async () => {
      vi.mocked(iotDevicesApi.list).mockRejectedValue(new Error('Network Error'));

      await useBuildingDetailStore.getState().fetchDevicesForFloor('floor-1');

      const state = useBuildingDetailStore.getState();
      expect(state.error).toBe('Unable to load devices. Server is unavailable.');
      expect(state.devices).toEqual([]);
    });
  });

  describe('device placement', () => {
    it('should enter placement mode', () => {
      useBuildingDetailStore.getState().enterPlacementMode('dev-1');

      const state = useBuildingDetailStore.getState();
      expect(state.isPlacementMode).toBe(true);
      expect(state.placementDeviceId).toBe('dev-1');
    });

    it('should exit placement mode', () => {
      useBuildingDetailStore.setState({ isPlacementMode: true, placementDeviceId: 'dev-1' });

      useBuildingDetailStore.getState().exitPlacementMode();

      const state = useBuildingDetailStore.getState();
      expect(state.isPlacementMode).toBe(false);
      expect(state.placementDeviceId).toBeNull();
    });

    it('should place device and update state', async () => {
      const updatedDevice = { ...mockDevice, position_x: 150, position_y: 250 };

      useBuildingDetailStore.setState({
        devices: [mockDevice],
      });

      vi.mocked(iotDevicesApi.updatePosition).mockResolvedValue(updatedDevice);

      await useBuildingDetailStore.getState().placeDevice('dev-1', 150, 250, 'floor-1');

      const state = useBuildingDetailStore.getState();
      expect(state.devices[0].position_x).toBe(150);
      expect(state.devices[0].position_y).toBe(250);
      expect(state.isPlacementMode).toBe(false);
      expect(state.selectedDevice).toEqual(updatedDevice);
    });

    it('should handle placement error', async () => {
      vi.mocked(iotDevicesApi.updatePosition).mockRejectedValue(new Error('Position update failed'));

      await expect(
        useBuildingDetailStore.getState().placeDevice('dev-1', 150, 250, 'floor-1')
      ).rejects.toThrow('Position update failed');

      const state = useBuildingDetailStore.getState();
      expect(state.error).toBe('Position update failed');
    });
  });

  describe('addFloorPlan', () => {
    it('should add floor plan and sort list', () => {
      const floor0 = { ...mockFloorPlan, floor_number: 0 };
      const floor2 = { ...mockFloorPlan, id: 'floor-2', floor_number: 2 };

      useBuildingDetailStore.setState({ floorPlans: [floor0] });

      useBuildingDetailStore.getState().addFloorPlan(floor2);

      const state = useBuildingDetailStore.getState();
      expect(state.floorPlans).toHaveLength(2);
      expect(state.floorPlans[0].floor_number).toBe(0);
      expect(state.floorPlans[1].floor_number).toBe(2);
      expect(state.selectedFloor).toEqual(floor2);
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', () => {
      useBuildingDetailStore.setState({
        building: mockBuilding,
        floorPlans: [mockFloorPlan],
        devices: [mockDevice],
        error: 'Some error',
      });

      useBuildingDetailStore.getState().reset();

      const state = useBuildingDetailStore.getState();
      expect(state.building).toBeNull();
      expect(state.floorPlans).toEqual([]);
      expect(state.devices).toEqual([]);
      expect(state.error).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useBuildingDetailStore.setState({ error: 'Some error' });
      useBuildingDetailStore.getState().clearError();

      const state = useBuildingDetailStore.getState();
      expect(state.error).toBeNull();
    });
  });
});
