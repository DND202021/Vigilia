/**
 * Resource State Store (Zustand)
 */

import { create } from 'zustand';
import type { Resource, ResourceCreateRequest, ResourceStatusUpdate } from '../types';
import { resourcesApi } from '../services/api';

interface ResourceStore {
  resources: Resource[];
  availableResources: Resource[];
  selectedResource: Resource | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchResources: (params?: Record<string, unknown>) => Promise<void>;
  fetchAvailableResources: (resourceType?: string) => Promise<void>;
  fetchResource: (id: string) => Promise<void>;
  createResource: (data: ResourceCreateRequest) => Promise<Resource>;
  updateResourceStatus: (id: string, data: ResourceStatusUpdate) => Promise<void>;
  updateResourceLocation: (id: string, latitude: number, longitude: number) => Promise<void>;
  setSelectedResource: (resource: Resource | null) => void;
  clearError: () => void;

  // Real-time update handler
  handleResourceUpdate: (resource: Resource) => void;
}

export const useResourceStore = create<ResourceStore>((set) => ({
  resources: [],
  availableResources: [],
  selectedResource: null,
  isLoading: false,
  error: null,

  fetchResources: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await resourcesApi.list(params);
      set({ resources: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch resources',
        isLoading: false,
      });
    }
  },

  fetchAvailableResources: async (resourceType) => {
    set({ isLoading: true, error: null });
    try {
      const resources = await resourcesApi.getAvailable(resourceType);
      set({ availableResources: resources, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch available resources',
        isLoading: false,
      });
    }
  },

  fetchResource: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const resource = await resourcesApi.get(id);
      set({ selectedResource: resource, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch resource',
        isLoading: false,
      });
    }
  },

  createResource: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const resource = await resourcesApi.create(data);
      set((state) => ({
        resources: [resource, ...state.resources],
        availableResources:
          resource.status === 'available'
            ? [resource, ...state.availableResources]
            : state.availableResources,
        isLoading: false,
      }));
      return resource;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create resource',
        isLoading: false,
      });
      throw error;
    }
  },

  updateResourceStatus: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await resourcesApi.updateStatus(id, data);
      set((state) => ({
        resources: state.resources.map((r) => (r.id === id ? updated : r)),
        availableResources:
          updated.status === 'available'
            ? state.availableResources.some((r) => r.id === id)
              ? state.availableResources.map((r) => (r.id === id ? updated : r))
              : [updated, ...state.availableResources]
            : state.availableResources.filter((r) => r.id !== id),
        selectedResource: state.selectedResource?.id === id ? updated : state.selectedResource,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update resource status',
        isLoading: false,
      });
      throw error;
    }
  },

  updateResourceLocation: async (id, latitude, longitude) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await resourcesApi.updateLocation(id, latitude, longitude);
      set((state) => ({
        resources: state.resources.map((r) => (r.id === id ? updated : r)),
        availableResources: state.availableResources.map((r) => (r.id === id ? updated : r)),
        selectedResource: state.selectedResource?.id === id ? updated : state.selectedResource,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update resource location',
        isLoading: false,
      });
      throw error;
    }
  },

  setSelectedResource: (resource) => set({ selectedResource: resource }),

  clearError: () => set({ error: null }),

  handleResourceUpdate: (resource) => {
    set((state) => {
      const isAvailable = resource.status === 'available';

      return {
        resources: state.resources.some((r) => r.id === resource.id)
          ? state.resources.map((r) => (r.id === resource.id ? resource : r))
          : [resource, ...state.resources],
        availableResources: isAvailable
          ? state.availableResources.some((r) => r.id === resource.id)
            ? state.availableResources.map((r) => (r.id === resource.id ? resource : r))
            : [resource, ...state.availableResources]
          : state.availableResources.filter((r) => r.id !== resource.id),
        selectedResource:
          state.selectedResource?.id === resource.id ? resource : state.selectedResource,
      };
    });
  },
}));
