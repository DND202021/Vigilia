/**
 * WebSocket Hook for Real-time Updates
 *
 * This hook provides optional real-time updates via Socket.IO.
 * If the connection fails (e.g., due to proxy configuration issues),
 * it fails silently without spamming the console.
 *
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
  const fetchMapBuildings = useBuildingMapStore((state) => state.fetchMapBuildings);

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
      // Only use polling - WebSocket upgrade fails through HTTP/2 proxies
      transports: ['polling'],
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
    });

    socket.on('device:alert', (data: SoundAlert) => {
      setLastEvent(`device:alert:${data.device_id}`);
      handleNewSoundAlert(data);
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

    socketRef.current = socket;
  }, [handleIncidentUpdate, handleAlertUpdate, handleResourceUpdate, handleDeviceStatusUpdate, handleNewSoundAlert, fetchMapBuildings, currentBuilding, addFloorPlan]);

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
  };
}
