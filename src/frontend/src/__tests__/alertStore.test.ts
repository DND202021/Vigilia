/**
 * Alert Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAlertStore } from '../stores/alertStore';
import { alertsApi } from '../services/api';
import type { Alert, Incident } from '../types';

// Mock API
vi.mock('../services/api', () => ({
  alertsApi: {
    list: vi.fn(),
    getPending: vi.fn(),
    get: vi.fn(),
    acknowledge: vi.fn(),
    createIncident: vi.fn(),
    resolve: vi.fn(),
  },
}));

const mockAlert: Alert = {
  id: 'alert-1',
  alert_type: 'fire_alarm',
  severity: 'critical',
  source: 'Building A - Floor 1',
  title: 'Fire Detected',
  status: 'new',
  created_at: new Date().toISOString(),
};

describe('useAlertStore', () => {
  beforeEach(() => {
    useAlertStore.setState({
      alerts: [],
      pendingAlerts: [],
      selectedAlert: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('fetchAlerts', () => {
    it('should fetch alerts successfully', async () => {
      const mockResponse = {
        items: [mockAlert],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      };

      vi.mocked(alertsApi.list).mockResolvedValue(mockResponse);

      await useAlertStore.getState().fetchAlerts();

      const state = useAlertStore.getState();
      expect(state.alerts).toEqual([mockAlert]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should handle fetch error', async () => {
      vi.mocked(alertsApi.list).mockRejectedValue(new Error('Network error'));

      await useAlertStore.getState().fetchAlerts();

      const state = useAlertStore.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });

    it('should pass filter params to API', async () => {
      vi.mocked(alertsApi.list).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      });

      await useAlertStore.getState().fetchAlerts({ severity: 'critical', status: 'new' });

      expect(alertsApi.list).toHaveBeenCalledWith({ severity: 'critical', status: 'new' });
    });
  });

  describe('fetchPendingAlerts', () => {
    it('should fetch pending alerts successfully', async () => {
      vi.mocked(alertsApi.getPending).mockResolvedValue([mockAlert]);

      await useAlertStore.getState().fetchPendingAlerts();

      const state = useAlertStore.getState();
      expect(state.pendingAlerts).toEqual([mockAlert]);
      expect(state.isLoading).toBe(false);
    });

    it('should handle fetch error', async () => {
      vi.mocked(alertsApi.getPending).mockRejectedValue(new Error('API error'));

      await useAlertStore.getState().fetchPendingAlerts();

      const state = useAlertStore.getState();
      expect(state.error).toBe('API error');
    });
  });

  describe('fetchAlert', () => {
    it('should fetch single alert and set as selected', async () => {
      vi.mocked(alertsApi.get).mockResolvedValue(mockAlert);

      await useAlertStore.getState().fetchAlert('alert-1');

      const state = useAlertStore.getState();
      expect(state.selectedAlert).toEqual(mockAlert);
      expect(alertsApi.get).toHaveBeenCalledWith('alert-1');
    });

    it('should handle fetch error', async () => {
      vi.mocked(alertsApi.get).mockRejectedValue(new Error('Not found'));

      await useAlertStore.getState().fetchAlert('alert-999');

      const state = useAlertStore.getState();
      expect(state.error).toBe('Not found');
    });
  });

  describe('acknowledgeAlert', () => {
    it('should acknowledge alert and remove from pending', async () => {
      const acknowledgedAlert = { ...mockAlert, status: 'acknowledged' as const };

      useAlertStore.setState({
        alerts: [mockAlert],
        pendingAlerts: [mockAlert],
      });

      vi.mocked(alertsApi.acknowledge).mockResolvedValue(acknowledgedAlert);

      await useAlertStore.getState().acknowledgeAlert('alert-1');

      const state = useAlertStore.getState();
      expect(state.alerts[0].status).toBe('acknowledged');
      expect(state.pendingAlerts).toHaveLength(0);
    });

    it('should update selected alert when acknowledged', async () => {
      const acknowledgedAlert = { ...mockAlert, status: 'acknowledged' as const };

      useAlertStore.setState({
        alerts: [mockAlert],
        selectedAlert: mockAlert,
      });

      vi.mocked(alertsApi.acknowledge).mockResolvedValue(acknowledgedAlert);

      await useAlertStore.getState().acknowledgeAlert('alert-1', { acknowledged_by: 'user-1' });

      const state = useAlertStore.getState();
      expect(state.selectedAlert?.status).toBe('acknowledged');
      expect(alertsApi.acknowledge).toHaveBeenCalledWith('alert-1', { acknowledged_by: 'user-1' });
    });

    it('should handle acknowledge error', async () => {
      vi.mocked(alertsApi.acknowledge).mockRejectedValue(new Error('Acknowledge failed'));

      await expect(
        useAlertStore.getState().acknowledgeAlert('alert-1')
      ).rejects.toThrow('Acknowledge failed');

      const state = useAlertStore.getState();
      expect(state.error).toBe('Acknowledge failed');
    });
  });

  describe('createIncidentFromAlert', () => {
    it('should create incident from alert', async () => {
      const mockIncident: Incident = {
        id: 'inc-1',
        incident_number: 'INC-001',
        incident_type: 'fire',
        priority: 1,
        status: 'new',
        title: 'Fire from Alert',
        reported_at: new Date().toISOString(),
        agency_id: 'agency-1',
        assigned_units: [],
        timeline_events: [],
      };

      useAlertStore.setState({
        alerts: [mockAlert],
        pendingAlerts: [mockAlert],
      });

      vi.mocked(alertsApi.createIncident).mockResolvedValue(mockIncident);

      const result = await useAlertStore.getState().createIncidentFromAlert('alert-1', {
        incident_type: 'fire',
        priority: 1,
        title: 'Fire from Alert',
      });

      expect(result).toEqual(mockIncident);

      const state = useAlertStore.getState();
      expect(state.alerts[0].status).toBe('escalated');
      expect(state.alerts[0].linked_incident_id).toBe('inc-1');
      expect(state.pendingAlerts).toHaveLength(0);
    });

    it('should handle create incident error', async () => {
      vi.mocked(alertsApi.createIncident).mockRejectedValue(new Error('Create failed'));

      await expect(
        useAlertStore.getState().createIncidentFromAlert('alert-1', {
          incident_type: 'fire',
          priority: 1,
          title: 'Test',
        })
      ).rejects.toThrow('Create failed');

      const state = useAlertStore.getState();
      expect(state.error).toBe('Create failed');
    });
  });

  describe('resolveAlert', () => {
    it('should resolve alert and remove from pending', async () => {
      const resolvedAlert = { ...mockAlert, status: 'resolved' as const };

      useAlertStore.setState({
        alerts: [mockAlert],
        pendingAlerts: [mockAlert],
      });

      vi.mocked(alertsApi.resolve).mockResolvedValue(resolvedAlert);

      await useAlertStore.getState().resolveAlert('alert-1', false);

      const state = useAlertStore.getState();
      expect(state.alerts[0].status).toBe('resolved');
      expect(state.pendingAlerts).toHaveLength(0);
      expect(alertsApi.resolve).toHaveBeenCalledWith('alert-1', false);
    });

    it('should mark as false alarm', async () => {
      const resolvedAlert = { ...mockAlert, status: 'resolved' as const, is_false_alarm: true };

      useAlertStore.setState({
        alerts: [mockAlert],
      });

      vi.mocked(alertsApi.resolve).mockResolvedValue(resolvedAlert);

      await useAlertStore.getState().resolveAlert('alert-1', true);

      expect(alertsApi.resolve).toHaveBeenCalledWith('alert-1', true);
    });

    it('should handle resolve error', async () => {
      vi.mocked(alertsApi.resolve).mockRejectedValue(new Error('Resolve failed'));

      await expect(
        useAlertStore.getState().resolveAlert('alert-1')
      ).rejects.toThrow('Resolve failed');
    });
  });

  describe('setSelectedAlert', () => {
    it('should set selected alert', () => {
      useAlertStore.getState().setSelectedAlert(mockAlert);

      const state = useAlertStore.getState();
      expect(state.selectedAlert).toEqual(mockAlert);
    });

    it('should clear selected alert', () => {
      useAlertStore.setState({ selectedAlert: mockAlert });
      useAlertStore.getState().setSelectedAlert(null);

      const state = useAlertStore.getState();
      expect(state.selectedAlert).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useAlertStore.setState({ error: 'Some error' });
      useAlertStore.getState().clearError();

      const state = useAlertStore.getState();
      expect(state.error).toBeNull();
    });
  });
});
