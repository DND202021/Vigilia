/**
 * WebSocket Hook for Real-time Updates
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { useIncidentStore } from '../stores/incidentStore';
import { useAlertStore } from '../stores/alertStore';
import { useResourceStore } from '../stores/resourceStore';
import { tokenStorage } from '../services/api';
import type { Incident, Alert, Resource } from '../types';

// Use relative path to go through nginx proxy, or fall back to localhost for dev
// WS_URL is now determined at connection time in connect() function

interface WebSocketHookResult {
  isConnected: boolean;
  lastEvent: string | null;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(): WebSocketHookResult {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<string | null>(null);

  const handleIncidentUpdate = useIncidentStore((state) => state.handleIncidentUpdate);
  const handleAlertUpdate = useAlertStore((state) => state.handleAlertUpdate);
  const handleResourceUpdate = useResourceStore((state) => state.handleResourceUpdate);

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;

    const token = tokenStorage.getAccessToken();
    if (!token) return;

    const wsUrl = window.location.origin;
    const socket = io(wsUrl, {
      path: '/socket.io/',
      auth: { token },
      // Use polling first, then upgrade to websocket - more reliable through proxy chains
      transports: ['polling', 'websocket'],
      reconnection: true,
      reconnectionAttempts: 3,
      reconnectionDelay: 2000,
      reconnectionDelayMax: 10000,
      timeout: 10000,
    });

    socket.on('connect', () => {
      setIsConnected(true);
      console.log('[WS] Connected');
    });

    socket.on('disconnect', (reason) => {
      setIsConnected(false);
      console.log('[WS] Disconnected:', reason);
    });

    socket.on('connect_error', (error) => {
      console.error('[WS] Connection error:', error.message);
      setIsConnected(false);
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

    socketRef.current = socket;
  }, [handleIncidentUpdate, handleAlertUpdate, handleResourceUpdate]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
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
  };
}
