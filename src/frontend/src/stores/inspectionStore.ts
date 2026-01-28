/**
 * Inspection Store (Zustand)
 *
 * Manages state for building inspections: list, create, update, upcoming/overdue tracking.
 */

import { create } from 'zustand';
import { inspectionsApi } from '../services/api';
import type { Inspection, InspectionType, InspectionStatus, InspectionCreateRequest, InspectionUpdateRequest } from '../types';

interface InspectionStore {
  // Data
  inspections: Inspection[];
  upcomingInspections: Inspection[];
  overdueInspections: Inspection[];
  selectedInspection: Inspection | null;

  // Loading state
  isLoading: boolean;
  isLoadingUpcoming: boolean;
  isLoadingOverdue: boolean;
  isSaving: boolean;
  error: string | null;

  // Filters
  typeFilter: InspectionType | null;
  statusFilter: InspectionStatus | null;

  // Actions
  fetchInspections: (buildingId: string) => Promise<void>;
  fetchUpcoming: () => Promise<void>;
  fetchOverdue: () => Promise<void>;
  createInspection: (buildingId: string, data: InspectionCreateRequest) => Promise<Inspection | null>;
  updateInspection: (inspectionId: string, data: InspectionUpdateRequest) => Promise<void>;
  deleteInspection: (inspectionId: string) => Promise<void>;
  selectInspection: (inspection: Inspection | null) => void;
  setTypeFilter: (type: InspectionType | null) => void;
  setStatusFilter: (status: InspectionStatus | null) => void;
  clearError: () => void;
}

const initialState = {
  inspections: [] as Inspection[],
  upcomingInspections: [] as Inspection[],
  overdueInspections: [] as Inspection[],
  selectedInspection: null as Inspection | null,
  isLoading: false,
  isLoadingUpcoming: false,
  isLoadingOverdue: false,
  isSaving: false,
  error: null as string | null,
  typeFilter: null as InspectionType | null,
  statusFilter: null as InspectionStatus | null,
};

export const useInspectionStore = create<InspectionStore>((set, get) => ({
  ...initialState,

  fetchInspections: async (buildingId: string) => {
    set({ isLoading: true, error: null });
    try {
      const { typeFilter, statusFilter } = get();
      const response = await inspectionsApi.list(buildingId, {
        inspection_type: typeFilter || undefined,
        status: statusFilter || undefined,
      });
      set({ inspections: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch inspections',
        isLoading: false,
      });
    }
  },

  fetchUpcoming: async () => {
    set({ isLoadingUpcoming: true, error: null });
    try {
      const response = await inspectionsApi.getUpcoming();
      set({ upcomingInspections: response.items, isLoadingUpcoming: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch upcoming inspections',
        isLoadingUpcoming: false,
      });
    }
  },

  fetchOverdue: async () => {
    set({ isLoadingOverdue: true, error: null });
    try {
      const response = await inspectionsApi.getOverdue();
      set({ overdueInspections: response.items, isLoadingOverdue: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch overdue inspections',
        isLoadingOverdue: false,
      });
    }
  },

  createInspection: async (buildingId, data) => {
    set({ isSaving: true, error: null });
    try {
      const inspection = await inspectionsApi.create(buildingId, data);
      set((state) => ({
        inspections: [inspection, ...state.inspections],
        isSaving: false,
      }));
      return inspection;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create inspection',
        isSaving: false,
      });
      return null;
    }
  },

  updateInspection: async (inspectionId, data) => {
    set({ isSaving: true, error: null });
    try {
      const updated = await inspectionsApi.update(inspectionId, data);
      set((state) => ({
        inspections: state.inspections.map((i) => (i.id === inspectionId ? updated : i)),
        selectedInspection: state.selectedInspection?.id === inspectionId ? updated : state.selectedInspection,
        isSaving: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update inspection',
        isSaving: false,
      });
    }
  },

  deleteInspection: async (inspectionId) => {
    try {
      await inspectionsApi.delete(inspectionId);
      set((state) => ({
        inspections: state.inspections.filter((i) => i.id !== inspectionId),
        selectedInspection: state.selectedInspection?.id === inspectionId ? null : state.selectedInspection,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete inspection',
      });
    }
  },

  selectInspection: (inspection) => {
    set({ selectedInspection: inspection });
  },

  setTypeFilter: (type) => {
    set({ typeFilter: type });
  },

  setStatusFilter: (status) => {
    set({ statusFilter: status });
  },

  clearError: () => {
    set({ error: null });
  },
}));
