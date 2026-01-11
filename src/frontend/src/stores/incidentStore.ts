/**
 * Incident State Store (Zustand)
 */

import { create } from 'zustand';
import type { Incident, IncidentCreateRequest, IncidentUpdateRequest } from '../types';
import { incidentsApi } from '../services/api';

interface IncidentStore {
  incidents: Incident[];
  activeIncidents: Incident[];
  selectedIncident: Incident | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchIncidents: (params?: Record<string, unknown>) => Promise<void>;
  fetchActiveIncidents: () => Promise<void>;
  fetchIncident: (id: string) => Promise<void>;
  createIncident: (data: IncidentCreateRequest) => Promise<Incident>;
  updateIncident: (id: string, data: IncidentUpdateRequest) => Promise<void>;
  updateIncidentStatus: (id: string, status: string, notes?: string) => Promise<void>;
  assignUnit: (incidentId: string, unitId: string) => Promise<void>;
  setSelectedIncident: (incident: Incident | null) => void;
  clearError: () => void;

  // Real-time update handler
  handleIncidentUpdate: (incident: Incident) => void;
}

export const useIncidentStore = create<IncidentStore>((set, get) => ({
  incidents: [],
  activeIncidents: [],
  selectedIncident: null,
  isLoading: false,
  error: null,

  fetchIncidents: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await incidentsApi.list(params);
      set({ incidents: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch incidents',
        isLoading: false,
      });
    }
  },

  fetchActiveIncidents: async () => {
    set({ isLoading: true, error: null });
    try {
      const incidents = await incidentsApi.getActive();
      set({ activeIncidents: incidents, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch active incidents',
        isLoading: false,
      });
    }
  },

  fetchIncident: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const incident = await incidentsApi.get(id);
      set({ selectedIncident: incident, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch incident',
        isLoading: false,
      });
    }
  },

  createIncident: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const incident = await incidentsApi.create(data);
      set((state) => ({
        incidents: [incident, ...state.incidents],
        activeIncidents: [incident, ...state.activeIncidents],
        isLoading: false,
      }));
      return incident;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create incident',
        isLoading: false,
      });
      throw error;
    }
  },

  updateIncident: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await incidentsApi.update(id, data);
      set((state) => ({
        incidents: state.incidents.map((i) => (i.id === id ? updated : i)),
        activeIncidents: state.activeIncidents.map((i) => (i.id === id ? updated : i)),
        selectedIncident: state.selectedIncident?.id === id ? updated : state.selectedIncident,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update incident',
        isLoading: false,
      });
      throw error;
    }
  },

  updateIncidentStatus: async (id, status, notes) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await incidentsApi.updateStatus(id, status, notes);
      set((state) => ({
        incidents: state.incidents.map((i) => (i.id === id ? updated : i)),
        activeIncidents:
          status === 'closed' || status === 'cancelled'
            ? state.activeIncidents.filter((i) => i.id !== id)
            : state.activeIncidents.map((i) => (i.id === id ? updated : i)),
        selectedIncident: state.selectedIncident?.id === id ? updated : state.selectedIncident,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update incident status',
        isLoading: false,
      });
      throw error;
    }
  },

  assignUnit: async (incidentId, unitId) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await incidentsApi.assignUnit(incidentId, unitId);
      set((state) => ({
        incidents: state.incidents.map((i) => (i.id === incidentId ? updated : i)),
        activeIncidents: state.activeIncidents.map((i) => (i.id === incidentId ? updated : i)),
        selectedIncident:
          state.selectedIncident?.id === incidentId ? updated : state.selectedIncident,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to assign unit',
        isLoading: false,
      });
      throw error;
    }
  },

  setSelectedIncident: (incident) => set({ selectedIncident: incident }),

  clearError: () => set({ error: null }),

  handleIncidentUpdate: (incident) => {
    set((state) => {
      const isActive = !['closed', 'cancelled', 'resolved'].includes(incident.status);

      return {
        incidents: state.incidents.some((i) => i.id === incident.id)
          ? state.incidents.map((i) => (i.id === incident.id ? incident : i))
          : [incident, ...state.incidents],
        activeIncidents: isActive
          ? state.activeIncidents.some((i) => i.id === incident.id)
            ? state.activeIncidents.map((i) => (i.id === incident.id ? incident : i))
            : [incident, ...state.activeIncidents]
          : state.activeIncidents.filter((i) => i.id !== incident.id),
        selectedIncident:
          state.selectedIncident?.id === incident.id ? incident : state.selectedIncident,
      };
    });
  },
}));
