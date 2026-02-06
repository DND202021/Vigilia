/**
 * Incident Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useIncidentStore } from '../stores/incidentStore';
import { incidentsApi } from '../services/api';
import type { Incident } from '../types';

// Mock API
vi.mock('../services/api', () => ({
  incidentsApi: {
    list: vi.fn(),
    getActive: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    updateStatus: vi.fn(),
    assignUnit: vi.fn(),
  },
}));

const mockIncident: Incident = {
  id: 'inc-1',
  incident_number: 'INC-001',
  incident_type: 'fire',
  priority: 1,
  status: 'new',
  title: 'Building Fire',
  reported_at: new Date().toISOString(),
  agency_id: 'agency-1',
  assigned_units: [],
  timeline_events: [],
};

describe('useIncidentStore', () => {
  beforeEach(() => {
    useIncidentStore.setState({
      incidents: [],
      activeIncidents: [],
      selectedIncident: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('fetchIncidents', () => {
    it('should fetch incidents successfully', async () => {
      const mockResponse = {
        items: [mockIncident],
        total: 1,
        page: 1,
        page_size: 10,
        total_pages: 1,
      };

      vi.mocked(incidentsApi.list).mockResolvedValue(mockResponse);

      await useIncidentStore.getState().fetchIncidents();

      const state = useIncidentStore.getState();
      expect(state.incidents).toEqual([mockIncident]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should handle fetch error', async () => {
      vi.mocked(incidentsApi.list).mockRejectedValue(new Error('Network error'));

      await useIncidentStore.getState().fetchIncidents();

      const state = useIncidentStore.getState();
      expect(state.incidents).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('Network error');
    });

    it('should pass filter params to API', async () => {
      vi.mocked(incidentsApi.list).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      });

      await useIncidentStore.getState().fetchIncidents({ status: 'active', priority: 1 });

      expect(incidentsApi.list).toHaveBeenCalledWith({ status: 'active', priority: 1 });
    });
  });

  describe('fetchActiveIncidents', () => {
    it('should fetch active incidents successfully', async () => {
      vi.mocked(incidentsApi.getActive).mockResolvedValue([mockIncident]);

      await useIncidentStore.getState().fetchActiveIncidents();

      const state = useIncidentStore.getState();
      expect(state.activeIncidents).toEqual([mockIncident]);
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should handle fetch error', async () => {
      vi.mocked(incidentsApi.getActive).mockRejectedValue(new Error('API error'));

      await useIncidentStore.getState().fetchActiveIncidents();

      const state = useIncidentStore.getState();
      expect(state.error).toBe('API error');
    });
  });

  describe('fetchIncident', () => {
    it('should fetch single incident and set as selected', async () => {
      vi.mocked(incidentsApi.get).mockResolvedValue(mockIncident);

      await useIncidentStore.getState().fetchIncident('inc-1');

      const state = useIncidentStore.getState();
      expect(state.selectedIncident).toEqual(mockIncident);
      expect(state.isLoading).toBe(false);
      expect(incidentsApi.get).toHaveBeenCalledWith('inc-1');
    });

    it('should handle fetch error', async () => {
      vi.mocked(incidentsApi.get).mockRejectedValue(new Error('Not found'));

      await useIncidentStore.getState().fetchIncident('inc-999');

      const state = useIncidentStore.getState();
      expect(state.selectedIncident).toBeNull();
      expect(state.error).toBe('Not found');
    });
  });

  describe('createIncident', () => {
    it('should create incident and add to lists', async () => {
      const newIncident = { ...mockIncident, id: 'inc-2' };
      vi.mocked(incidentsApi.create).mockResolvedValue(newIncident);

      const result = await useIncidentStore.getState().createIncident({
        incident_type: 'fire',
        priority: 1,
        title: 'New Fire',
        description: 'Test',
      });

      expect(result).toEqual(newIncident);

      const state = useIncidentStore.getState();
      expect(state.incidents).toContain(newIncident);
      expect(state.activeIncidents).toContain(newIncident);
      expect(state.isLoading).toBe(false);
    });

    it('should handle create error', async () => {
      vi.mocked(incidentsApi.create).mockRejectedValue(new Error('Validation error'));

      await expect(
        useIncidentStore.getState().createIncident({
          incident_type: 'fire',
          priority: 1,
          title: 'Invalid',
        })
      ).rejects.toThrow('Validation error');

      const state = useIncidentStore.getState();
      expect(state.error).toBe('Validation error');
    });
  });

  describe('updateIncident', () => {
    it('should update incident in all lists', async () => {
      const existingIncident = { ...mockIncident };
      const updatedIncident = { ...mockIncident, title: 'Updated Title' };

      useIncidentStore.setState({
        incidents: [existingIncident],
        activeIncidents: [existingIncident],
        selectedIncident: existingIncident,
      });

      vi.mocked(incidentsApi.update).mockResolvedValue(updatedIncident);

      await useIncidentStore.getState().updateIncident('inc-1', { title: 'Updated Title' });

      const state = useIncidentStore.getState();
      expect(state.incidents[0].title).toBe('Updated Title');
      expect(state.activeIncidents[0].title).toBe('Updated Title');
      expect(state.selectedIncident?.title).toBe('Updated Title');
    });

    it('should handle update error', async () => {
      vi.mocked(incidentsApi.update).mockRejectedValue(new Error('Update failed'));

      await expect(
        useIncidentStore.getState().updateIncident('inc-1', { title: 'New' })
      ).rejects.toThrow('Update failed');

      const state = useIncidentStore.getState();
      expect(state.error).toBe('Update failed');
    });
  });

  describe('updateIncidentStatus', () => {
    it('should update status and keep in active list', async () => {
      const incident = { ...mockIncident, status: 'new' as const };
      const updatedIncident = { ...mockIncident, status: 'in_progress' as const };

      useIncidentStore.setState({
        incidents: [incident],
        activeIncidents: [incident],
      });

      vi.mocked(incidentsApi.updateStatus).mockResolvedValue(updatedIncident);

      await useIncidentStore.getState().updateIncidentStatus('inc-1', 'in_progress');

      const state = useIncidentStore.getState();
      expect(state.incidents[0].status).toBe('in_progress');
      expect(state.activeIncidents).toHaveLength(1);
    });

    it('should remove from active list when closed', async () => {
      const incident = { ...mockIncident, status: 'in_progress' as const };
      const closedIncident = { ...mockIncident, status: 'closed' as const };

      useIncidentStore.setState({
        incidents: [incident],
        activeIncidents: [incident],
      });

      vi.mocked(incidentsApi.updateStatus).mockResolvedValue(closedIncident);

      await useIncidentStore.getState().updateIncidentStatus('inc-1', 'closed');

      const state = useIncidentStore.getState();
      expect(state.incidents[0].status).toBe('closed');
      expect(state.activeIncidents).toHaveLength(0);
    });

    it('should handle status update error', async () => {
      vi.mocked(incidentsApi.updateStatus).mockRejectedValue(new Error('Status update failed'));

      await expect(
        useIncidentStore.getState().updateIncidentStatus('inc-1', 'closed')
      ).rejects.toThrow('Status update failed');
    });
  });

  describe('assignUnit', () => {
    it('should assign unit to incident', async () => {
      const incident = { ...mockIncident };
      const updatedIncident = { ...mockIncident, assigned_units: ['unit-1'] };

      useIncidentStore.setState({
        incidents: [incident],
        activeIncidents: [incident],
      });

      vi.mocked(incidentsApi.assignUnit).mockResolvedValue(updatedIncident);

      await useIncidentStore.getState().assignUnit('inc-1', 'unit-1');

      const state = useIncidentStore.getState();
      expect(state.incidents[0].assigned_units).toContain('unit-1');
      expect(incidentsApi.assignUnit).toHaveBeenCalledWith('inc-1', 'unit-1');
    });

    it('should handle assign error', async () => {
      vi.mocked(incidentsApi.assignUnit).mockRejectedValue(new Error('Assign failed'));

      await expect(
        useIncidentStore.getState().assignUnit('inc-1', 'unit-1')
      ).rejects.toThrow('Assign failed');
    });
  });

  describe('setSelectedIncident', () => {
    it('should set selected incident', () => {
      useIncidentStore.getState().setSelectedIncident(mockIncident);

      const state = useIncidentStore.getState();
      expect(state.selectedIncident).toEqual(mockIncident);
    });

    it('should clear selected incident', () => {
      useIncidentStore.setState({ selectedIncident: mockIncident });
      useIncidentStore.getState().setSelectedIncident(null);

      const state = useIncidentStore.getState();
      expect(state.selectedIncident).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useIncidentStore.setState({ error: 'Some error' });
      useIncidentStore.getState().clearError();

      const state = useIncidentStore.getState();
      expect(state.error).toBeNull();
    });
  });
});
