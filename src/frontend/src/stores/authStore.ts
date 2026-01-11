/**
 * Authentication State Store (Zustand)
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, LoginCredentials, AuthState } from '../types';
import { authApi, tokenStorage } from '../services/api';

interface AuthStore extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  setUser: (user: User | null) => void;
  setLoading: (isLoading: boolean) => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: true,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
        }),

      setLoading: (isLoading) => set({ isLoading }),

      login: async (credentials) => {
        set({ isLoading: true });
        try {
          await authApi.login(credentials);
          const user = await authApi.getCurrentUser();
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          tokenStorage.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
          throw error;
        }
      },

      logout: async () => {
        set({ isLoading: true });
        try {
          await authApi.logout();
        } finally {
          tokenStorage.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      },

      checkAuth: async () => {
        const token = tokenStorage.getAccessToken();
        if (!token) {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
          return;
        }

        try {
          const user = await authApi.getCurrentUser();
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          tokenStorage.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          });
        }
      },
    }),
    {
      name: 'eriop-auth',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
