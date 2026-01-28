/**
 * Building Map Store (Zustand)
 *
 * Manages state for the building map view: buildings loaded for map display,
 * selection, nearby building lookup, search, clustering, and type filtering.
 */

import { create } from 'zustand';
import { buildingsApi } from '../services/api';
import type { Building, BuildingType } from '../types';

/** All building types available for filtering. */
const ALL_BUILDING_TYPES: BuildingType[] = [
  'residential_single',
  'residential_multi',
  'commercial',
  'industrial',
  'institutional',
  'healthcare',
  'educational',
  'government',
  'religious',
  'mixed_use',
  'parking',
  'warehouse',
  'high_rise',
  'other',
];

interface BuildingMapStore {
  // Data
  mapBuildings: Building[];
  selectedBuilding: Building | null;
  nearbyBuildings: Building[];
  searchResults: Building[];
  searchQuery: string;

  // Loading / error state
  isLoading: boolean;
  isLoadingNearby: boolean;
  isSearching: boolean;
  error: string | null;

  // UI state
  showClustering: boolean;
  visibleBuildingTypes: BuildingType[];

  // Actions
  fetchMapBuildings: () => Promise<void>;
  fetchNearbyBuildings: (lat: number, lng: number, radiusKm?: number) => Promise<void>;
  searchBuildings: (query: string) => Promise<void>;
  selectBuilding: (building: Building | null) => void;
  setShowClustering: (enabled: boolean) => void;
  toggleBuildingType: (type: BuildingType) => void;
  clearSearch: () => void;
  clearNearby: () => void;
}

const initialState = {
  mapBuildings: [] as Building[],
  selectedBuilding: null as Building | null,
  nearbyBuildings: [] as Building[],
  searchResults: [] as Building[],
  searchQuery: '',
  isLoading: false,
  isLoadingNearby: false,
  isSearching: false,
  error: null as string | null,
  showClustering: true,
  visibleBuildingTypes: [...ALL_BUILDING_TYPES],
};

/** Debounce timer handle for search. */
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

export const useBuildingMapStore = create<BuildingMapStore>((set) => ({
  ...initialState,

  fetchMapBuildings: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await buildingsApi.list({ page_size: 1000 });
      set({ mapBuildings: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch buildings for map',
        isLoading: false,
      });
    }
  },

  fetchNearbyBuildings: async (lat, lng, radiusKm) => {
    set({ isLoadingNearby: true, error: null });
    try {
      const buildings = await buildingsApi.getNearLocation(lat, lng, radiusKm);
      set({ nearbyBuildings: buildings, isLoadingNearby: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch nearby buildings',
        isLoadingNearby: false,
      });
    }
  },

  searchBuildings: async (query) => {
    set({ searchQuery: query });

    // Clear previous debounce timer
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = null;
    }

    // Clear results for empty query
    if (!query.trim()) {
      set({ searchResults: [], isSearching: false });
      return;
    }

    set({ isSearching: true, error: null });

    // Debounce: wait 300ms before making the API call
    return new Promise<void>((resolve) => {
      searchDebounceTimer = setTimeout(async () => {
        try {
          const results = await buildingsApi.search(query);
          set({ searchResults: results, isSearching: false });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to search buildings',
            isSearching: false,
          });
        }
        resolve();
      }, 300);
    });
  },

  selectBuilding: (building) => {
    set({ selectedBuilding: building });
  },

  setShowClustering: (enabled) => {
    set({ showClustering: enabled });
  },

  toggleBuildingType: (type) => {
    set((state) => {
      const isVisible = state.visibleBuildingTypes.includes(type);
      return {
        visibleBuildingTypes: isVisible
          ? state.visibleBuildingTypes.filter((t) => t !== type)
          : [...state.visibleBuildingTypes, type],
      };
    });
  },

  clearSearch: () => {
    if (searchDebounceTimer) {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = null;
    }
    set({ searchResults: [], searchQuery: '', isSearching: false });
  },

  clearNearby: () => {
    set({ nearbyBuildings: [], isLoadingNearby: false });
  },
}));
