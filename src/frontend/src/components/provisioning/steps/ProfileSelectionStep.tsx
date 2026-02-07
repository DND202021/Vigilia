/**
 * Profile Selection Step (Step 1)
 *
 * Displays device profiles as selectable cards.
 * Allows user to skip if no profile is needed.
 */

import { useEffect } from 'react';
import { useProvisioningStore } from '../../../stores/provisioningStore';
import type { DeviceType } from '../../../types';

function getDeviceTypeIcon(type: DeviceType) {
  switch (type) {
    case 'microphone': return '🎙️';
    case 'camera': return '📷';
    case 'sensor': return '📡';
    case 'gateway': return '🔌';
    default: return '📱';
  }
}

export function ProfileSelectionStep() {
  const {
    profiles,
    isLoadingProfiles,
    formData,
    updateFormData,
    fetchProfiles,
  } = useProvisioningStore();

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  const selectedProfileId = formData.profileId;

  const handleProfileSelect = (profileId: string, deviceType: DeviceType) => {
    // Only allow valid device types from the form
    const validDeviceType = deviceType === 'other' ? 'sensor' : deviceType;
    updateFormData({ profileId, deviceType: validDeviceType as 'microphone' | 'camera' | 'sensor' | 'gateway' });
  };

  const handleSkipProfile = () => {
    updateFormData({ profileId: null });
  };

  if (isLoadingProfiles) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading profiles...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Select Device Profile</h2>
        <p className="text-sm text-gray-500 mt-1">
          Choose a pre-configured profile for your device, or skip to configure manually.
        </p>
      </div>

      {profiles.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-gray-600">No device profiles found. You can still provision without a profile.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              onClick={() => handleProfileSelect(profile.id, profile.device_type as DeviceType)}
              className={`text-left p-4 rounded-lg border-2 transition-all ${
                selectedProfileId === profile.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:shadow-md'
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="text-3xl">{getDeviceTypeIcon(profile.device_type as DeviceType)}</span>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{profile.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5 capitalize">{profile.device_type}</p>
                  {profile.description && (
                    <p className="text-sm text-gray-600 mt-2">{profile.description}</p>
                  )}
                </div>
                {selectedProfileId === profile.id && (
                  <span className="text-blue-600 text-xl">✓</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      <div className="border-t pt-4">
        <button
          onClick={handleSkipProfile}
          className={`w-full p-3 rounded-lg border-2 transition-all ${
            selectedProfileId === null
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-200 text-gray-600 hover:border-gray-300'
          }`}
        >
          Skip - No Profile (Configure Manually)
        </button>
      </div>
    </div>
  );
}
