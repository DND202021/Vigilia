/**
 * Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../stores/authStore';
import { useIncidentStore } from '../stores/incidentStore';
import { useAlertStore } from '../stores/alertStore';
import { useResourceStore } from '../stores/resourceStore';
import type { Incident, Alert, Resource } from '../types';

// Mock API
vi.mock('../services/api', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
  },
  incidentsApi: {
    list: vi.fn(),
    getActive: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    updateStatus: vi.fn(),
    assignUnit: vi.fn(),
  },
  alertsApi: {
    list: vi.fn(),
    getPending: vi.fn(),
    acknowledge: vi.fn(),
    resolve: vi.fn(),
    createIncident: vi.fn(),
  },
  resourcesApi: {
    list: vi.fn(),
    getAvailable: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    updateStatus: vi.fn(),
    updateLocation: vi.fn(),
  },
  tokenStorage: {
    getAccessToken: vi.fn(),
    getRefreshToken: vi.fn(),
    setTokens: vi.fn(),
    clearTokens: vi.fn(),
  },
}));

describe('useIncidentStore', () => {
  beforeEach(() => {
    useIncidentStore.setState({
      incidents: [],
      activeIncidents: [],
      selectedIncident: null,
      isLoading: false,
      error: null,
    });
  });

  it('should handle incident updates', () => {
    const store = useIncidentStore.getState();

    const incident: Incident = {
      id: '1',
      incident_number: 'INC-001',
      incident_type: 'fire',
      priority: 1,
      status: 'new',
      title: 'Test Incident',
      reported_at: new Date().toISOString(),
      agency_id: 'agency-1',
      assigned_units: [],
      timeline_events: [],
    };

    store.handleIncidentUpdate(incident);

    const updatedState = useIncidentStore.getState();
    expect(updatedState.incidents).toHaveLength(1);
    expect(updatedState.activeIncidents).toHaveLength(1);
  });

  it('should remove closed incidents from active list', () => {
    const store = useIncidentStore.getState();

    const incident: Incident = {
      id: '1',
      incident_number: 'INC-001',
      incident_type: 'fire',
      priority: 1,
      status: 'new',
      title: 'Test Incident',
      reported_at: new Date().toISOString(),
      agency_id: 'agency-1',
      assigned_units: [],
      timeline_events: [],
    };

    store.handleIncidentUpdate(incident);
    expect(useIncidentStore.getState().activeIncidents).toHaveLength(1);

    // Close incident
    store.handleIncidentUpdate({ ...incident, status: 'closed' });
    expect(useIncidentStore.getState().activeIncidents).toHaveLength(0);
  });

  it('should update selected incident', () => {
    const store = useIncidentStore.getState();

    const incident: Incident = {
      id: '1',
      incident_number: 'INC-001',
      incident_type: 'fire',
      priority: 1,
      status: 'new',
      title: 'Test Incident',
      reported_at: new Date().toISOString(),
      agency_id: 'agency-1',
      assigned_units: [],
      timeline_events: [],
    };

    store.setSelectedIncident(incident);
    expect(useIncidentStore.getState().selectedIncident).toEqual(incident);

    store.setSelectedIncident(null);
    expect(useIncidentStore.getState().selectedIncident).toBeNull();
  });

  it('should clear error', () => {
    useIncidentStore.setState({ error: 'Test error' });
    useIncidentStore.getState().clearError();
    expect(useIncidentStore.getState().error).toBeNull();
  });
});

describe('useAlertStore', () => {
  beforeEach(() => {
    useAlertStore.setState({
      alerts: [],
      pendingAlerts: [],
      selectedAlert: null,
      isLoading: false,
      error: null,
    });
  });

  it('should handle alert updates', () => {
    const store = useAlertStore.getState();

    const alert: Alert = {
      id: '1',
      alert_type: 'fire_alarm',
      severity: 'critical',
      source: 'Test Source',
      title: 'Test Alert',
      status: 'new',
      created_at: new Date().toISOString(),
    };

    store.handleAlertUpdate(alert);

    const updatedState = useAlertStore.getState();
    expect(updatedState.alerts).toHaveLength(1);
    expect(updatedState.pendingAlerts).toHaveLength(1);
  });

  it('should remove non-pending alerts from pending list', () => {
    const store = useAlertStore.getState();

    const alert: Alert = {
      id: '1',
      alert_type: 'fire_alarm',
      severity: 'critical',
      source: 'Test Source',
      title: 'Test Alert',
      status: 'new',
      created_at: new Date().toISOString(),
    };

    store.handleAlertUpdate(alert);
    expect(useAlertStore.getState().pendingAlerts).toHaveLength(1);

    // Acknowledge alert
    store.handleAlertUpdate({ ...alert, status: 'acknowledged' });
    expect(useAlertStore.getState().pendingAlerts).toHaveLength(0);
  });
});

describe('useResourceStore', () => {
  beforeEach(() => {
    useResourceStore.setState({
      resources: [],
      availableResources: [],
      selectedResource: null,
      isLoading: false,
      error: null,
    });
  });

  it('should handle resource updates', () => {
    const store = useResourceStore.getState();

    const resource: Resource = {
      id: '1',
      resource_type: 'vehicle',
      name: 'Engine 1',
      call_sign: 'E1',
      status: 'available',
      capabilities: ['fire'],
      agency_id: 'agency-1',
      last_status_update: new Date().toISOString(),
    };

    store.handleResourceUpdate(resource);

    const updatedState = useResourceStore.getState();
    expect(updatedState.resources).toHaveLength(1);
    expect(updatedState.availableResources).toHaveLength(1);
  });

  it('should remove unavailable resources from available list', () => {
    const store = useResourceStore.getState();

    const resource: Resource = {
      id: '1',
      resource_type: 'vehicle',
      name: 'Engine 1',
      status: 'available',
      capabilities: [],
      agency_id: 'agency-1',
      last_status_update: new Date().toISOString(),
    };

    store.handleResourceUpdate(resource);
    expect(useResourceStore.getState().availableResources).toHaveLength(1);

    // Dispatch resource
    store.handleResourceUpdate({ ...resource, status: 'dispatched' });
    expect(useResourceStore.getState().availableResources).toHaveLength(0);
  });
});
