/**
 * useFloorPlanSync Hook
 *
 * Orchestrates real-time floor plan synchronization for collaborative editing.
 * Manages WebSocket room joining/leaving, presence heartbeat, marker operations
 * with optimistic updates, and device position synchronization.
 */

import { useEffect, useRef, useCallback, useState, useMemo } from 'react';
import { useWebSocket } from './useWebSocket';
import { usePresenceStore } from '../stores/presenceStore';
import { useMarkerStore } from '../stores/markerStore';
import { useDevicePositionStore } from '../stores/devicePositionStore';
import type {
  UserPresence,
  MarkerConflict,
  DeviceFloorPosition,
  FloorKeyLocation,
} from '../types';

// ============================================================================
// Types
// ============================================================================

export interface UseFloorPlanSyncOptions {
  floorPlanId: string | null;
  userId: string;
  userName: string;
  userRole?: string;
  enabled?: boolean;
}

export interface UseFloorPlanSyncReturn {
  // Connection state
  isConnected: boolean;
  isSyncing: boolean;

  // Presence
  activeUsers: UserPresence[];
  setEditing: (isEditing: boolean) => void;

  // Markers
  addMarker: (marker: Omit<FloorKeyLocation, 'id'>) => Promise<string>;
  updateMarker: (markerId: string, updates: Partial<FloorKeyLocation>) => Promise<void>;
  deleteMarker: (markerId: string) => Promise<void>;
  conflicts: MarkerConflict[];
  resolveConflict: (conflictId: string, resolution: 'keep_local' | 'accept_remote' | 'merge') => void;

  // Device positions
  devicePositions: Record<string, DeviceFloorPosition>;

  // Error handling
  error: string | null;
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useFloorPlanSync(options: UseFloorPlanSyncOptions): UseFloorPlanSyncReturn {
  const { floorPlanId, userId, userName, userRole, enabled = true } = options;

  // Refs to track current values and avoid stale closures
  const floorPlanIdRef = useRef<string | null>(floorPlanId);
  const userIdRef = useRef(userId);
  const userNameRef = useRef(userName);
  const userRoleRef = useRef(userRole);

  // Local state
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WebSocket hook
  const {
    isConnected,
    joinFloorPlan,
    leaveFloorPlan,
    sendMarkerAdd,
    sendMarkerUpdate,
    sendMarkerDelete,
    sendPresenceHeartbeat,
  } = useWebSocket();

  // Store selectors
  const activeUsers = usePresenceStore((state) => state.activeUsers);
  const setEditingMode = usePresenceStore((state) => state.setEditingMode);
  const startHeartbeat = usePresenceStore((state) => state.startHeartbeat);
  const stopHeartbeat = usePresenceStore((state) => state.stopHeartbeat);
  const isEditing = usePresenceStore((state) => state.isEditing);

  const markers = useMarkerStore((state) => state.markers);
  const conflicts = useMarkerStore((state) => state.conflicts);
  const clientId = useMarkerStore((state) => state.clientId);
  const storeAddMarker = useMarkerStore((state) => state.addMarker);
  const storeUpdateMarker = useMarkerStore((state) => state.updateMarker);
  const storeDeleteMarker = useMarkerStore((state) => state.deleteMarker);
  const addOptimisticMarker = useMarkerStore((state) => state.addOptimisticMarker);
  const confirmOptimisticMarker = useMarkerStore((state) => state.confirmOptimisticMarker);
  const resolveConflictStore = useMarkerStore((state) => state.resolveConflict);

  const devicePositions = useDevicePositionStore((state) => state.positions);
  const loadDevicesForFloorPlan = useDevicePositionStore((state) => state.loadDevicesForFloorPlan);
  const clearPositions = useDevicePositionStore((state) => state.clearPositions);

  // Keep refs in sync
  useEffect(() => {
    floorPlanIdRef.current = floorPlanId;
    userIdRef.current = userId;
    userNameRef.current = userName;
    userRoleRef.current = userRole;
  }, [floorPlanId, userId, userName, userRole]);

  // ============================================================================
  // Device Loading (independent of WebSocket)
  // ============================================================================

  useEffect(() => {
    if (!enabled || !floorPlanId) {
      return;
    }

    // Load devices for this floor plan (regardless of WebSocket connection)
    loadDevicesForFloorPlan(floorPlanId).catch((err) => {
      console.error('[FloorPlanSync] Failed to load devices:', err);
    });

    // Cleanup function - clear positions when leaving floor plan
    return () => {
      clearPositions();
    };
  }, [enabled, floorPlanId, loadDevicesForFloorPlan, clearPositions]);

  // ============================================================================
  // Room Join/Leave Management (requires WebSocket connection)
  // ============================================================================

  useEffect(() => {
    if (!enabled || !floorPlanId || !isConnected) {
      return;
    }

    // Join the floor plan room
    joinFloorPlan(floorPlanId);

    // Start presence heartbeat
    const sendHeartbeatFn = () => {
      if (floorPlanIdRef.current) {
        sendPresenceHeartbeat(floorPlanIdRef.current, isEditing);
      }
    };
    startHeartbeat(sendHeartbeatFn);

    // Cleanup function
    return () => {
      if (floorPlanId) {
        leaveFloorPlan(floorPlanId);
      }
      stopHeartbeat();
    };
  }, [
    enabled,
    floorPlanId,
    isConnected,
    joinFloorPlan,
    leaveFloorPlan,
    startHeartbeat,
    stopHeartbeat,
    sendPresenceHeartbeat,
    isEditing,
  ]);

  // ============================================================================
  // Presence Methods
  // ============================================================================

  const setEditing = useCallback((editing: boolean) => {
    setEditingMode(editing);

    // Send heartbeat with updated editing status
    if (floorPlanIdRef.current && isConnected) {
      sendPresenceHeartbeat(floorPlanIdRef.current, editing);
    }
  }, [setEditingMode, isConnected, sendPresenceHeartbeat]);

  // ============================================================================
  // Marker Methods with Optimistic Updates
  // ============================================================================

  const addMarker = useCallback(async (marker: Omit<FloorKeyLocation, 'id'>): Promise<string> => {
    const currentFloorPlanId = floorPlanIdRef.current;
    if (!currentFloorPlanId) {
      throw new Error('No floor plan selected');
    }

    setIsSyncing(true);
    setError(null);

    try {
      // Create optimistic marker
      const optimisticMarker = addOptimisticMarker(marker as FloorKeyLocation);

      // Also add to local markers for immediate rendering
      const newMarkerId = crypto.randomUUID();
      storeAddMarker({
        ...marker,
        type: marker.type,
        name: marker.name,
        x: marker.x ?? 0,
        y: marker.y ?? 0,
      });

      // Send via WebSocket
      if (isConnected) {
        sendMarkerAdd(currentFloorPlanId, {
          ...marker,
          id: newMarkerId,
        }, clientId);
      }

      // In a real implementation, we'd wait for server confirmation
      // For now, we simulate immediate success
      confirmOptimisticMarker(optimisticMarker.client_id, newMarkerId);

      setIsSyncing(false);
      return newMarkerId;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add marker';
      setError(errorMessage);
      setIsSyncing(false);
      throw err;
    }
  }, [
    addOptimisticMarker,
    storeAddMarker,
    confirmOptimisticMarker,
    isConnected,
    sendMarkerAdd,
    clientId,
  ]);

  const updateMarker = useCallback(async (markerId: string, updates: Partial<FloorKeyLocation>): Promise<void> => {
    const currentFloorPlanId = floorPlanIdRef.current;
    if (!currentFloorPlanId) {
      throw new Error('No floor plan selected');
    }

    setIsSyncing(true);
    setError(null);

    // Store original state for rollback
    const originalMarker = markers.find((m) => m.id === markerId);
    if (!originalMarker) {
      setError('Marker not found');
      setIsSyncing(false);
      return;
    }

    try {
      // Optimistic update
      storeUpdateMarker(markerId, updates);

      // Send via WebSocket
      if (isConnected) {
        sendMarkerUpdate(currentFloorPlanId, markerId, updates, clientId);
      }

      setIsSyncing(false);
    } catch (err) {
      // Rollback on failure
      storeUpdateMarker(markerId, {
        type: originalMarker.type,
        name: originalMarker.name,
        x: originalMarker.x,
        y: originalMarker.y,
        description: originalMarker.description,
      });

      const errorMessage = err instanceof Error ? err.message : 'Failed to update marker';
      setError(errorMessage);
      setIsSyncing(false);
      throw err;
    }
  }, [
    markers,
    storeUpdateMarker,
    isConnected,
    sendMarkerUpdate,
    clientId,
  ]);

  const deleteMarkerFn = useCallback(async (markerId: string): Promise<void> => {
    const currentFloorPlanId = floorPlanIdRef.current;
    if (!currentFloorPlanId) {
      throw new Error('No floor plan selected');
    }

    setIsSyncing(true);
    setError(null);

    // Store original state for rollback
    const originalMarker = markers.find((m) => m.id === markerId);

    try {
      // Optimistic delete
      storeDeleteMarker(markerId);

      // Send via WebSocket
      if (isConnected) {
        sendMarkerDelete(currentFloorPlanId, markerId);
      }

      setIsSyncing(false);
    } catch (err) {
      // Rollback on failure
      if (originalMarker) {
        storeAddMarker({
          type: originalMarker.type,
          name: originalMarker.name,
          x: originalMarker.x,
          y: originalMarker.y,
          description: originalMarker.description,
        });
      }

      const errorMessage = err instanceof Error ? err.message : 'Failed to delete marker';
      setError(errorMessage);
      setIsSyncing(false);
      throw err;
    }
  }, [
    markers,
    storeDeleteMarker,
    storeAddMarker,
    isConnected,
    sendMarkerDelete,
  ]);

  // ============================================================================
  // Conflict Resolution
  // ============================================================================

  const resolveConflict = useCallback((conflictId: string, resolution: 'keep_local' | 'accept_remote' | 'merge') => {
    // Find the conflict
    const conflict = conflicts.find((c) => c.marker_id === conflictId);
    if (!conflict) {
      setError('Conflict not found');
      return;
    }

    switch (resolution) {
      case 'keep_local':
        resolveConflictStore(conflictId, 'local_wins', false);
        break;
      case 'accept_remote':
        resolveConflictStore(conflictId, 'server_authoritative', true);
        break;
      case 'merge':
        // For merge, we combine position from local and properties from remote
        // This is a simplified merge strategy
        if (conflict.conflict_type === 'position') {
          // Keep local position, accept other properties from server
          const mergedMarker = {
            ...conflict.server_version,
            x: conflict.local_version.x,
            y: conflict.local_version.y,
          };
          storeUpdateMarker(conflictId, mergedMarker);
        } else {
          // For property conflicts, prefer server version
          resolveConflictStore(conflictId, 'server_authoritative', true);
        }
        break;
    }

    setError(null);
  }, [conflicts, resolveConflictStore, storeUpdateMarker]);

  // ============================================================================
  // Return Value
  // ============================================================================

  return useMemo(() => ({
    // Connection state
    isConnected,
    isSyncing,

    // Presence
    activeUsers,
    setEditing,

    // Markers
    addMarker,
    updateMarker,
    deleteMarker: deleteMarkerFn,
    conflicts,
    resolveConflict,

    // Device positions
    devicePositions,

    // Error handling
    error,
  }), [
    isConnected,
    isSyncing,
    activeUsers,
    setEditing,
    addMarker,
    updateMarker,
    deleteMarkerFn,
    conflicts,
    resolveConflict,
    devicePositions,
    error,
  ]);
}

// Default export
export default useFloorPlanSync;
