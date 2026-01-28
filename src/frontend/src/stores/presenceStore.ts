/**
 * Presence Store (Zustand)
 *
 * Manages user presence tracking for collaborative floor plan editing.
 */

import { create } from 'zustand';
import type { UserPresence } from '../types';

interface PresenceStore {
  // State
  currentFloorPlanId: string | null;
  activeUsers: UserPresence[];
  isEditing: boolean;
  lastHeartbeat: string | null;
  heartbeatInterval: ReturnType<typeof setInterval> | null;

  // Actions
  setCurrentFloorPlan: (floorPlanId: string | null) => void;
  updateActiveUsers: (users: UserPresence[]) => void;
  handleUserJoined: (user: UserPresence) => void;
  handleUserLeft: (userId: string) => void;
  setEditingMode: (isEditing: boolean) => void;
  updateHeartbeat: () => void;
  startHeartbeat: (sendHeartbeat: () => void) => void;
  stopHeartbeat: () => void;
  reset: () => void;
}

const HEARTBEAT_INTERVAL = 5000; // 5 seconds

const initialState = {
  currentFloorPlanId: null as string | null,
  activeUsers: [] as UserPresence[],
  isEditing: false,
  lastHeartbeat: null as string | null,
  heartbeatInterval: null as ReturnType<typeof setInterval> | null,
};

export const usePresenceStore = create<PresenceStore>((set, get) => ({
  ...initialState,

  setCurrentFloorPlan: (floorPlanId) => {
    set({ currentFloorPlanId: floorPlanId, activeUsers: [] });
  },

  updateActiveUsers: (users) => {
    set({ activeUsers: users });
  },

  handleUserJoined: (user) => {
    set((state) => {
      // Avoid duplicates
      const exists = state.activeUsers.some((u) => u.user_id === user.user_id);
      if (exists) {
        // Update existing user
        return {
          activeUsers: state.activeUsers.map((u) =>
            u.user_id === user.user_id ? { ...u, ...user } : u
          ),
        };
      }
      return { activeUsers: [...state.activeUsers, user] };
    });
  },

  handleUserLeft: (userId) => {
    set((state) => ({
      activeUsers: state.activeUsers.filter((u) => u.user_id !== userId),
    }));
  },

  setEditingMode: (isEditing) => {
    set({ isEditing });
  },

  updateHeartbeat: () => {
    set({ lastHeartbeat: new Date().toISOString() });
  },

  startHeartbeat: (sendHeartbeat) => {
    const { heartbeatInterval } = get();

    // Clear existing interval if any
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval);
    }

    // Send initial heartbeat
    sendHeartbeat();

    // Set up interval
    const interval = setInterval(() => {
      sendHeartbeat();
      get().updateHeartbeat();
    }, HEARTBEAT_INTERVAL);

    set({ heartbeatInterval: interval, lastHeartbeat: new Date().toISOString() });
  },

  stopHeartbeat: () => {
    const { heartbeatInterval } = get();
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval);
    }
    set({ heartbeatInterval: null });
  },

  reset: () => {
    const { heartbeatInterval } = get();
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval);
    }
    set(initialState);
  },
}));
