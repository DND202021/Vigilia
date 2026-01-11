/**
 * Alert State Store (Zustand)
 */

import { create } from 'zustand';
import type { Alert, AlertAcknowledgeRequest, AlertCreateIncidentRequest, Incident } from '../types';
import { alertsApi } from '../services/api';

interface AlertStore {
  alerts: Alert[];
  pendingAlerts: Alert[];
  selectedAlert: Alert | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchAlerts: (params?: Record<string, unknown>) => Promise<void>;
  fetchPendingAlerts: () => Promise<void>;
  fetchAlert: (id: string) => Promise<void>;
  acknowledgeAlert: (id: string, data?: AlertAcknowledgeRequest) => Promise<void>;
  createIncidentFromAlert: (id: string, data: AlertCreateIncidentRequest) => Promise<Incident>;
  resolveAlert: (id: string, isFalseAlarm?: boolean) => Promise<void>;
  setSelectedAlert: (alert: Alert | null) => void;
  clearError: () => void;

  // Real-time update handler
  handleAlertUpdate: (alert: Alert) => void;
}

export const useAlertStore = create<AlertStore>((set, get) => ({
  alerts: [],
  pendingAlerts: [],
  selectedAlert: null,
  isLoading: false,
  error: null,

  fetchAlerts: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await alertsApi.list(params);
      set({ alerts: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch alerts',
        isLoading: false,
      });
    }
  },

  fetchPendingAlerts: async () => {
    set({ isLoading: true, error: null });
    try {
      const alerts = await alertsApi.getPending();
      set({ pendingAlerts: alerts, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch pending alerts',
        isLoading: false,
      });
    }
  },

  fetchAlert: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const alert = await alertsApi.get(id);
      set({ selectedAlert: alert, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch alert',
        isLoading: false,
      });
    }
  },

  acknowledgeAlert: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await alertsApi.acknowledge(id, data);
      set((state) => ({
        alerts: state.alerts.map((a) => (a.id === id ? updated : a)),
        pendingAlerts: state.pendingAlerts.filter((a) => a.id !== id),
        selectedAlert: state.selectedAlert?.id === id ? updated : state.selectedAlert,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to acknowledge alert',
        isLoading: false,
      });
      throw error;
    }
  },

  createIncidentFromAlert: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const incident = await alertsApi.createIncident(id, data);
      // Update alert status
      const updatedAlerts = get().alerts.map((a) =>
        a.id === id ? { ...a, status: 'escalated' as const, linked_incident_id: incident.id } : a
      );
      set({
        alerts: updatedAlerts,
        pendingAlerts: get().pendingAlerts.filter((a) => a.id !== id),
        isLoading: false,
      });
      return incident;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create incident from alert',
        isLoading: false,
      });
      throw error;
    }
  },

  resolveAlert: async (id, isFalseAlarm) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await alertsApi.resolve(id, isFalseAlarm);
      set((state) => ({
        alerts: state.alerts.map((a) => (a.id === id ? updated : a)),
        pendingAlerts: state.pendingAlerts.filter((a) => a.id !== id),
        selectedAlert: state.selectedAlert?.id === id ? updated : state.selectedAlert,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to resolve alert',
        isLoading: false,
      });
      throw error;
    }
  },

  setSelectedAlert: (alert) => set({ selectedAlert: alert }),

  clearError: () => set({ error: null }),

  handleAlertUpdate: (alert) => {
    set((state) => {
      const isPending = alert.status === 'new';

      return {
        alerts: state.alerts.some((a) => a.id === alert.id)
          ? state.alerts.map((a) => (a.id === alert.id ? alert : a))
          : [alert, ...state.alerts],
        pendingAlerts: isPending
          ? state.pendingAlerts.some((a) => a.id === alert.id)
            ? state.pendingAlerts.map((a) => (a.id === alert.id ? alert : a))
            : [alert, ...state.pendingAlerts]
          : state.pendingAlerts.filter((a) => a.id !== alert.id),
        selectedAlert: state.selectedAlert?.id === alert.id ? alert : state.selectedAlert,
      };
    });
  },
}));
