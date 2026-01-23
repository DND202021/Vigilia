/**
 * User Management State Store (Zustand)
 */

import { create } from 'zustand';
import type { UserFull, UserCreateRequest, UserUpdateRequest, UserStats } from '../types';
import { usersApi } from '../services/api';

interface UserStore {
  users: UserFull[];
  selectedUser: UserFull | null;
  stats: UserStats | null;
  isLoading: boolean;
  error: string | null;
  total: number;
  page: number;
  pageSize: number;

  // Actions
  fetchUsers: (params?: {
    agency_id?: string;
    role_id?: string;
    is_active?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  }) => Promise<void>;
  fetchUser: (id: string) => Promise<void>;
  fetchStats: (agencyId?: string) => Promise<void>;
  createUser: (data: UserCreateRequest) => Promise<UserFull>;
  updateUser: (id: string, data: UserUpdateRequest) => Promise<UserFull>;
  deactivateUser: (id: string) => Promise<void>;
  activateUser: (id: string) => Promise<void>;
  verifyUser: (id: string) => Promise<void>;
  resetPassword: (id: string, newPassword: string) => Promise<void>;
  deleteUser: (id: string) => Promise<void>;
  setSelectedUser: (user: UserFull | null) => void;
  setPage: (page: number) => void;
  clearError: () => void;
}

export const useUserStore = create<UserStore>((set, get) => ({
  users: [],
  selectedUser: null,
  stats: null,
  isLoading: false,
  error: null,
  total: 0,
  page: 1,
  pageSize: 20,

  fetchUsers: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await usersApi.list({
        ...params,
        page: params?.page ?? get().page,
        page_size: params?.page_size ?? get().pageSize,
      });
      set({
        users: response.items,
        total: response.total,
        page: response.page,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch users',
        isLoading: false,
      });
    }
  },

  fetchUser: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const user = await usersApi.get(id);
      set({ selectedUser: user, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch user',
        isLoading: false,
      });
    }
  },

  fetchStats: async (agencyId) => {
    set({ isLoading: true, error: null });
    try {
      const stats = await usersApi.getStats(agencyId);
      set({ stats, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch user stats',
        isLoading: false,
      });
    }
  },

  createUser: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const user = await usersApi.create(data);
      set((state) => ({
        users: [user, ...state.users],
        total: state.total + 1,
        isLoading: false,
      }));
      return user;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create user',
        isLoading: false,
      });
      throw error;
    }
  },

  updateUser: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await usersApi.update(id, data);
      set((state) => ({
        users: state.users.map((u) => (u.id === id ? updated : u)),
        selectedUser: state.selectedUser?.id === id ? updated : state.selectedUser,
        isLoading: false,
      }));
      return updated;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update user',
        isLoading: false,
      });
      throw error;
    }
  },

  deactivateUser: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await usersApi.deactivate(id);
      set((state) => ({
        users: state.users.map((u) => (u.id === id ? updated : u)),
        selectedUser: state.selectedUser?.id === id ? updated : state.selectedUser,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to deactivate user',
        isLoading: false,
      });
      throw error;
    }
  },

  activateUser: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await usersApi.activate(id);
      set((state) => ({
        users: state.users.map((u) => (u.id === id ? updated : u)),
        selectedUser: state.selectedUser?.id === id ? updated : state.selectedUser,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to activate user',
        isLoading: false,
      });
      throw error;
    }
  },

  verifyUser: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await usersApi.verify(id);
      set((state) => ({
        users: state.users.map((u) => (u.id === id ? updated : u)),
        selectedUser: state.selectedUser?.id === id ? updated : state.selectedUser,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to verify user',
        isLoading: false,
      });
      throw error;
    }
  },

  resetPassword: async (id, newPassword) => {
    set({ isLoading: true, error: null });
    try {
      await usersApi.resetPassword(id, newPassword);
      set({ isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to reset password',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteUser: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await usersApi.delete(id);
      set((state) => ({
        users: state.users.filter((u) => u.id !== id),
        total: state.total - 1,
        selectedUser: state.selectedUser?.id === id ? null : state.selectedUser,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete user',
        isLoading: false,
      });
      throw error;
    }
  },

  setSelectedUser: (user) => set({ selectedUser: user }),

  setPage: (page) => set({ page }),

  clearError: () => set({ error: null }),
}));
