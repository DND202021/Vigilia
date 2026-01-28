/**
 * Marker Store (Zustand)
 *
 * Manages state for floor plan marker editing: markers data, selection,
 * editing mode, dirty state tracking, and persistence to the backend.
 */

import { create } from 'zustand';
import { buildingsApi } from '../services/api';
import type { FloorKeyLocation } from '../types';

/** Extended FloorKeyLocation with a unique ID for local editing. */
export interface MarkerWithId extends FloorKeyLocation {
  id: string;
}

interface MarkerStore {
  // State
  markers: MarkerWithId[];
  selectedMarkerId: string | null;
  isEditing: boolean;
  isDirty: boolean;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  currentFloorPlanId: string | null;

  // Actions
  loadMarkers: (floorPlanId: string) => Promise<void>;
  addMarker: (marker: Omit<MarkerWithId, 'id'>) => void;
  updateMarker: (id: string, updates: Partial<FloorKeyLocation>) => void;
  deleteMarker: (id: string) => void;
  selectMarker: (id: string | null) => void;
  setEditing: (enabled: boolean) => void;
  saveMarkers: () => Promise<void>;
  resetState: () => void;

  // Computed helpers
  getSelectedMarker: () => MarkerWithId | null;
}

const initialState = {
  markers: [] as MarkerWithId[],
  selectedMarkerId: null as string | null,
  isEditing: false,
  isDirty: false,
  isLoading: false,
  isSaving: false,
  error: null as string | null,
  currentFloorPlanId: null as string | null,
};

/**
 * Converts a FloorKeyLocation (without id) to a MarkerWithId by generating a UUID.
 */
const toMarkerWithId = (location: FloorKeyLocation): MarkerWithId => ({
  ...location,
  id: crypto.randomUUID(),
});

/**
 * Converts a MarkerWithId back to a FloorKeyLocation format for API saving.
 * Ensures x and y are numbers (defaults to 0 if undefined).
 */
const toFloorKeyLocation = (marker: MarkerWithId): { type: string; name: string; x: number; y: number; description?: string } => ({
  type: marker.type,
  name: marker.name,
  x: marker.x ?? 0,
  y: marker.y ?? 0,
  description: marker.description,
});

export const useMarkerStore = create<MarkerStore>((set, get) => ({
  ...initialState,

  loadMarkers: async (floorPlanId) => {
    set({ isLoading: true, error: null, currentFloorPlanId: floorPlanId });
    try {
      // Get the floor plan which contains key_locations
      // We need the building ID to fetch floor plans, but the API has a direct endpoint
      // Using the PATCH endpoint pattern, we can infer we need to fetch floor plan data
      // The buildingsApi.getFloorPlans requires buildingId, so we'll need to work around this
      // For now, we'll fetch via the floor plan locations endpoint indirectly

      // Since we don't have a direct getFloorPlan(id) method, we'll reset and let
      // the component pass in initial markers, or we fetch from a parent context.
      // However, based on the API structure, let's add a reasonable approach:
      // The floor plan data comes from buildingsApi.getFloorPlans which returns FloorPlan[]
      // The caller should have access to the floor plan data already.

      // For a cleaner implementation, we'll accept that loadMarkers may need the floor plan
      // data passed differently. Let's implement a pattern where we can load from API
      // or accept initial data. For now, reset markers for the new floor plan.

      // Note: In practice, the component using this store will likely have the floor plan
      // data already and can initialize markers directly. This method provides a reset point.
      set({
        markers: [],
        selectedMarkerId: null,
        isDirty: false,
        isLoading: false,
        isEditing: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load markers',
        isLoading: false,
      });
    }
  },

  addMarker: (marker) => {
    const newMarker: MarkerWithId = {
      ...marker,
      id: crypto.randomUUID(),
    };

    set((state) => ({
      markers: [...state.markers, newMarker],
      isDirty: true,
      selectedMarkerId: newMarker.id,
    }));
  },

  updateMarker: (id, updates) => {
    set((state) => ({
      markers: state.markers.map((marker) =>
        marker.id === id ? { ...marker, ...updates } : marker
      ),
      isDirty: true,
    }));
  },

  deleteMarker: (id) => {
    set((state) => ({
      markers: state.markers.filter((marker) => marker.id !== id),
      selectedMarkerId: state.selectedMarkerId === id ? null : state.selectedMarkerId,
      isDirty: true,
    }));
  },

  selectMarker: (id) => {
    set({ selectedMarkerId: id });
  },

  setEditing: (enabled) => {
    set({ isEditing: enabled });
    // Deselect marker when exiting edit mode
    if (!enabled) {
      set({ selectedMarkerId: null });
    }
  },

  saveMarkers: async () => {
    const { currentFloorPlanId, markers } = get();

    if (!currentFloorPlanId) {
      set({ error: 'No floor plan selected' });
      return;
    }

    set({ isSaving: true, error: null });

    try {
      // Convert markers to FloorKeyLocation format (strip IDs)
      const keyLocations = markers.map(toFloorKeyLocation);

      // Save to the API
      await buildingsApi.updateFloorPlanLocations(currentFloorPlanId, {
        key_locations: keyLocations,
      });

      set({
        isDirty: false,
        isSaving: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to save markers',
        isSaving: false,
      });
      throw error;
    }
  },

  resetState: () => {
    set(initialState);
  },

  getSelectedMarker: () => {
    const { markers, selectedMarkerId } = get();
    if (!selectedMarkerId) return null;
    return markers.find((marker) => marker.id === selectedMarkerId) || null;
  },
}));

/**
 * Helper function to initialize markers from a FloorPlan's key_locations.
 * Call this when you have the floor plan data and want to populate the store.
 */
export const initializeMarkersFromFloorPlan = (
  floorPlanId: string,
  keyLocations: FloorKeyLocation[] | undefined
): void => {
  const markers = (keyLocations || []).map(toMarkerWithId);
  useMarkerStore.setState({
    markers,
    currentFloorPlanId: floorPlanId,
    selectedMarkerId: null,
    isEditing: false,
    isDirty: false,
    isLoading: false,
    isSaving: false,
    error: null,
  });
};
