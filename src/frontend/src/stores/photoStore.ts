/**
 * Photo Store (Zustand)
 *
 * Manages state for building photo gallery: list, upload, delete, filters.
 */

import { create } from 'zustand';
import { photosApi } from '../services/api';
import type { BuildingPhoto } from '../types';

interface PhotoFilters {
  tags: string[];
  dateFrom?: string;
  dateTo?: string;
  floorPlanId?: string;
}

interface PhotoStore {
  // Data
  photos: BuildingPhoto[];
  selectedPhoto: BuildingPhoto | null;
  allTags: string[];

  // Loading state
  isLoading: boolean;
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;

  // Filters
  filters: PhotoFilters;

  // Actions
  fetchPhotos: (buildingId: string) => Promise<void>;
  uploadPhoto: (buildingId: string, file: File, metadata: { title: string; description?: string; floorPlanId?: string; latitude?: number; longitude?: number; tags?: string[] }) => Promise<BuildingPhoto | null>;
  deletePhoto: (photoId: string) => Promise<void>;
  selectPhoto: (photo: BuildingPhoto | null) => void;
  setFilters: (filters: Partial<PhotoFilters>) => void;
  clearFilters: () => void;
  clearError: () => void;
}

const initialFilters: PhotoFilters = {
  tags: [],
  dateFrom: undefined,
  dateTo: undefined,
  floorPlanId: undefined,
};

const initialState = {
  photos: [] as BuildingPhoto[],
  selectedPhoto: null as BuildingPhoto | null,
  allTags: [] as string[],
  isLoading: false,
  isUploading: false,
  uploadProgress: 0,
  error: null as string | null,
  filters: initialFilters,
};

export const usePhotoStore = create<PhotoStore>((set, get) => ({
  ...initialState,

  fetchPhotos: async (buildingId: string) => {
    set({ isLoading: true, error: null });
    try {
      const { filters } = get();
      const response = await photosApi.list(buildingId, {
        tags: filters.tags.length > 0 ? filters.tags.join(',') : undefined,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        floor_plan_id: filters.floorPlanId,
      });
      // Extract unique tags from all photos
      const allTags = [...new Set(response.items.flatMap((p) => p.tags || []))];
      set({ photos: response.items, allTags, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch photos',
        isLoading: false,
      });
    }
  },

  uploadPhoto: async (buildingId, file, metadata) => {
    set({ isUploading: true, uploadProgress: 0, error: null });
    try {
      const photo = await photosApi.upload(buildingId, file, metadata, (progress) => {
        set({ uploadProgress: progress });
      });
      set((state) => ({
        photos: [photo, ...state.photos],
        allTags: [...new Set([...state.allTags, ...(photo.tags || [])])],
        isUploading: false,
        uploadProgress: 100,
      }));
      return photo;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to upload photo',
        isUploading: false,
        uploadProgress: 0,
      });
      return null;
    }
  },

  deletePhoto: async (photoId) => {
    try {
      await photosApi.delete(photoId);
      set((state) => ({
        photos: state.photos.filter((p) => p.id !== photoId),
        selectedPhoto: state.selectedPhoto?.id === photoId ? null : state.selectedPhoto,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete photo',
      });
    }
  },

  selectPhoto: (photo) => {
    set({ selectedPhoto: photo });
  },

  setFilters: (newFilters) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    }));
  },

  clearFilters: () => {
    set({ filters: initialFilters });
  },

  clearError: () => {
    set({ error: null });
  },
}));
