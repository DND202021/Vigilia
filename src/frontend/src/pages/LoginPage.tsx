/**
 * Login Page
 */

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { Button, Input, Card, CardContent } from '../components/ui';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, isAuthenticated } = useAuthStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  // Redirect if already authenticated
  if (isAuthenticated) {
    navigate(from, { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username || !password) {
      setError('Please enter username and password');
      return;
    }

    try {
      await login({ username, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError('Invalid username or password');
    }
  };

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
          <form onSubmit={handleSubmit} className="space-y-4">
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
              disabled={isLoading}
            />

            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={isLoading}
            />

            <Button
              type="submit"
              className="w-full"
              isLoading={isLoading}
              disabled={isLoading}
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            <p>Emergency Response Personnel Only</p>
            <p className="mt-1">Contact your administrator for access</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
