/**
 * Notification Preferences Component
 *
 * Allows users to configure their alert notification preferences:
 * - Channel toggles (call, SMS, email, push)
 * - Building scope selection
 * - Severity filter
 * - Quiet hours
 */

import { useEffect, useState } from 'react';
import { notificationPrefsApi, buildingsApi } from '../../services/api';
import type { NotificationPreference, NotificationPreferenceUpdate, Building } from '../../types';

interface NotificationPreferencesProps {
  userId: string;
  className?: string;
}

const SEVERITY_OPTIONS = [
  { value: 1, label: 'Critical only' },
  { value: 2, label: 'High and above' },
  { value: 3, label: 'Medium and above' },
  { value: 4, label: 'Low and above' },
  { value: 5, label: 'All alerts' },
];

export function NotificationPreferences({ userId, className = '' }: NotificationPreferencesProps) {
  const [prefs, setPrefs] = useState<NotificationPreference | null>(null);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadData();
  }, [userId]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [prefsData, buildingsData] = await Promise.all([
        notificationPrefsApi.get(userId).catch(() => null),
        buildingsApi.list({ page_size: 100 }),
      ]);
      setPrefs(prefsData);
      setBuildings(buildingsData.items);
    } catch (err) {
      setError('Failed to load notification preferences');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!prefs) return;
    setIsSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const update: NotificationPreferenceUpdate = {
        call_enabled: prefs.call_enabled,
        sms_enabled: prefs.sms_enabled,
        email_enabled: prefs.email_enabled,
        push_enabled: prefs.push_enabled,
        building_ids: prefs.building_ids,
        min_severity: prefs.min_severity,
        quiet_start: prefs.quiet_start || undefined,
        quiet_end: prefs.quiet_end || undefined,
        quiet_override_critical: prefs.quiet_override_critical,
      };
      const updated = await notificationPrefsApi.update(userId, update);
      setPrefs(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError('Failed to save notification preferences');
    } finally {
      setIsSaving(false);
    }
  };

  const updatePref = (updates: Partial<NotificationPreference>) => {
    if (!prefs) {
      // Create default preferences
      setPrefs({
        id: '',
        user_id: userId,
        call_enabled: false,
        sms_enabled: false,
        email_enabled: false,
        push_enabled: true,
        building_ids: [],
        min_severity: 3,
        quiet_start: undefined,
        quiet_end: undefined,
        quiet_override_critical: true,
        ...updates,
      } as NotificationPreference);
    } else {
      setPrefs({ ...prefs, ...updates });
    }
  };

  const toggleBuilding = (buildingId: string) => {
    const current = prefs?.building_ids || [];
    const updated = current.includes(buildingId)
      ? current.filter((id) => id !== buildingId)
      : [...current, buildingId];
    updatePref({ building_ids: updated });
  };

  if (isLoading) {
    return <div className="text-gray-500 text-sm p-4">Loading preferences...</div>;
  }

  const hasAlertingEnabled = prefs && (prefs.call_enabled || prefs.sms_enabled || prefs.email_enabled);
  const hasNoBuildings = hasAlertingEnabled && (!prefs.building_ids || prefs.building_ids.length === 0);

  return (
    <div className={`bg-white rounded-lg border ${className}`}>
      <div className="p-4 border-b">
        <h3 className="text-lg font-semibold text-gray-900">Notification Preferences</h3>
        <p className="text-sm text-gray-500 mt-1">Configure how you receive alert notifications</p>
      </div>

      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="mx-4 mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
          Preferences saved successfully
        </div>
      )}

      {hasNoBuildings && (
        <div className="mx-4 mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          Warning: You have alerting enabled but no buildings assigned. Select buildings below to receive alerts.
        </div>
      )}

      <div className="p-4 space-y-6">
        {/* Channel Toggles */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-3">Notification Channels</h4>
          <div className="space-y-3">
            {[
              { key: 'call_enabled' as const, label: 'Phone Call', desc: 'Receive voice calls for critical alerts' },
              { key: 'sms_enabled' as const, label: 'SMS', desc: 'Receive text messages for alerts' },
              { key: 'email_enabled' as const, label: 'Email', desc: 'Receive email notifications' },
              { key: 'push_enabled' as const, label: 'Push Notification', desc: 'Receive browser push notifications' },
            ].map((channel) => (
              <label key={channel.key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100">
                <div>
                  <div className="text-sm font-medium text-gray-800">{channel.label}</div>
                  <div className="text-xs text-gray-500">{channel.desc}</div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={prefs?.[channel.key] || false}
                    onChange={(e) => updatePref({ [channel.key]: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-100 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600" />
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Severity Filter */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Minimum Severity</h4>
          <select
            value={prefs?.min_severity || 3}
            onChange={(e) => updatePref({ min_severity: Number(e.target.value) })}
            className="w-full border rounded-lg px-3 py-2 text-sm"
          >
            {SEVERITY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Building Scope */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Building Scope
            <span className="text-xs text-gray-400 font-normal ml-2">
              (empty = all buildings)
            </span>
          </h4>
          <div className="max-h-48 overflow-y-auto border rounded-lg divide-y">
            {buildings.map((building) => (
              <label
                key={building.id}
                className="flex items-center gap-3 px-3 py-2 hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={prefs?.building_ids?.includes(building.id) || false}
                  onChange={() => toggleBuilding(building.id)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-gray-800 truncate">{building.name}</div>
                  <div className="text-xs text-gray-400 truncate">{building.full_address}</div>
                </div>
              </label>
            ))}
            {buildings.length === 0 && (
              <div className="p-3 text-sm text-gray-400 text-center">No buildings available</div>
            )}
          </div>
        </div>

        {/* Quiet Hours */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Quiet Hours</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500">Start</label>
              <input
                type="time"
                value={prefs?.quiet_start || ''}
                onChange={(e) => updatePref({ quiet_start: e.target.value || undefined })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500">End</label>
              <input
                type="time"
                value={prefs?.quiet_end || ''}
                onChange={(e) => updatePref({ quiet_end: e.target.value || undefined })}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
          <label className="flex items-center gap-2 mt-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={prefs?.quiet_override_critical ?? true}
              onChange={(e) => updatePref({ quiet_override_critical: e.target.checked })}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Override quiet hours for critical alerts
          </label>
        </div>
      </div>

      {/* Save */}
      <div className="p-4 border-t bg-gray-50 rounded-b-lg">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
        >
          {isSaving ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>
    </div>
  );
}
