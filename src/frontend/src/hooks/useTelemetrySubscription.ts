/**
 * useTelemetrySubscription Hook
 *
 * Subscribes to Socket.IO telemetry events for a specific device+metric.
 * Throttles incoming events at 1.5s intervals using lodash.throttle.
 * Automatically joins/leaves device telemetry rooms via Socket.IO.
 */
import { useEffect, useRef, useMemo, useState } from 'react';
import { throttle } from 'lodash';
import { io, Socket } from 'socket.io-client';
import { useTelemetryStore } from '../stores/telemetryStore';
import { tokenStorage } from '../services/api';
import type { TelemetryEvent } from '../types';

interface UseTelemetrySubscriptionParams {
  deviceId: string | null;
  metricName: string | null;
}

interface UseTelemetrySubscriptionResult {
  isSubscribed: boolean;
}

export function useTelemetrySubscription({
  deviceId,
  metricName,
}: UseTelemetrySubscriptionParams): UseTelemetrySubscriptionResult {
  const socketRef = useRef<Socket | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);

  // Create throttled handler using useMemo so it's stable across renders
  const throttledHandler = useMemo(() => {
    return throttle((event: TelemetryEvent) => {
      // Filter by metricName if specified
      if (metricName && event.metric_name !== metricName) {
        return;
      }

      // Add data point to store directly (not via hook to avoid re-renders)
      useTelemetryStore.getState().addDataPoint(
        event.device_id,
        event.metric_name,
        {
          time: event.time,
          value: event.value,
        }
      );
    }, 1500);
  }, [metricName]);

  useEffect(() => {
    // Skip if no deviceId provided
    if (!deviceId) {
      setIsSubscribed(false);
      return;
    }

    // Get auth token
    const token = tokenStorage.getAccessToken();
    if (!token) {
      setIsSubscribed(false);
      return;
    }

    // Connect to Socket.IO
    const wsUrl = window.location.origin;
    const socket = io(wsUrl, {
      path: '/socket.io/',
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 10000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      // Join device telemetry room
      socket.emit('join_device_telemetry', { device_id: deviceId });
      setIsSubscribed(true);

      // Track subscription in store
      if (metricName) {
        useTelemetryStore.getState().addSubscription(deviceId, metricName);
      }
    });

    socket.on('disconnect', () => {
      setIsSubscribed(false);
    });

    // Listen for telemetry:data events
    socket.on('telemetry:data', throttledHandler);

    // Cleanup function
    return () => {
      // Cancel throttled function
      throttledHandler.cancel();

      // Leave room
      if (socket.connected) {
        socket.emit('leave_device_telemetry', { device_id: deviceId });
      }

      // Remove subscription from store
      if (metricName) {
        useTelemetryStore.getState().removeSubscription(deviceId, metricName);
      }

      // Remove listener and disconnect
      socket.off('telemetry:data', throttledHandler);
      socket.disconnect();
      socketRef.current = null;
      setIsSubscribed(false);
    };
  }, [deviceId, metricName, throttledHandler]);

  return { isSubscribed };
}
