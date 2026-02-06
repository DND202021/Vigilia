/**
 * Device Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useDeviceStore } from '../stores/deviceStore';
import { iotDevicesApi } from '../services/api';
import type { IoTDevice } from '../types';

// Mock API
vi.mock('../services/api', () => ({
  iotDevicesApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updatePosition: vi.fn(),
  },
}));

describe('useDeviceStore', () => {
  const mockDevice: IoTDevice = {
    id: 'device-1',
    name: 'Camera 101',
    device_type: 'camera',
    status: 'online',
    building_id: 'building-1',
    floor_plan_id: 'floor-1',
    position_x: 100,
    position_y: 200,
    connection_string: 'http://camera-101.local',
    config: { resolution: '1080p' },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    // Reset store state
    useDeviceStore.setState({
      devices: [],
      selectedDevice: null,
      totalDevices: 0,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('fetchDevices', () => {
    it('should fetch devices and update state', async () => {
      const mockResponse = {
        items: [mockDevice],
        total: 1,
        page: 1,
        page_size: 20,
      };

      vi.mocked(iotDevicesApi.list).mockResolvedValueOnce(mockResponse);

      await useDeviceStore.getState().fetchDevices({ building_id: 'building-1' });

      expect(iotDevicesApi.list).toHaveBeenCalledWith({ building_id: 'building-1' });
      expect(useDeviceStore.getState().devices).toEqual([mockDevice]);
      expect(useDeviceStore.getState().totalDevices).toBe(1);
      expect(useDeviceStore.getState().isLoading).toBe(false);
      expect(useDeviceStore.getState().error).toBeNull();
    });

    it('should handle fetch error', async () => {
      vi.mocked(iotDevicesApi.list).mockRejectedValueOnce(new Error('Network error'));

      await useDeviceStore.getState().fetchDevices();

      expect(useDeviceStore.getState().devices).toEqual([]);
      expect(useDeviceStore.getState().isLoading).toBe(false);
      expect(useDeviceStore.getState().error).toBe('Network error');
    });
  });

  describe('fetchDevice', () => {
    it('should fetch a single device and set as selected', async () => {
      vi.mocked(iotDevicesApi.get).mockResolvedValueOnce(mockDevice);

      await useDeviceStore.getState().fetchDevice('device-1');

      expect(iotDevicesApi.get).toHaveBeenCalledWith('device-1');
      expect(useDeviceStore.getState().selectedDevice).toEqual(mockDevice);
      expect(useDeviceStore.getState().isLoading).toBe(false);
    });

    it('should handle fetch error', async () => {
      vi.mocked(iotDevicesApi.get).mockRejectedValueOnce(new Error('Not found'));

      await useDeviceStore.getState().fetchDevice('device-1');

      expect(useDeviceStore.getState().selectedDevice).toBeNull();
      expect(useDeviceStore.getState().error).toBe('Not found');
    });
  });

  describe('createDevice', () => {
    it('should create a device and add to list', async () => {
      const createData = {
        name: 'New Camera',
        device_type: 'camera' as const,
        building_id: 'building-1',
        connection_string: 'http://camera.local',
      };

      vi.mocked(iotDevicesApi.create).mockResolvedValueOnce(mockDevice);

      const result = await useDeviceStore.getState().createDevice(createData);

      expect(iotDevicesApi.create).toHaveBeenCalledWith(createData);
      expect(result).toEqual(mockDevice);
      expect(useDeviceStore.getState().devices).toEqual([mockDevice]);
      expect(useDeviceStore.getState().totalDevices).toBe(1);
    });

    it('should handle create error', async () => {
      const createData = {
        name: 'New Camera',
        device_type: 'camera' as const,
        building_id: 'building-1',
        connection_string: 'http://camera.local',
      };

      vi.mocked(iotDevicesApi.create).mockRejectedValueOnce(new Error('Validation error'));

      await expect(useDeviceStore.getState().createDevice(createData)).rejects.toThrow();

      expect(useDeviceStore.getState().devices).toEqual([]);
      expect(useDeviceStore.getState().error).toBe('Validation error');
    });
  });

  describe('updateDevice', () => {
    it('should update a device in the list', async () => {
      useDeviceStore.setState({ devices: [mockDevice] });

      const updatedDevice = { ...mockDevice, name: 'Updated Camera' };
      vi.mocked(iotDevicesApi.update).mockResolvedValueOnce(updatedDevice);

      await useDeviceStore.getState().updateDevice('device-1', { name: 'Updated Camera' });

      expect(iotDevicesApi.update).toHaveBeenCalledWith('device-1', { name: 'Updated Camera' });
      expect(useDeviceStore.getState().devices[0].name).toBe('Updated Camera');
    });

    it('should update selectedDevice if it matches', async () => {
      useDeviceStore.setState({ devices: [mockDevice], selectedDevice: mockDevice });

      const updatedDevice = { ...mockDevice, status: 'offline' as const };
      vi.mocked(iotDevicesApi.update).mockResolvedValueOnce(updatedDevice);

      await useDeviceStore.getState().updateDevice('device-1', { status: 'offline' });

      expect(useDeviceStore.getState().selectedDevice?.status).toBe('offline');
    });

    it('should handle update error', async () => {
      useDeviceStore.setState({ devices: [mockDevice] });

      vi.mocked(iotDevicesApi.update).mockRejectedValueOnce(new Error('Update failed'));

      await expect(useDeviceStore.getState().updateDevice('device-1', { name: 'New Name' })).rejects.toThrow();

      expect(useDeviceStore.getState().error).toBe('Update failed');
    });
  });

  describe('deleteDevice', () => {
    it('should delete a device from the list', async () => {
      useDeviceStore.setState({ devices: [mockDevice], totalDevices: 1 });

      vi.mocked(iotDevicesApi.delete).mockResolvedValueOnce(undefined);

      await useDeviceStore.getState().deleteDevice('device-1');

      expect(iotDevicesApi.delete).toHaveBeenCalledWith('device-1');
      expect(useDeviceStore.getState().devices).toEqual([]);
      expect(useDeviceStore.getState().totalDevices).toBe(0);
    });

    it('should clear selectedDevice if it matches deleted device', async () => {
      useDeviceStore.setState({
        devices: [mockDevice],
        selectedDevice: mockDevice,
        totalDevices: 1,
      });

      vi.mocked(iotDevicesApi.delete).mockResolvedValueOnce(undefined);

      await useDeviceStore.getState().deleteDevice('device-1');

      expect(useDeviceStore.getState().selectedDevice).toBeNull();
    });

    it('should handle delete error', async () => {
      useDeviceStore.setState({ devices: [mockDevice] });

      vi.mocked(iotDevicesApi.delete).mockRejectedValueOnce(new Error('Delete failed'));

      await expect(useDeviceStore.getState().deleteDevice('device-1')).rejects.toThrow();

      expect(useDeviceStore.getState().error).toBe('Delete failed');
      expect(useDeviceStore.getState().devices).toEqual([mockDevice]); // Not deleted
    });
  });

  describe('updatePosition', () => {
    it('should update device position', async () => {
      useDeviceStore.setState({ devices: [mockDevice] });

      const updatedDevice = { ...mockDevice, position_x: 300, position_y: 400 };
      vi.mocked(iotDevicesApi.updatePosition).mockResolvedValueOnce(updatedDevice);

      await useDeviceStore.getState().updatePosition('device-1', {
        floor_plan_id: 'floor-1',
        position_x: 300,
        position_y: 400,
      });

      expect(useDeviceStore.getState().devices[0].position_x).toBe(300);
      expect(useDeviceStore.getState().devices[0].position_y).toBe(400);
    });
  });

  describe('setSelectedDevice', () => {
    it('should set the selected device', () => {
      useDeviceStore.getState().setSelectedDevice(mockDevice);

      expect(useDeviceStore.getState().selectedDevice).toEqual(mockDevice);
    });

    it('should clear the selected device', () => {
      useDeviceStore.setState({ selectedDevice: mockDevice });

      useDeviceStore.getState().setSelectedDevice(null);

      expect(useDeviceStore.getState().selectedDevice).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear the error state', () => {
      useDeviceStore.setState({ error: 'Some error' });

      useDeviceStore.getState().clearError();

      expect(useDeviceStore.getState().error).toBeNull();
    });
  });

  describe('handleDeviceStatusUpdate', () => {
    it('should update device status via WebSocket event', () => {
      useDeviceStore.setState({ devices: [mockDevice] });

      useDeviceStore.getState().handleDeviceStatusUpdate({
        device_id: 'device-1',
        status: 'offline',
      });

      expect(useDeviceStore.getState().devices[0].status).toBe('offline');
    });

    it('should update last_seen for online status', () => {
      useDeviceStore.setState({ devices: [mockDevice] });

      useDeviceStore.getState().handleDeviceStatusUpdate({
        device_id: 'device-1',
        status: 'online',
      });

      const device = useDeviceStore.getState().devices[0];
      expect(device.status).toBe('online');
      expect(device.last_seen).toBeDefined();
    });

    it('should update selectedDevice status if it matches', () => {
      useDeviceStore.setState({ devices: [mockDevice], selectedDevice: mockDevice });

      useDeviceStore.getState().handleDeviceStatusUpdate({
        device_id: 'device-1',
        status: 'offline',
      });

      expect(useDeviceStore.getState().selectedDevice?.status).toBe('offline');
    });
  });
});
