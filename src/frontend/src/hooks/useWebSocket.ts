/**
 * WebSocket Hook for Real-time Updates
 *
 * This hook provides real-time updates via Socket.IO using WebSocket
 * transport with polling fallback. WebSocket connections go through
 * nginx which is configured with proper upgrade headers.
 *
 * If the connection fails, it fails silently without spamming the console.
 * The app works fully without WebSocket - users just need to refresh
 * to see updates instead of getting them in real-time.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { useIncidentStore } from '../stores/incidentStore';
import { useAlertStore } from '../stores/alertStore';
import { useResourceStore } from '../stores/resourceStore';
import { useDeviceStore } from '../stores/deviceStore';
import { useAudioStore } from '../stores/audioStore';
import { useBuildingDetailStore } from '../stores/buildingDetailStore';
import { useBuildingMapStore } from '../stores/buildingMapStore';
import { useMarkerStore, initializeMarkersFromFloorPlan } from '../stores/markerStore';
import { usePresenceStore } from '../stores/presenceStore';
import { useDevicePositionStore } from '../stores/devicePositionStore';
import { tokenStorage } from '../services/api';
import type { Incident, Alert, Resource, SoundAlert, Building, FloorPlan } from '../types';

// Feature flag to completely disable WebSocket (set via env or here)
const WEBSOCKET_ENABLED = import.meta.env.VITE_WEBSOCKET_ENABLED !== 'false';

// After this many consecutive failures, stop trying
const MAX_CONSECUTIVE_FAILURES = 5;

interface WebSocketHookResult {
  isConnected: boolean;
  lastEvent: string | null;
  connect: () => void;
  disconnect: () => void;
  joinBuilding: (buildingId: string) => void;
  leaveBuilding: (buildingId: string) => void;
  // Floor Plan methods
  joinFloorPlan: (floorPlanId: string) => void;
  leaveFloorPlan: (floorPlanId: string) => void;
  sendMarkerAdd: (floorPlanId: string, marker: any, clientId: string) => void;
  sendMarkerUpdate: (floorPlanId: string, markerId: string, updates: any, clientId: string) => void;
  sendMarkerDelete: (floorPlanId: string, markerId: string) => void;
  sendPresenceHeartbeat: (floorPlanId: string, isEditing: boolean) => void;
}

export function useWebSocket(): WebSocketHookResult {
  const socketRef = useRef<Socket | null>(null);
  const failureCountRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<string | null>(null);

  const handleIncidentUpdate = useIncidentStore((state) => state.handleIncidentUpdate);
  const handleAlertUpdate = useAlertStore((state) => state.handleAlertUpdate);
  const handleResourceUpdate = useResourceStore((state) => state.handleResourceUpdate);
  const handleDeviceStatusUpdate = useDeviceStore((state) => state.handleDeviceStatusUpdate);
  const handleNewSoundAlert = useAudioStore((state) => state.handleNewSoundAlert);

  // Building store selectors
  const currentBuilding = useBuildingDetailStore((state) => state.building);
  const addFloorPlan = useBuildingDetailStore((state) => state.addFloorPlan);
  const fetchFloorPlans = useBuildingDetailStore((state) => state.fetchFloorPlans);
  const fetchMapBuildings = useBuildingMapStore((state) => state.fetchMapBuildings);

  // Marker store selectors
  const currentFloorPlanId = useMarkerStore((state) => state.currentFloorPlanId);
  const isEditing = useMarkerStore((state) => state.isEditing);

  const connect = useCallback(() => {
    // Skip if disabled or already connected
    if (!WEBSOCKET_ENABLED) return;
    if (socketRef.current?.connected) return;

    // Stop trying after too many failures
    if (failureCountRef.current >= MAX_CONSECUTIVE_FAILURES) {
      return;
    }

    const token = tokenStorage.getAccessToken();
    if (!token) return;

    const wsUrl = window.location.origin;
    const socket = io(wsUrl, {
      path: '/socket.io/',
      auth: { token },
      // Try WebSocket first, fallback to polling if upgrade fails
      transports: ['websocket', 'polling'],
      // Enable reconnection with reasonable settings
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    });

    socket.on('connect', () => {
      failureCountRef.current = 0; // Reset on success
      setIsConnected(true);
      // Only log in development
      if (import.meta.env.DEV) {
        console.log('[WS] Connected');
      }
    });

    socket.on('disconnect', (reason) => {
      setIsConnected(false);
      if (import.meta.env.DEV) {
        console.log('[WS] Disconnected:', reason);
      }
    });

    socket.on('connect_error', (err) => {
      failureCountRef.current++;
      setIsConnected(false);
      // Log error in dev mode for debugging
      if (import.meta.env.DEV) {
        console.log('[WS] Connection error:', err.message);
      }
      // Socket.io will handle reconnection automatically now
      // Only fully give up after max consecutive failures
      if (failureCountRef.current >= MAX_CONSECUTIVE_FAILURES) {
        if (import.meta.env.DEV) {
          console.log('[WS] Max failures reached, disabling real-time updates');
        }
        socket.disconnect();
        socketRef.current = null;
      }
    });

    socket.on('reconnect', (attemptNumber) => {
      failureCountRef.current = 0; // Reset on successful reconnect
      setIsConnected(true);
      if (import.meta.env.DEV) {
        console.log('[WS] Reconnected after', attemptNumber, 'attempts');
      }
    });

    socket.on('reconnect_failed', () => {
      failureCountRef.current = MAX_CONSECUTIVE_FAILURES;
      setIsConnected(false);
      if (import.meta.env.DEV) {
        console.log('[WS] Reconnection failed, giving up');
      }
    });

    // Event handlers
    socket.on('incident:created', (data: Incident) => {
      setLastEvent(`incident:created:${data.id}`);
      handleIncidentUpdate(data);
    });

    socket.on('incident:updated', (data: Incident) => {
      setLastEvent(`incident:updated:${data.id}`);
      handleIncidentUpdate(data);
    });

    socket.on('alert:created', (data: Alert) => {
      setLastEvent(`alert:created:${data.id}`);
      handleAlertUpdate(data);
    });

    socket.on('alert:updated', (data: Alert) => {
      setLastEvent(`alert:updated:${data.id}`);
      handleAlertUpdate(data);
    });

    socket.on('resource:updated', (data: Resource) => {
      setLastEvent(`resource:updated:${data.id}`);
      handleResourceUpdate(data);
    });

    // Device events
    socket.on('device:status', (data: { device_id: string; status: string; name?: string }) => {
      setLastEvent(`device:status:${data.device_id}`);
      handleDeviceStatusUpdate(data);
      // Also update device position store for floor plan overlays
      const timestamp = new Date().toISOString();
      useDevicePositionStore.getState().handleRemoteStatusChange(
        data.device_id,
        data.status as any,
        timestamp
      );
    });

    socket.on('device:alert', (data: SoundAlert) => {
      setLastEvent(`device:alert:${data.device_id}`);
      handleNewSoundAlert(data);
      // Update device status to 'alert' in both stores
      if (data.device_id) {
        const alertStatus = { device_id: data.device_id, status: 'alert' };
        handleDeviceStatusUpdate(alertStatus);
        useDevicePositionStore.getState().handleRemoteStatusChange(
          data.device_id,
          'alert',
          new Date().toISOString()
        );
      }
    });

    // Building events
    socket.on('building:created', (building: Building) => {
      setLastEvent(`building:created:${building.id}`);
      // Refresh map buildings list to include the new building
      fetchMapBuildings();
      console.log('Building created:', building.id);
    });

    socket.on('building:updated', (building: Building) => {
      setLastEvent(`building:updated:${building.id}`);
      // Refresh map buildings list to get updated data
      fetchMapBuildings();
      console.log('Building updated:', building.id);
    });

    socket.on('floor_plan:uploaded', (floorPlan: FloorPlan) => {
      setLastEvent(`floor_plan:uploaded:${floorPlan.id}`);
      // If this floor plan belongs to the currently viewed building, add it to the store
      if (currentBuilding && floorPlan.building_id === currentBuilding.id) {
        addFloorPlan(floorPlan);
      }
      console.log('Floor plan uploaded:', floorPlan.id);
    });

    socket.on('floor_plan:updated', (floorPlan: FloorPlan) => {
      setLastEvent(`floor_plan:updated:${floorPlan.id}`);
      console.log('Floor plan updated:', floorPlan.id);
    });

    // Markers updated event - refresh markers if user is viewing the affected floor plan
    socket.on('markers:updated', async (data: { floor_plan_id: string; building_id: string }) => {
      setLastEvent(`markers:updated:${data.floor_plan_id}`);
      console.log('Markers updated:', data.floor_plan_id);

      // Only refresh if we're viewing this floor plan and not currently editing
      // (to avoid overwriting the user's unsaved changes)
      if (currentFloorPlanId === data.floor_plan_id && !isEditing) {
        // Refresh floor plans to get the updated key_locations data
        // The buildingDetailStore will update its state, and we'll reinitialize markers
        // from the freshly fetched data
        if (currentBuilding && currentBuilding.id === data.building_id) {
          await fetchFloorPlans(data.building_id);
          // After fetching, get the updated floor plan from the store and reinitialize markers
          const updatedFloorPlans = useBuildingDetailStore.getState().floorPlans;
          const updatedFloorPlan = updatedFloorPlans.find((fp) => fp.id === data.floor_plan_id);
          if (updatedFloorPlan) {
            initializeMarkersFromFloorPlan(data.floor_plan_id, updatedFloorPlan.key_locations);
          }
        }
      }
    });

    // Floor Plan Real-time Events
    socket.on('marker:added', (data) => {
      const markerStore = useMarkerStore.getState();
      if (data.client_id !== markerStore.clientId) {
        markerStore.handleRemoteMarkerAdded(data.marker, data.user_id, data.client_id);
      }
    });

    socket.on('marker:updated', (data) => {
      const markerStore = useMarkerStore.getState();
      if (data.client_id !== markerStore.clientId) {
        markerStore.handleRemoteMarkerUpdated(data.marker_id, data.updates, data.user_id, data.client_id);
      }
    });

    socket.on('marker:deleted', (data) => {
      const markerStore = useMarkerStore.getState();
      markerStore.handleRemoteMarkerDeleted(data.marker_id, data.user_id);
    });

    socket.on('presence:joined_floor_plan', (data) => {
      usePresenceStore.getState().handleUserJoined({
        user_id: data.user_id,
        user_name: data.user_name,
        user_role: data.user_role,
        is_editing: false,
        joined_at: data.timestamp,
      });
    });

    socket.on('presence:left_floor_plan', (data) => {
      usePresenceStore.getState().handleUserLeft(data.user_id);
    });

    socket.on('presence:list', (data) => {
      usePresenceStore.getState().updateActiveUsers(data.active_users);
    });

    socket.on('presence:editing', (data) => {
      const presenceStore = usePresenceStore.getState();
      presenceStore.handleUserJoined({
        ...presenceStore.activeUsers.find(u => u.user_id === data.user_id),
        user_id: data.user_id,
        user_name: data.user_name,
        is_editing: data.is_editing,
        joined_at: data.timestamp,
      });
    });

    socket.on('device:position_updated', (data) => {
      useDevicePositionStore.getState().handleRemotePositionUpdate(
        data.device_id,
        data.position_x,
        data.position_y,
        data.timestamp
      );
    });

    socketRef.current = socket;
  }, [handleIncidentUpdate, handleAlertUpdate, handleResourceUpdate, handleDeviceStatusUpdate, handleNewSoundAlert, fetchMapBuildings, currentBuilding, addFloorPlan, fetchFloorPlans, currentFloorPlanId, isEditing]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  }, []);

  const joinBuilding = useCallback((buildingId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('join_building', { building_id: buildingId });
    }
  }, []);

  const leaveBuilding = useCallback((buildingId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('leave_building', { building_id: buildingId });
    }
  }, []);

  // Floor Plan methods
  const joinFloorPlan = useCallback((floorPlanId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('join_floor_plan', { floor_plan_id: floorPlanId });
      usePresenceStore.getState().setCurrentFloorPlan(floorPlanId);
    }
  }, []);

  const leaveFloorPlan = useCallback((floorPlanId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('leave_floor_plan', { floor_plan_id: floorPlanId });
      usePresenceStore.getState().setCurrentFloorPlan(null);
      usePresenceStore.getState().reset();
    }
  }, []);

  const sendMarkerAdd = useCallback((floorPlanId: string, marker: any, clientId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('marker_added', { floor_plan_id: floorPlanId, marker, client_id: clientId });
    }
  }, []);

  const sendMarkerUpdate = useCallback((floorPlanId: string, markerId: string, updates: any, clientId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('marker_updated', { floor_plan_id: floorPlanId, marker_id: markerId, updates, client_id: clientId });
    }
  }, []);

  const sendMarkerDelete = useCallback((floorPlanId: string, markerId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('marker_deleted', { floor_plan_id: floorPlanId, marker_id: markerId });
    }
  }, []);

  const sendPresenceHeartbeat = useCallback((floorPlanId: string, isEditing: boolean) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('presence_editing', { floor_plan_id: floorPlanId, is_editing: isEditing });
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    lastEvent,
    connect,
    disconnect,
    joinBuilding,
    leaveBuilding,
    // Floor Plan methods
    joinFloorPlan,
    leaveFloorPlan,
    sendMarkerAdd,
    sendMarkerUpdate,
    sendMarkerDelete,
    sendPresenceHeartbeat,
  };
}
