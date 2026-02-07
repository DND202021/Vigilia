/**
 * Credential Generation Step (Step 3)
 *
 * Automatically calls the provisioning API to generate credentials.
 * Shows loading state, success state with auto-advance, or error with retry.
 */

import { useEffect } from 'react';
import { useProvisioningStore } from '../../../stores/provisioningStore';

export function CredentialGenerationStep() {
  const {
    formData,
    credentials,
    isProvisioning,
    error,
    provisionDevice,
    nextStep,
    clearError,
  } = useProvisioningStore();

  useEffect(() => {
    // Auto-provision on mount if credentials don't exist yet
    if (!credentials) {
      provisionDevice().catch(() => {
        // Error is already set in store
      });
    }
  }, []); // Only run once on mount

  useEffect(() => {
    // Auto-advance after successful provisioning
    if (credentials && !isProvisioning) {
      const timer = setTimeout(() => {
        nextStep();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [credentials, isProvisioning, nextStep]);

  if (isProvisioning) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
        <h3 className="text-lg font-semibold text-gray-900">Generating Credentials...</h3>
        <p className="text-sm text-gray-500 text-center max-w-md">
          Creating secure credentials for your device. This may take a moment.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 py-8">
        <div className="flex flex-col items-center text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <span className="text-3xl">❌</span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Provisioning Failed</h3>
          <p className="text-sm text-red-600 max-w-md">{error}</p>
        </div>

        <div className="flex justify-center">
          <button
            onClick={() => {
              clearError();
              provisionDevice();
            }}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (credentials) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
          <span className="text-3xl">✓</span>
        </div>
        <h3 className="text-lg font-semibold text-green-800">Credentials Generated Successfully!</h3>
        <p className="text-sm text-gray-500">Redirecting to download...</p>
      </div>
    );
  }

  // Summary of what's being provisioned
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Generate Credentials</h2>
        <p className="text-sm text-gray-500 mt-1">
          Review the device details before generating credentials.
        </p>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-2">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <span className="text-gray-600">Device Name:</span>
          <span className="font-medium text-gray-900">{formData.name}</span>

          <span className="text-gray-600">Device Type:</span>
          <span className="font-medium text-gray-900 capitalize">{formData.deviceType}</span>

          <span className="text-gray-600">Credential Type:</span>
          <span className="font-medium text-gray-900">
            {formData.credentialType === 'access_token' ? 'Access Token' : 'X.509 Certificate'}
          </span>
        </div>
      </div>
    </div>
  );
}
