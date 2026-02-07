/**
 * Credential Download Step (Step 4)
 *
 * Displays credentials with download functionality.
 * Auto-clears credentials after 30 seconds for security.
 */

import { useState, useEffect } from 'react';
import { useProvisioningStore } from '../../../stores/provisioningStore';
import { CredentialDownloadCard } from '../CredentialDownloadCard';

export function CredentialDownloadStep() {
  const { credentials, clearCredentials, nextStep } = useProvisioningStore();
  const [hasDownloaded, setHasDownloaded] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(30);

  useEffect(() => {
    if (!credentials) return;

    // Start 30-second countdown
    const interval = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          clearCredentials();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [credentials, clearCredentials]);

  const handleDownloaded = () => {
    setHasDownloaded(true);
  };

  const handleContinue = () => {
    nextStep();
  };

  if (!credentials) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Credentials Downloaded</h2>
          <p className="text-sm text-gray-500 mt-1">
            Credentials have been downloaded and cleared from this page for security.
          </p>
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-green-600 text-xl">✓</span>
          <div>
            <p className="font-semibold text-green-800">Credentials Secured</p>
            <p className="text-sm text-green-700 mt-1">
              Your credentials have been downloaded. Keep them in a secure location.
            </p>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleContinue}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Continue to Activation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Download Credentials</h2>
        <p className="text-sm text-gray-500 mt-1">
          Save your device credentials securely before continuing.
        </p>
      </div>

      <CredentialDownloadCard credentials={credentials} onDownloaded={handleDownloaded} />

      {hasDownloaded && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
          <span className="text-green-600 text-xl">✓</span>
          <div>
            <p className="font-semibold text-green-800">Credentials downloaded successfully</p>
            <p className="text-sm text-green-700 mt-1">
              You can now proceed to wait for device activation.
            </p>
          </div>
        </div>
      )}

      {timeRemaining > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
          <p className="text-sm text-gray-600">
            Credentials will be cleared from this page in{' '}
            <span className="font-semibold text-gray-900">{timeRemaining}</span> seconds
          </p>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleContinue}
          disabled={!hasDownloaded}
          className={`px-6 py-2 rounded-lg transition-colors ${
            hasDownloaded
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          Continue to Activation
        </button>
      </div>
    </div>
  );
}
