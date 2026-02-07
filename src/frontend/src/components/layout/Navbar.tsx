/**
 * Navigation Bar Component
 */

import { Link, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { cn } from '../../utils';

const navLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/incidents', label: 'Incidents' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/resources', label: 'Resources' },
  { to: '/buildings', label: 'Buildings' },
  { to: '/map', label: 'Map' },
  { to: '/messages', label: 'Messages' },
  { to: '/devices', label: 'Devices' },
  { to: '/telemetry', label: 'Telemetry' },
  { to: '/analytics', label: 'Analytics' },
];

const adminLinks = [
  { to: '/users', label: 'Users' },
  { to: '/roles', label: 'Roles' },
  { to: '/audit-logs', label: 'Audit Logs' },
];

export function Navbar() {
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuthStore();

  if (!isAuthenticated) return null;

  return (
    <nav className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="font-bold text-lg">E</span>
              </div>
              <span className="font-bold text-xl">ERIOP</span>
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.to ||
                (link.to !== '/' && location.pathname.startsWith(link.to));

              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={cn(
                    'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  )}
                >
                  {link.label}
                </Link>
              );
            })}

            {/* Admin Links Separator */}
            <div className="w-px h-6 bg-gray-700 mx-2" />

            {adminLinks.map((link) => {
              const isActive = location.pathname === link.to ||
                (link.to !== '/' && location.pathname.startsWith(link.to));

              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={cn(
                    'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <div className="text-sm">
              <span className="text-gray-400">Logged in as</span>{' '}
              <span className="font-medium">{user?.username || 'User'}</span>
            </div>
            <button
              onClick={() => logout()}
              className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden border-t border-gray-800">
        <div className="flex overflow-x-auto py-2 px-4 space-x-2">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to ||
              (link.to !== '/' && location.pathname.startsWith(link.to));

            return (
              <Link
                key={link.to}
                to={link.to}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                )}
              >
                {link.label}
              </Link>
            );
          })}
          {adminLinks.map((link) => {
            const isActive = location.pathname === link.to ||
              (link.to !== '/' && location.pathname.startsWith(link.to));

            return (
              <Link
                key={link.to}
                to={link.to}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                  isActive
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800'
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
