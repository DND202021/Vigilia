/**
 * Marker Store (Zustand)
 *
 * Manages state for floor plan marker editing: markers data, selection,
 * editing mode, dirty state tracking, and persistence to the backend.
 */

import { create } from 'zustand';
import { buildingsApi } from '../services/api';
import type { FloorKeyLocation, OptimisticMarker, MarkerConflict, ConflictResolutionStrategy } from '../types';

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

  // Real-time collaboration state
  clientId: string;
  optimisticMarkers: OptimisticMarker[];
  conflicts: MarkerConflict[];
  conflictResolutionStrategy: ConflictResolutionStrategy;

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

  // Real-time collaboration actions
  generateClientId: () => string;
  addOptimisticMarker: (marker: FloorKeyLocation) => OptimisticMarker;
  confirmOptimisticMarker: (clientId: string, serverId: string) => void;
  rollbackOptimisticMarker: (clientId: string) => void;
  handleRemoteMarkerAdded: (marker: FloorKeyLocation, userId: string, clientId?: string) => void;
  handleRemoteMarkerUpdated: (markerId: string, updates: Partial<FloorKeyLocation>, userId: string, clientId?: string) => void;
  handleRemoteMarkerDeleted: (markerId: string, userId: string) => void;
  addConflict: (conflict: MarkerConflict) => void;
  resolveConflict: (markerId: string, strategy: ConflictResolutionStrategy, useServerVersion?: boolean) => void;
  clearConflicts: () => void;
  setConflictResolutionStrategy: (strategy: ConflictResolutionStrategy) => void;
}

/**
 * Generates a unique client ID for this session.
 */
const generateClientId = () => `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

const initialState = {
  markers: [] as MarkerWithId[],
  selectedMarkerId: null as string | null,
  isEditing: false,
  isDirty: false,
  isLoading: false,
  isSaving: false,
  error: null as string | null,
  currentFloorPlanId: null as string | null,
  // Real-time collaboration state
  clientId: generateClientId(),
  optimisticMarkers: [] as OptimisticMarker[],
  conflicts: [] as MarkerConflict[],
  conflictResolutionStrategy: 'server_authoritative' as ConflictResolutionStrategy,
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

  // ============================================================================
  // Real-time Collaboration Actions
  // ============================================================================

  generateClientId: () => {
    const newClientId = generateClientId();
    set({ clientId: newClientId });
    return newClientId;
  },

  addOptimisticMarker: (marker: FloorKeyLocation): OptimisticMarker => {
    const { clientId } = get();
    const optimisticMarker: OptimisticMarker = {
      ...marker,
      client_id: clientId,
      is_optimistic: true,
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      optimisticMarkers: [...state.optimisticMarkers, optimisticMarker],
    }));

    return optimisticMarker;
  },

  confirmOptimisticMarker: (markerClientId: string, serverId: string) => {
    set((state) => {
      // Find the optimistic marker
      const optimisticMarker = state.optimisticMarkers.find(
        (m) => m.client_id === markerClientId
      );

      if (!optimisticMarker) {
        return state;
      }

      // Convert to confirmed marker with server ID
      const confirmedMarker: MarkerWithId = {
        ...optimisticMarker,
        id: serverId,
      };

      return {
        // Add to confirmed markers
        markers: [...state.markers, confirmedMarker],
        // Remove from optimistic markers
        optimisticMarkers: state.optimisticMarkers.filter(
          (m) => m.client_id !== markerClientId
        ),
        isDirty: true,
      };
    });
  },

  rollbackOptimisticMarker: (markerClientId: string) => {
    set((state) => ({
      optimisticMarkers: state.optimisticMarkers.filter(
        (m) => m.client_id !== markerClientId
      ),
    }));
  },

  handleRemoteMarkerAdded: (marker: FloorKeyLocation, _userId: string, remoteClientId?: string) => {
    const { clientId, optimisticMarkers } = get();

    // Ignore if this is our own marker (already handled via optimistic update)
    if (remoteClientId && remoteClientId === clientId) {
      return;
    }

    // Check if we have an optimistic marker that matches (in case of race condition)
    const matchingOptimistic = optimisticMarkers.find(
      (m) => m.client_id === remoteClientId
    );

    if (matchingOptimistic) {
      // This was our marker, confirmed by server via another path
      return;
    }

    // Add the remote marker
    const newMarker: MarkerWithId = {
      ...marker,
      id: marker.id || crypto.randomUUID(),
    };

    set((state) => ({
      markers: [...state.markers, newMarker],
    }));
  },

  handleRemoteMarkerUpdated: (markerId: string, updates: Partial<FloorKeyLocation>, _userId: string, remoteClientId?: string) => {
    const { clientId, markers, conflictResolutionStrategy, currentFloorPlanId } = get();

    // Ignore if this is our own update
    if (remoteClientId && remoteClientId === clientId) {
      return;
    }

    // Find the local marker
    const localMarker = markers.find((m) => m.id === markerId);
    if (!localMarker) {
      // Marker doesn't exist locally, nothing to update
      return;
    }

    // Check for conflicts: if local marker was modified (isDirty) and values differ
    const hasConflict = Object.keys(updates).some((key) => {
      const updateKey = key as keyof FloorKeyLocation;
      const localValue = localMarker[updateKey];
      const remoteValue = updates[updateKey];
      // Conflict if local has a different value than the remote update
      return localValue !== undefined && localValue !== remoteValue;
    });

    if (hasConflict && get().isDirty) {
      // Create a conflict record
      const conflict: MarkerConflict = {
        marker_id: markerId,
        floor_plan_id: currentFloorPlanId || '',
        local_version: { ...localMarker },
        server_version: { ...localMarker, ...updates },
        conflict_type: updates.x !== undefined || updates.y !== undefined ? 'position' : 'properties',
        detected_at: new Date().toISOString(),
        resolved: false,
      };

      set((state) => ({
        conflicts: [...state.conflicts, conflict],
      }));

      // Apply resolution based on strategy
      if (conflictResolutionStrategy === 'server_authoritative' || conflictResolutionStrategy === 'last_write_wins') {
        // Apply server version
        set((state) => ({
          markers: state.markers.map((m) =>
            m.id === markerId ? { ...m, ...updates } : m
          ),
        }));
      } else if (conflictResolutionStrategy === 'local_wins') {
        // Keep local version, do nothing
      }
      // 'manual' strategy: don't auto-resolve, let user decide
    } else {
      // No conflict, apply the update
      set((state) => ({
        markers: state.markers.map((m) =>
          m.id === markerId ? { ...m, ...updates } : m
        ),
      }));
    }
  },

  handleRemoteMarkerDeleted: (markerId: string, _userId: string) => {
    const { markers, selectedMarkerId, currentFloorPlanId, conflictResolutionStrategy } = get();

    // Find the local marker
    const localMarker = markers.find((m) => m.id === markerId);
    if (!localMarker) {
      // Already deleted locally
      return;
    }

    // If we have local changes to this marker, create a deletion conflict
    if (get().isDirty) {
      const conflict: MarkerConflict = {
        marker_id: markerId,
        floor_plan_id: currentFloorPlanId || '',
        local_version: { ...localMarker },
        server_version: { ...localMarker }, // Server deleted this
        conflict_type: 'deletion',
        detected_at: new Date().toISOString(),
        resolved: false,
      };

      set((state) => ({
        conflicts: [...state.conflicts, conflict],
      }));

      // Apply resolution based on strategy
      if (conflictResolutionStrategy === 'server_authoritative' || conflictResolutionStrategy === 'last_write_wins') {
        // Accept deletion
        set((state) => ({
          markers: state.markers.filter((m) => m.id !== markerId),
          selectedMarkerId: selectedMarkerId === markerId ? null : selectedMarkerId,
        }));
      }
      // 'local_wins' or 'manual': keep the marker
    } else {
      // No conflict, remove the marker
      set((state) => ({
        markers: state.markers.filter((m) => m.id !== markerId),
        selectedMarkerId: selectedMarkerId === markerId ? null : selectedMarkerId,
      }));
    }
  },

  addConflict: (conflict: MarkerConflict) => {
    set((state) => ({
      conflicts: [...state.conflicts, conflict],
    }));
  },

  resolveConflict: (markerId: string, _strategy: ConflictResolutionStrategy, useServerVersion: boolean = true) => {
    const { conflicts } = get();

    // Find the conflict
    const conflict = conflicts.find((c) => c.marker_id === markerId && !c.resolved);
    if (!conflict) {
      return;
    }

    if (conflict.conflict_type === 'deletion') {
      if (useServerVersion) {
        // Accept deletion
        set((state) => ({
          markers: state.markers.filter((m) => m.id !== markerId),
          selectedMarkerId: state.selectedMarkerId === markerId ? null : state.selectedMarkerId,
          conflicts: state.conflicts.map((c) =>
            c.marker_id === markerId ? { ...c, resolved: true } : c
          ),
        }));
      } else {
        // Keep local version
        set((state) => ({
          conflicts: state.conflicts.map((c) =>
            c.marker_id === markerId ? { ...c, resolved: true } : c
          ),
        }));
      }
    } else {
      // Position or property conflict
      const versionToUse = useServerVersion ? conflict.server_version : conflict.local_version;

      set((state) => ({
        markers: state.markers.map((m) =>
          m.id === markerId ? { ...m, ...versionToUse } : m
        ),
        conflicts: state.conflicts.map((c) =>
          c.marker_id === markerId ? { ...c, resolved: true } : c
        ),
      }));
    }
  },

  clearConflicts: () => {
    set({ conflicts: [] });
  },

  setConflictResolutionStrategy: (strategy: ConflictResolutionStrategy) => {
    set({ conflictResolutionStrategy: strategy });
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
