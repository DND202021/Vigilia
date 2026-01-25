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
import { tokenStorage } from '../services/api';
import type { Incident, Alert, Resource } from '../types';

// Feature flag to completely disable WebSocket (set via env or here)
const WEBSOCKET_ENABLED = import.meta.env.VITE_WEBSOCKET_ENABLED !== 'false';

// After this many consecutive failures, stop trying
const MAX_CONSECUTIVE_FAILURES = 2;

interface WebSocketHookResult {
  isConnected: boolean;
  lastEvent: string | null;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(): WebSocketHookResult {
  const socketRef = useRef<Socket | null>(null);
  const failureCountRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<string | null>(null);

  const handleIncidentUpdate = useIncidentStore((state) => state.handleIncidentUpdate);
  const handleAlertUpdate = useAlertStore((state) => state.handleAlertUpdate);
  const handleResourceUpdate = useResourceStore((state) => state.handleResourceUpdate);

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
      reconnection: false, // Don't auto-reconnect, we'll handle it manually
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

    socket.on('connect_error', () => {
      failureCountRef.current++;
      setIsConnected(false);
      // Silently fail - WebSocket is optional
      // The app works fine without real-time updates
      if (failureCountRef.current >= MAX_CONSECUTIVE_FAILURES) {
        socket.disconnect();
        socketRef.current = null;
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
