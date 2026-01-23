/**
 * Role Management State Store (Zustand)
 */

import { create } from 'zustand';
import type { Role, RoleCreateRequest, RoleUpdateRequest, Permission } from '../types';
import { rolesApi } from '../services/api';

interface RoleStore {
  roles: Role[];
  selectedRole: Role | null;
  availablePermissions: Permission[];
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchRoles: (includeInactive?: boolean) => Promise<void>;
  fetchRole: (id: string) => Promise<void>;
  fetchPermissions: () => Promise<void>;
  createRole: (data: RoleCreateRequest) => Promise<Role>;
  updateRole: (id: string, data: RoleUpdateRequest) => Promise<Role>;
  deleteRole: (id: string) => Promise<void>;
  setSelectedRole: (role: Role | null) => void;
  clearError: () => void;
}

export const useRoleStore = create<RoleStore>((set, get) => ({
  roles: [],
  selectedRole: null,
  availablePermissions: [],
  isLoading: false,
  error: null,

  fetchRoles: async (includeInactive) => {
    set({ isLoading: true, error: null });
    try {
      const roles = await rolesApi.list(includeInactive);
      set({ roles, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch roles',
        isLoading: false,
      });
    }
  },

  fetchRole: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const role = await rolesApi.get(id);
      set({ selectedRole: role, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch role',
        isLoading: false,
      });
    }
  },

  fetchPermissions: async () => {
    set({ isLoading: true, error: null });
    try {
      const permissions = await rolesApi.getPermissions();
      set({ availablePermissions: permissions, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch permissions',
        isLoading: false,
      });
    }
  },

  createRole: async (data) => {
    set({ isLoading: true, error: null });
    try {
      const role = await rolesApi.create(data);
      set((state) => ({
        roles: [...state.roles, role].sort((a, b) => a.hierarchy_level - b.hierarchy_level),
        isLoading: false,
      }));
      return role;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create role',
        isLoading: false,
      });
      throw error;
    }
  },

  updateRole: async (id, data) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await rolesApi.update(id, data);
      set((state) => ({
        roles: state.roles
          .map((r) => (r.id === id ? updated : r))
          .sort((a, b) => a.hierarchy_level - b.hierarchy_level),
        selectedRole: state.selectedRole?.id === id ? updated : state.selectedRole,
        isLoading: false,
      }));
      return updated;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to update role',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteRole: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await rolesApi.delete(id);
      set((state) => ({
        roles: state.roles.filter((r) => r.id !== id),
        selectedRole: state.selectedRole?.id === id ? null : state.selectedRole,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete role',
        isLoading: false,
      });
      throw error;
    }
  },

  setSelectedRole: (role) => set({ selectedRole: role }),

  clearError: () => set({ error: null }),
}));
