/**
 * Settings Page
 * Central hub for user account settings
 */

import { useState } from 'react';
import { useAuthStore } from '../stores/authStore';
import { SecuritySettings } from '../components/settings';
import { NotificationPreferences } from '../components/notifications';
import { cn } from '../utils';

type SettingsTab = 'security' | 'notifications' | 'profile';

const tabs: { id: SettingsTab; label: string; icon: string }[] = [
  { id: 'security', label: 'Security', icon: 'shield' },
  { id: 'notifications', label: 'Notifications', icon: 'bell' },
  { id: 'profile', label: 'Profile', icon: 'user' },
];

export function SettingsPage() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<SettingsTab>('security');

  const renderTabIcon = (icon: string) => {
    switch (icon) {
      case 'shield':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        );
      case 'bell':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
        );
      case 'user':
        return (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Manage your account settings and preferences</p>
      </div>

      <div className="flex flex-col md:flex-row gap-6">
        {/* Sidebar Navigation */}
        <nav className="md:w-48 flex-shrink-0">
          <ul className="space-y-1">
            {tabs.map((tab) => (
              <li key={tab.id}>
                <button
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-2 rounded-lg text-left transition-colors',
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  )}
                >
                  {renderTabIcon(tab.icon)}
                  {tab.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* Content Area */}
        <main className="flex-1 min-w-0">
          {activeTab === 'security' && <SecuritySettings />}

          {activeTab === 'notifications' && user && (
            <NotificationPreferences userId={user.id} />
          )}

          {activeTab === 'profile' && (
            <div className="bg-white rounded-lg border p-6">
              <h2 className="text-lg font-semibold mb-4">Profile Information</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Full Name</label>
                  <p className="mt-1 text-gray-900">{user?.full_name || '—'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Email</label>
                  <p className="mt-1 text-gray-900">{user?.email || '—'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Username</label>
                  <p className="mt-1 text-gray-900">{user?.username || '—'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">Role</label>
                  <p className="mt-1 text-gray-900 capitalize">{user?.role || '—'}</p>
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  Contact your administrator to update your profile information
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
