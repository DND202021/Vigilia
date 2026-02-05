/**
 * Login Page
 * Two-step flow: 1) Username/Password 2) MFA code (if enabled)
 */

import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../services/api';
import { Button, Input, Card, CardContent } from '../components/ui';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isLoading, setUser, setMfaPending, completeMfaLogin } = useAuthStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [error, setError] = useState('');
  const [mfaStep, setMfaStep] = useState(false);
  const [localLoading, setLocalLoading] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  // Redirect if already authenticated
  if (isAuthenticated) {
    navigate(from, { replace: true });
    return null;
  }

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username || !password) {
      setError('Please enter username and password');
      return;
    }

    setLocalLoading(true);

    try {
      const response = await authApi.login({ username, password });

      if (response.mfa_required && response.mfa_temp_token) {
        // MFA required - show code input
        setMfaStep(true);
        setMfaPending(true, response.mfa_temp_token);
      } else {
        // No MFA - complete login
        const user = await authApi.getCurrentUser();
        setUser(user);
        navigate(from, { replace: true });
      }
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const detail = axiosError.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Invalid username or password');
      }
    } finally {
      setLocalLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (mfaCode.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setLocalLoading(true);

    try {
      await completeMfaLogin(mfaCode);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const detail = axiosError.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Invalid verification code');
      }
    } finally {
      setLocalLoading(false);
    }
  };

  const handleBackToPassword = () => {
    setMfaStep(false);
    setMfaCode('');
    setError('');
    setMfaPending(false);
  };

  const showLoading = isLoading || localLoading;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
      <Card className="w-full max-w-md">
        <div className="bg-blue-600 text-white text-center py-6">
          <div className="w-16 h-16 bg-white/10 rounded-full mx-auto flex items-center justify-center mb-3">
            <span className="text-3xl font-bold">E</span>
          </div>
          <h1 className="text-2xl font-bold">ERIOP</h1>
          <p className="text-blue-100 mt-1">Emergency Response IoT Platform</p>
        </div>

        <CardContent className="pt-6">
          {!mfaStep ? (
            // Step 1: Username/Password
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              <Input
                label="Username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                autoComplete="username"
                disabled={showLoading}
              />

              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                disabled={showLoading}
              />

              <Button
                type="submit"
                className="w-full"
                isLoading={showLoading}
                disabled={showLoading}
              >
                Sign In
              </Button>

              <div className="text-center">
                <Link
                  to="/forgot-password"
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  Forgot password?
                </Link>
              </div>
            </form>
          ) : (
            // Step 2: MFA Code
            <form onSubmit={handleMfaSubmit} className="space-y-4">
              <div className="text-center mb-4">
                <div className="w-12 h-12 bg-blue-100 rounded-full mx-auto flex items-center justify-center mb-3">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <h2 className="text-lg font-semibold text-gray-900">Two-Factor Authentication</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Enter the 6-digit code from your authenticator app
                </p>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              <Input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000"
                className="text-center text-2xl tracking-widest font-mono"
                autoFocus
                disabled={showLoading}
              />

              <Button
                type="submit"
                className="w-full"
                isLoading={showLoading}
                disabled={showLoading || mfaCode.length !== 6}
              >
                Verify
              </Button>

              <button
                type="button"
                onClick={handleBackToPassword}
                className="w-full text-sm text-gray-500 hover:text-gray-700"
                disabled={showLoading}
              >
                Back to login
              </button>
            </form>
          )}

          <div className="mt-6 text-center text-sm text-gray-500">
            <p>Emergency Response Personnel Only</p>
            <p className="mt-1">Contact your administrator for access</p>
            <Link to="/register" className="block mt-2 text-blue-600 hover:text-blue-700">
              Create an account
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
