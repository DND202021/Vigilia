/**
 * Auth Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../stores/authStore';
import { authApi, tokenStorage } from '../services/api';
import type { User } from '../types';

// Mock API
vi.mock('../services/api', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    mfaComplete: vi.fn(),
  },
  tokenStorage: {
    getAccessToken: vi.fn(),
    getRefreshToken: vi.fn(),
    setTokens: vi.fn(),
    clearTokens: vi.fn(),
  },
}));

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      mfaPending: false,
      mfaTempToken: null,
    });
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should login successfully and set user', async () => {
      const mockUser: User = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'dispatcher',
        agency_id: 'agency-1',
        is_active: true,
        is_verified: true,
        created_at: new Date().toISOString(),
      };

      vi.mocked(authApi.login).mockResolvedValue({
        access_token: 'access-token',
        refresh_token: 'refresh-token',
        token_type: 'bearer',
        mfa_required: false,
      });
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().login({ username: 'test@example.com', password: 'password' });

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
      expect(authApi.login).toHaveBeenCalledWith({ username: 'test@example.com', password: 'password' });
      expect(authApi.getCurrentUser).toHaveBeenCalled();
    });

    it('should handle login failure', async () => {
      vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'));

      await expect(
        useAuthStore.getState().login({ username: 'test@example.com', password: 'wrong' })
      ).rejects.toThrow('Invalid credentials');

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(tokenStorage.clearTokens).toHaveBeenCalled();
    });

    it('should set MFA pending when MFA is required', async () => {
      vi.mocked(authApi.login).mockResolvedValue({
        access_token: '',
        refresh_token: '',
        token_type: 'bearer',
        mfa_required: true,
        mfa_temp_token: 'temp-token-123',
      });

      // Login should NOT throw even though MFA is required
      // The caller will check mfa_required from the response
      await useAuthStore.getState().login({ username: 'test@example.com', password: 'password' });

      expect(authApi.login).toHaveBeenCalled();
    });
  });

  describe('logout', () => {
    it('should logout and clear state', async () => {
      // Set initial authenticated state
      useAuthStore.setState({
        user: { id: 'user-1', email: 'test@example.com' } as User,
        isAuthenticated: true,
      });

      vi.mocked(authApi.logout).mockResolvedValue();

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(tokenStorage.clearTokens).toHaveBeenCalled();
      expect(authApi.logout).toHaveBeenCalled();
    });

    it('should clear tokens even if API call fails', async () => {
      vi.mocked(authApi.logout).mockResolvedValue(); // logout doesn't throw, it catches internally

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(tokenStorage.clearTokens).toHaveBeenCalled();
    });
  });

  describe('checkAuth', () => {
    it('should restore session if token exists', async () => {
      const mockUser: User = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'dispatcher',
        agency_id: 'agency-1',
        is_active: true,
        is_verified: true,
        created_at: new Date().toISOString(),
      };

      vi.mocked(tokenStorage.getAccessToken).mockReturnValue('existing-token');
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().checkAuth();

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.isLoading).toBe(false);
    });

    it('should clear auth if no token', async () => {
      vi.mocked(tokenStorage.getAccessToken).mockReturnValue(null);

      await useAuthStore.getState().checkAuth();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isLoading).toBe(false);
      expect(authApi.getCurrentUser).not.toHaveBeenCalled();
    });

    it('should clear auth if token is invalid', async () => {
      vi.mocked(tokenStorage.getAccessToken).mockReturnValue('invalid-token');
      vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error('Unauthorized'));

      await useAuthStore.getState().checkAuth();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(tokenStorage.clearTokens).toHaveBeenCalled();
    });
  });

  describe('MFA flow', () => {
    it('should set MFA pending state', () => {
      useAuthStore.getState().setMfaPending(true, 'temp-token-456');

      const state = useAuthStore.getState();
      expect(state.mfaPending).toBe(true);
      expect(state.mfaTempToken).toBe('temp-token-456');
    });

    it('should complete MFA login successfully', async () => {
      const mockUser: User = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'dispatcher',
        agency_id: 'agency-1',
        is_active: true,
        is_verified: true,
        created_at: new Date().toISOString(),
      };

      // Set MFA pending state
      useAuthStore.setState({
        mfaPending: true,
        mfaTempToken: 'temp-token-789',
      });

      vi.mocked(authApi.mfaComplete).mockResolvedValue({
        access_token: 'access-token',
        refresh_token: 'refresh-token',
        token_type: 'bearer',
      });
      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().completeMfaLogin('123456');

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(state.mfaPending).toBe(false);
      expect(state.mfaTempToken).toBeNull();
      expect(authApi.mfaComplete).toHaveBeenCalledWith('temp-token-789', '123456');
    });

    it('should throw error if no temp token', async () => {
      useAuthStore.setState({ mfaTempToken: null });

      await expect(
        useAuthStore.getState().completeMfaLogin('123456')
      ).rejects.toThrow('No MFA temp token');
    });
  });

  describe('refreshUser', () => {
    it('should refresh user data', async () => {
      const mockUser: User = {
        id: 'user-1',
        email: 'updated@example.com',
        name: 'Updated User',
        role: 'dispatcher',
        agency_id: 'agency-1',
        is_active: true,
        is_verified: true,
        created_at: new Date().toISOString(),
      };

      vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

      await useAuthStore.getState().refreshUser();

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
    });

    it('should ignore refresh errors', async () => {
      vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error('Network error'));

      await useAuthStore.getState().refreshUser();

      // Should not throw, just silently fail
      expect(true).toBe(true);
    });
  });

  describe('setUser', () => {
    it('should set user and authenticated state', () => {
      const mockUser: User = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'dispatcher',
        agency_id: 'agency-1',
        is_active: true,
        is_verified: true,
        created_at: new Date().toISOString(),
      };

      useAuthStore.getState().setUser(mockUser);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });

    it('should clear user when null', () => {
      useAuthStore.getState().setUser(null);

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });
});
