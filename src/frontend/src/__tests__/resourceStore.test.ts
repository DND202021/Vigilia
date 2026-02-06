/**
 * Resource Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useResourceStore } from '../stores/resourceStore';
import { resourcesApi } from '../services/api';
import type { Resource } from '../types';

// Mock API
vi.mock('../services/api', () => ({
  resourcesApi: {
    list: vi.fn(),
    getAvailable: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    updateStatus: vi.fn(),
    updateLocation: vi.fn(),
  },
}));

const mockResource: Resource = {
  id: 'res-1',
  resource_type: 'vehicle',
  name: 'Engine 1',
  call_sign: 'E1',
  status: 'available',
  capabilities: ['fire', 'rescue'],
  agency_id: 'agency-1',
  last_status_update: new Date().toISOString(),
};

describe('useResourceStore', () => {
  beforeEach(() => {
    useResourceStore.setState({
      resources: [],
      availableResources: [],
      selectedResource: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('fetchResources', () => {
    it('should fetch resources successfully', async () => {
      const mockResponse = {
        items: [mockResource],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      };

      vi.mocked(resourcesApi.list).mockResolvedValue(mockResponse);

      await useResourceStore.getState().fetchResources();

      const state = useResourceStore.getState();
      expect(state.resources).toEqual([mockResource]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should handle fetch error', async () => {
      vi.mocked(resourcesApi.list).mockRejectedValue(new Error('Network error'));

      await useResourceStore.getState().fetchResources();

      const state = useResourceStore.getState();
      expect(state.error).toBe('Network error');
    });

    it('should pass filter params to API', async () => {
      vi.mocked(resourcesApi.list).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      });

      await useResourceStore.getState().fetchResources({ resource_type: 'vehicle', status: 'available' });

      expect(resourcesApi.list).toHaveBeenCalledWith({ resource_type: 'vehicle', status: 'available' });
    });
  });

  describe('fetchAvailableResources', () => {
    it('should fetch available resources', async () => {
      vi.mocked(resourcesApi.getAvailable).mockResolvedValue([mockResource]);

      await useResourceStore.getState().fetchAvailableResources();

      const state = useResourceStore.getState();
      expect(state.availableResources).toEqual([mockResource]);
    });

    it('should fetch available resources by type', async () => {
      vi.mocked(resourcesApi.getAvailable).mockResolvedValue([mockResource]);

      await useResourceStore.getState().fetchAvailableResources('vehicle');

      expect(resourcesApi.getAvailable).toHaveBeenCalledWith('vehicle');
    });

    it('should handle fetch error', async () => {
      vi.mocked(resourcesApi.getAvailable).mockRejectedValue(new Error('API error'));

      await useResourceStore.getState().fetchAvailableResources();

      const state = useResourceStore.getState();
      expect(state.error).toBe('API error');
    });
  });

  describe('fetchResource', () => {
    it('should fetch single resource and set as selected', async () => {
      vi.mocked(resourcesApi.get).mockResolvedValue(mockResource);

      await useResourceStore.getState().fetchResource('res-1');

      const state = useResourceStore.getState();
      expect(state.selectedResource).toEqual(mockResource);
      expect(resourcesApi.get).toHaveBeenCalledWith('res-1');
    });

    it('should handle fetch error', async () => {
      vi.mocked(resourcesApi.get).mockRejectedValue(new Error('Not found'));

      await useResourceStore.getState().fetchResource('res-999');

      const state = useResourceStore.getState();
      expect(state.error).toBe('Not found');
    });
  });

  describe('createResource', () => {
    it('should create resource and add to lists', async () => {
      const newResource = { ...mockResource, id: 'res-2' };
      vi.mocked(resourcesApi.create).mockResolvedValue(newResource);

      const result = await useResourceStore.getState().createResource({
        resource_type: 'vehicle',
        name: 'Engine 2',
        agency_id: 'agency-1',
      });

      expect(result).toEqual(newResource);

      const state = useResourceStore.getState();
      expect(state.resources).toContain(newResource);
      expect(state.availableResources).toContain(newResource);
    });

    it('should not add unavailable resource to available list', async () => {
      const newResource = { ...mockResource, id: 'res-2', status: 'dispatched' as const };
      vi.mocked(resourcesApi.create).mockResolvedValue(newResource);

      await useResourceStore.getState().createResource({
        resource_type: 'vehicle',
        name: 'Engine 2',
        agency_id: 'agency-1',
      });

      const state = useResourceStore.getState();
      expect(state.resources).toContain(newResource);
      expect(state.availableResources).toHaveLength(0);
    });

    it('should handle create error', async () => {
      vi.mocked(resourcesApi.create).mockRejectedValue(new Error('Validation error'));

      await expect(
        useResourceStore.getState().createResource({
          resource_type: 'vehicle',
          name: 'Invalid',
          agency_id: 'agency-1',
        })
      ).rejects.toThrow('Validation error');
    });
  });

  describe('updateResourceStatus', () => {
    it('should update status and manage available list', async () => {
      const resource = { ...mockResource, status: 'available' as const };
      const updatedResource = { ...mockResource, status: 'dispatched' as const };

      useResourceStore.setState({
        resources: [resource],
        availableResources: [resource],
      });

      vi.mocked(resourcesApi.updateStatus).mockResolvedValue(updatedResource);

      await useResourceStore.getState().updateResourceStatus('res-1', { status: 'dispatched' });

      const state = useResourceStore.getState();
      expect(state.resources[0].status).toBe('dispatched');
      expect(state.availableResources).toHaveLength(0);
    });

    it('should add to available list when status becomes available', async () => {
      const resource = { ...mockResource, status: 'dispatched' as const };
      const updatedResource = { ...mockResource, status: 'available' as const };

      useResourceStore.setState({
        resources: [resource],
        availableResources: [],
      });

      vi.mocked(resourcesApi.updateStatus).mockResolvedValue(updatedResource);

      await useResourceStore.getState().updateResourceStatus('res-1', { status: 'available' });

      const state = useResourceStore.getState();
      expect(state.availableResources).toContain(updatedResource);
    });

    it('should handle status update error', async () => {
      vi.mocked(resourcesApi.updateStatus).mockRejectedValue(new Error('Update failed'));

      await expect(
        useResourceStore.getState().updateResourceStatus('res-1', { status: 'dispatched' })
      ).rejects.toThrow('Update failed');
    });
  });

  describe('updateResourceLocation', () => {
    it('should update resource location', async () => {
      const updatedResource = { ...mockResource, latitude: 45.5, longitude: -73.5 };

      useResourceStore.setState({
        resources: [mockResource],
        availableResources: [mockResource],
      });

      vi.mocked(resourcesApi.updateLocation).mockResolvedValue(updatedResource);

      await useResourceStore.getState().updateResourceLocation('res-1', 45.5, -73.5);

      const state = useResourceStore.getState();
      expect(state.resources[0]).toEqual(updatedResource);
      expect(resourcesApi.updateLocation).toHaveBeenCalledWith('res-1', 45.5, -73.5);
    });

    it('should handle location update error', async () => {
      vi.mocked(resourcesApi.updateLocation).mockRejectedValue(new Error('Location failed'));

      await expect(
        useResourceStore.getState().updateResourceLocation('res-1', 45.5, -73.5)
      ).rejects.toThrow('Location failed');
    });
  });

  describe('setSelectedResource', () => {
    it('should set selected resource', () => {
      useResourceStore.getState().setSelectedResource(mockResource);

      const state = useResourceStore.getState();
      expect(state.selectedResource).toEqual(mockResource);
    });

    it('should clear selected resource', () => {
      useResourceStore.setState({ selectedResource: mockResource });
      useResourceStore.getState().setSelectedResource(null);

      const state = useResourceStore.getState();
      expect(state.selectedResource).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useResourceStore.setState({ error: 'Some error' });
      useResourceStore.getState().clearError();

      const state = useResourceStore.getState();
      expect(state.error).toBeNull();
    });
  });
});
