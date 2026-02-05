/**
 * Reset Password Page
 * User sets new password using token from email link
 * URL format: /reset-password?token=xxx
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { authApi } from '../services/api';
import { Button, Input, Card, CardContent } from '../components/ui';

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);
  const [success, setSuccess] = useState(false);

  // Validate password requirements
  const validatePassword = (value: string) => {
    const errors: string[] = [];
    if (value.length < 12) errors.push('At least 12 characters');
    if (!/[A-Z]/.test(value)) errors.push('At least one uppercase letter');
    if (!/[a-z]/.test(value)) errors.push('At least one lowercase letter');
    if (!/[0-9]/.test(value)) errors.push('At least one number');
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(value)) errors.push('At least one special character');
    setPasswordErrors(errors);
    return errors.length === 0;
  };

  useEffect(() => {
    if (password) {
      validatePassword(password);
    }
  }, [password]);

  // No token - show error
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
        <Card className="w-full max-w-md">
          <CardContent className="py-8 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full mx-auto flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Invalid Reset Link</h2>
            <p className="text-sm text-gray-600 mb-4">
              This password reset link is invalid or has expired. Please request a new one.
            </p>
            <Link
              to="/forgot-password"
              className="text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Request new reset link
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validatePassword(password)) {
      setError('Please fix the password requirements above');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      await authApi.resetPassword(token, password);
      setSuccess(true);
      // Redirect to login after 3 seconds
      setTimeout(() => navigate('/login'), 3000);
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } };
      const detail = error.response?.data?.detail;
      if (error.response?.status === 404) {
        setError('Password reset is not available. Please contact your administrator.');
      } else if (error.response?.status === 400 || error.response?.status === 401) {
        setError('This reset link has expired or is invalid. Please request a new one.');
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Failed to reset password. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
      <Card className="w-full max-w-md">
        <div className="bg-blue-600 text-white text-center py-6">
          <div className="w-16 h-16 bg-white/10 rounded-full mx-auto flex items-center justify-center mb-3">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold">Set New Password</h1>
          <p className="text-blue-100 mt-1">ERIOP Account Recovery</p>
        </div>

        <CardContent className="pt-6">
          {success ? (
            // Success state
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-green-100 rounded-full mx-auto flex items-center justify-center">
                <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Password Reset Complete</h2>
              <p className="text-sm text-gray-600">
                Your password has been successfully reset. You will be redirected to the login page shortly.
              </p>
              <Link
                to="/login"
                className="inline-block mt-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                Go to login now
              </Link>
            </div>
          ) : (
            // Form state
            <form onSubmit={handleSubmit} className="space-y-4">
              <p className="text-sm text-gray-600">
                Enter your new password below. Make sure it meets all the security requirements.
              </p>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              <div>
                <Input
                  label="New Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter new password"
                  autoComplete="new-password"
                  disabled={isLoading}
                  autoFocus
                />
                {password && passwordErrors.length > 0 && (
                  <ul className="mt-2 text-xs space-y-1">
                    {['At least 12 characters', 'At least one uppercase letter', 'At least one lowercase letter', 'At least one number', 'At least one special character'].map((req) => (
                      <li
                        key={req}
                        className={passwordErrors.includes(req) ? 'text-red-600' : 'text-green-600'}
                      >
                        {passwordErrors.includes(req) ? 'x' : 'v'} {req}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <Input
                label="Confirm Password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                autoComplete="new-password"
                disabled={isLoading}
              />

              <Button
                type="submit"
                className="w-full"
                isLoading={isLoading}
                disabled={isLoading || passwordErrors.length > 0 || !confirmPassword}
              >
                Reset Password
              </Button>

              <div className="text-center">
                <Link
                  to="/login"
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Back to login
                </Link>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
