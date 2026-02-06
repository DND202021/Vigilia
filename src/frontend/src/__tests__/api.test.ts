/**
 * API Service Tests
 *
 * Note: These tests focus on API call signatures and response handling.
 * localStorage mocking is simplified to avoid conflicts with setup.ts.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';
import { authApi } from '../services/api';

// Mock axios
vi.mock('axios', () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn(),
      },
      response: {
        use: vi.fn(),
      },
    },
  };
  return {
    default: mockAxios,
  };
});

describe('authApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should call login endpoint with correct params', async () => {
      const mockResponse = {
        data: {
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
          token_type: 'bearer',
          mfa_required: false,
        },
      };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.login({
        username: 'test@example.com',
        password: 'password123',
      });

      expect(result).toEqual(mockResponse.data);
      expect(axios.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password123',
      });
    });

    it('should return MFA required response', async () => {
      const mockResponse = {
        data: {
          access_token: '',
          refresh_token: '',
          token_type: 'bearer',
          mfa_required: true,
          mfa_temp_token: 'temp-token-123',
        },
      };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.login({
        username: 'test@example.com',
        password: 'password123',
      });

      expect(result.mfa_required).toBe(true);
      expect(result.mfa_temp_token).toBe('temp-token-123');
    });
  });

  describe('logout', () => {
    it('should call logout endpoint', async () => {
      vi.mocked(axios.post).mockResolvedValue({ data: {} });

      await authApi.logout();

      expect(axios.post).toHaveBeenCalledWith('/auth/logout');
    });
  });

  describe('getCurrentUser', () => {
    it('should fetch current user', async () => {
      const mockUser = {
        id: 'user-1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'dispatcher',
      };

      vi.mocked(axios.get).mockResolvedValue({ data: mockUser });

      const result = await authApi.getCurrentUser();

      expect(result).toEqual(mockUser);
      expect(axios.get).toHaveBeenCalledWith('/auth/me');
    });
  });

  describe('changePassword', () => {
    it('should call change password endpoint', async () => {
      vi.mocked(axios.post).mockResolvedValue({ data: {} });

      await authApi.changePassword('old-password', 'new-password');

      expect(axios.post).toHaveBeenCalledWith('/auth/change-password', {
        current_password: 'old-password',
        new_password: 'new-password',
      });
    });
  });

  describe('requestPasswordReset', () => {
    it('should request password reset', async () => {
      const mockResponse = { data: { message: 'Reset email sent' } };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.requestPasswordReset('test@example.com');

      expect(result).toEqual(mockResponse.data);
      expect(axios.post).toHaveBeenCalledWith('/auth/forgot-password', {
        email: 'test@example.com',
      });
    });
  });

  describe('resetPassword', () => {
    it('should reset password with token', async () => {
      const mockResponse = { data: { message: 'Password reset successful' } };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.resetPassword('reset-token-123', 'new-password');

      expect(result).toEqual(mockResponse.data);
      expect(axios.post).toHaveBeenCalledWith('/auth/reset-password', {
        token: 'reset-token-123',
        new_password: 'new-password',
      });
    });
  });

  describe('MFA methods', () => {
    it('should setup MFA', async () => {
      const mockResponse = {
        data: {
          secret: 'mfa-secret-123',
          qr_code: 'data:image/png;base64,...',
        },
      };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.mfaSetup();

      expect(result).toEqual(mockResponse.data);
      expect(axios.post).toHaveBeenCalledWith('/auth/mfa/setup');
    });

    it('should confirm MFA', async () => {
      const mockResponse = { data: { message: 'MFA enabled' } };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.mfaConfirm('secret-123', '123456');

      expect(result).toEqual(mockResponse.data);
      expect(axios.post).toHaveBeenCalledWith('/auth/mfa/confirm', {
        secret: 'secret-123',
        code: '123456',
      });
    });

    it('should disable MFA', async () => {
      const mockResponse = { data: { message: 'MFA disabled' } };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.mfaDisable('123456');

      expect(result).toEqual(mockResponse.data);
      expect(axios.post).toHaveBeenCalledWith('/auth/mfa/disable', { code: '123456' });
    });

    it('should complete MFA login', async () => {
      const mockResponse = {
        data: {
          access_token: 'mfa-access-token',
          refresh_token: 'mfa-refresh-token',
          token_type: 'bearer',
        },
      };

      vi.mocked(axios.post).mockResolvedValue(mockResponse);

      const result = await authApi.mfaComplete('temp-token-456', '123456');

      expect(result).toEqual(mockResponse.data);
      expect(axios.post).toHaveBeenCalledWith(
        '/auth/mfa/complete?mfa_temp_token=temp-token-456',
        { code: '123456' }
      );
    });
  });
});
