/**
 * Registration Page
 * Public registration for new users
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { authApi } from '../services/api';
import { Button, Input, Card, CardContent } from '../components/ui';

interface PasswordValidation {
  minLength: boolean;
  hasUppercase: boolean;
  hasLowercase: boolean;
  hasNumber: boolean;
  hasSpecial: boolean;
}

function validatePassword(password: string): PasswordValidation {
  return {
    minLength: password.length >= 12,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };
}

function isPasswordValid(validation: PasswordValidation): boolean {
  return Object.values(validation).every(Boolean);
}

export function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const passwordValidation = validatePassword(password);
  const passwordsMatch = password === confirmPassword && password.length > 0;

  // Redirect if already authenticated
  if (isAuthenticated) {
    navigate('/', { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validate
    if (!email || !password || !fullName) {
      setError('Please fill in all fields');
      return;
    }

    if (!isPasswordValid(passwordValidation)) {
      setError('Password does not meet requirements');
      return;
    }

    if (!passwordsMatch) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      await authApi.register({
        email,
        password,
        full_name: fullName,
      });
      setSuccess(true);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string | Array<{ msg?: string }> } } };
      const detail = axiosError.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg || String(d)).join(', '));
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
        <Card className="w-full max-w-md">
          <div className="bg-green-600 text-white text-center py-6">
            <div className="w-16 h-16 bg-white/10 rounded-full mx-auto flex items-center justify-center mb-3">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold">Registration Successful</h1>
          </div>
          <CardContent className="pt-6 text-center">
            <p className="text-gray-600 mb-4">
              Your account has been created. Please contact your administrator to verify your account before signing in.
            </p>
            <Link to="/login">
              <Button className="w-full">Go to Sign In</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4 py-8">
      <Card className="w-full max-w-md">
        <div className="bg-blue-600 text-white text-center py-6">
          <div className="w-16 h-16 bg-white/10 rounded-full mx-auto flex items-center justify-center mb-3">
            <span className="text-3xl font-bold">E</span>
          </div>
          <h1 className="text-2xl font-bold">Create Account</h1>
          <p className="text-blue-100 mt-1">Emergency Response IoT Platform</p>
        </div>

        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <Input
              label="Full Name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Enter your full name"
              autoComplete="name"
              disabled={isLoading}
              required
            />

            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              autoComplete="email"
              disabled={isLoading}
              required
            />

            <div>
              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create a password"
                autoComplete="new-password"
                disabled={isLoading}
                required
              />
              <div className="mt-2 space-y-1 text-xs">
                <PasswordRequirement met={passwordValidation.minLength}>
                  At least 12 characters
                </PasswordRequirement>
                <PasswordRequirement met={passwordValidation.hasUppercase}>
                  At least one uppercase letter
                </PasswordRequirement>
                <PasswordRequirement met={passwordValidation.hasLowercase}>
                  At least one lowercase letter
                </PasswordRequirement>
                <PasswordRequirement met={passwordValidation.hasNumber}>
                  At least one number
                </PasswordRequirement>
                <PasswordRequirement met={passwordValidation.hasSpecial}>
                  At least one special character
                </PasswordRequirement>
              </div>
            </div>

            <div>
              <Input
                label="Confirm Password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm your password"
                autoComplete="new-password"
                disabled={isLoading}
                required
              />
              {confirmPassword && !passwordsMatch && (
                <p className="text-red-600 text-xs mt-1">Passwords do not match</p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full"
              isLoading={isLoading}
              disabled={isLoading || !isPasswordValid(passwordValidation) || !passwordsMatch}
            >
              Create Account
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            <p>Already have an account?</p>
            <Link to="/login" className="text-blue-600 hover:text-blue-700 font-medium">
              Sign In
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PasswordRequirement({ met, children }: { met: boolean; children: React.ReactNode }) {
  return (
    <div className={`flex items-center gap-1 ${met ? 'text-green-600' : 'text-gray-400'}`}>
      {met ? (
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      ) : (
        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3a1 1 0 002 0V7z" clipRule="evenodd" />
        </svg>
      )}
      <span>{children}</span>
    </div>
  );
}
