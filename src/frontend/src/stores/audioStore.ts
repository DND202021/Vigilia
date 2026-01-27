/**
 * Audio Clips & Sound Alerts State Store (Zustand)
 */

import { create } from 'zustand';
import type { AudioClip, SoundAlert, AlertHistoryPoint } from '../types';
import { audioClipsApi, soundAlertsApi } from '../services/api';

interface AudioStore {
  audioClips: AudioClip[];
  soundAlerts: SoundAlert[];
  alarms: SoundAlert[];
  noiseWarnings: SoundAlert[];
  historyChart: AlertHistoryPoint[];
  totalSoundAlerts: number;
  totalAlarms: number;
  totalNoiseWarnings: number;
  isLoading: boolean;
  error: string | null;

  // Audio clip actions
  fetchAudioClips: (params?: {
    device_id?: string;
    alert_id?: string;
    event_type?: string;
    page?: number;
    page_size?: number;
  }) => Promise<void>;

  // Sound alert actions
  fetchSoundAlerts: (params?: {
    building_id?: string;
    floor_plan_id?: string;
    device_id?: string;
    severity?: string;
    page?: number;
    page_size?: number;
  }) => Promise<void>;

  fetchAlarms: (params?: { page?: number; page_size?: number }) => Promise<void>;
  fetchNoiseWarnings: (params?: { page?: number; page_size?: number }) => Promise<void>;

  fetchHistoryChart: (params?: {
    building_id?: string;
    floor_plan_id?: string;
    days?: number;
  }) => Promise<void>;

  assignAlert: (alertId: string, userId: string) => Promise<void>;
  clearError: () => void;

  // Real-time handler for new sound alerts from WebSocket
  handleNewSoundAlert: (alert: SoundAlert) => void;
}

export const useAudioStore = create<AudioStore>((set) => ({
  audioClips: [],
  soundAlerts: [],
  alarms: [],
  noiseWarnings: [],
  historyChart: [],
  totalSoundAlerts: 0,
  totalAlarms: 0,
  totalNoiseWarnings: 0,
  isLoading: false,
  error: null,

  fetchAudioClips: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await audioClipsApi.list(params);
      set({ audioClips: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch audio clips',
        isLoading: false,
      });
    }
  },

  fetchSoundAlerts: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await soundAlertsApi.listSoundAnomalies(params);
      set({ soundAlerts: response.items, totalSoundAlerts: response.total, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch sound alerts',
        isLoading: false,
      });
    }
  },

  fetchAlarms: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await soundAlertsApi.listAlarms(params);
      set({ alarms: response.items, totalAlarms: response.total, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch alarms',
        isLoading: false,
      });
    }
  },

  fetchNoiseWarnings: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await soundAlertsApi.listNoiseWarnings(params);
      set({ noiseWarnings: response.items, totalNoiseWarnings: response.total, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch noise warnings',
        isLoading: false,
      });
    }
  },

  fetchHistoryChart: async (params) => {
    try {
      const response = await soundAlertsApi.getHistoryChart(params);
      set({ historyChart: response.data });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch alert history',
      });
    }
  },

  assignAlert: async (alertId, userId) => {
    try {
      const updated = await soundAlertsApi.assignAlert(alertId, userId);
      set((state) => ({
        soundAlerts: state.soundAlerts.map((a) => (a.id === alertId ? updated : a)),
        alarms: state.alarms.map((a) => (a.id === alertId ? updated : a)),
        noiseWarnings: state.noiseWarnings.map((a) => (a.id === alertId ? updated : a)),
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to assign alert',
      });
      throw error;
    }
  },

  clearError: () => set({ error: null }),

  handleNewSoundAlert: (alert) => {
    set((state) => {
      const isCritical = alert.severity === 'critical' || alert.severity === 'high';
      const alertType = alert.alert_type as string;
      const isNoiseWarning = alertType === 'scream' || alertType === 'car_alarm';

      return {
        soundAlerts: [alert, ...state.soundAlerts],
        totalSoundAlerts: state.totalSoundAlerts + 1,
        alarms: isCritical ? [alert, ...state.alarms] : state.alarms,
        totalAlarms: isCritical ? state.totalAlarms + 1 : state.totalAlarms,
        noiseWarnings: isNoiseWarning ? [alert, ...state.noiseWarnings] : state.noiseWarnings,
        totalNoiseWarnings: isNoiseWarning ? state.totalNoiseWarnings + 1 : state.totalNoiseWarnings,
      };
    });
  },
}));
