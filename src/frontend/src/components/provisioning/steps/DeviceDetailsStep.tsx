/**
 * Device Details Step (Step 2)
 *
 * Form for entering device information:
 * - Name (required)
 * - Device Type (select)
 * - Building (required, select)
 * - Credential Type (radio)
 * - Serial Number (optional)
 * - Manufacturer (optional)
 * - Model (optional)
 */

import { useEffect } from 'react';
import { useProvisioningStore } from '../../../stores/provisioningStore';
import type { DeviceType } from '../../../types';

const DEVICE_TYPES: { value: DeviceType; label: string }[] = [
  { value: 'microphone', label: 'Microphone' },
  { value: 'camera', label: 'Camera' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'gateway', label: 'Gateway' },
];

export function DeviceDetailsStep() {
  const {
    formData,
    updateFormData,
    buildings,
    isLoadingBuildings,
    fetchBuildings,
  } = useProvisioningStore();

  useEffect(() => {
    fetchBuildings();
  }, [fetchBuildings]);

  const isValid = formData.name.trim() !== '' && formData.buildingId !== '';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Device Details</h2>
        <p className="text-sm text-gray-500 mt-1">
          Enter the device information for provisioning.
        </p>
      </div>

      <div className="space-y-4">
        {/* Device Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Device Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => updateFormData({ name: e.target.value })}
            placeholder="e.g., Lobby Microphone 1"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Device Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Device Type
          </label>
          <select
            value={formData.deviceType}
            onChange={(e) => updateFormData({ deviceType: e.target.value as 'microphone' | 'camera' | 'sensor' | 'gateway' })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {DEVICE_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          {formData.profileId && (
            <p className="text-xs text-gray-500 mt-1">
              Pre-filled from selected profile
            </p>
          )}
        </div>

        {/* Building */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Building <span className="text-red-500">*</span>
          </label>
          {isLoadingBuildings ? (
            <div className="flex items-center text-sm text-gray-500">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              Loading buildings...
            </div>
          ) : (
            <select
              value={formData.buildingId}
              onChange={(e) => updateFormData({ buildingId: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select a building</option>
              {buildings.map((building) => (
                <option key={building.id} value={building.id}>
                  {building.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Credential Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Credential Type
          </label>
          <div className="space-y-3">
            <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                name="credentialType"
                value="access_token"
                checked={formData.credentialType === 'access_token'}
                onChange={(e) => updateFormData({ credentialType: e.target.value as 'access_token' | 'x509' })}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-gray-900">Access Token</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  Simple token-based authentication. Best for devices with limited TLS support.
                </div>
              </div>
            </label>

            <label className="flex items-start p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
              <input
                type="radio"
                name="credentialType"
                value="x509"
                checked={formData.credentialType === 'x509'}
                onChange={(e) => updateFormData({ credentialType: e.target.value as 'access_token' | 'x509' })}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-gray-900">X.509 Certificate</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  Certificate-based mutual TLS authentication. Recommended for production deployments.
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Serial Number */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Serial Number
          </label>
          <input
            type="text"
            value={formData.serialNumber}
            onChange={(e) => updateFormData({ serialNumber: e.target.value })}
            placeholder="Optional"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Manufacturer */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Manufacturer
          </label>
          <input
            type="text"
            value={formData.manufacturer}
            onChange={(e) => updateFormData({ manufacturer: e.target.value })}
            placeholder="Optional"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Model */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Model
          </label>
          <input
            type="text"
            value={formData.model}
            onChange={(e) => updateFormData({ model: e.target.value })}
            placeholder="Optional"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {!isValid && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
          Please fill in all required fields to continue.
        </div>
      )}
    </div>
  );
}
