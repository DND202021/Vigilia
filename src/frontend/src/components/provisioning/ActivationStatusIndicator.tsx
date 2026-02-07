/**
 * Activation Status Indicator Component
 *
 * Shows the current status of device activation:
 * - pending: waiting for device to connect
 * - active: device successfully activated
 * - timeout: device did not activate within timeout period
 */

import type { ActivationStatus } from '../../stores/provisioningStore';

interface ActivationStatusIndicatorProps {
  status: ActivationStatus;
  elapsedSeconds: number;
  onRefresh?: () => void;
}

export function ActivationStatusIndicator({ status, elapsedSeconds, onRefresh }: ActivationStatusIndicatorProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (status === 'idle' || status === 'pending') {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <div className="relative">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
            <span className="w-4 h-4 bg-blue-600 rounded-full animate-pulse"></span>
          </div>
        </div>
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900">Waiting for device to connect...</h3>
          <p className="text-sm text-gray-500 mt-2">Elapsed time: {formatTime(elapsedSeconds)}</p>
          <p className="text-xs text-gray-400 mt-1">
            Listening for device activation via real-time connection
          </p>
        </div>
      </div>
    );
  }

  if (status === 'active') {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
          <span className="text-3xl">✓</span>
        </div>
        <div className="text-center">
          <h3 className="text-lg font-semibold text-green-800">Device activated successfully!</h3>
          <p className="text-sm text-gray-500 mt-2">
            Your device is now online and ready to use
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Activation completed in {formatTime(elapsedSeconds)}
          </p>
        </div>
      </div>
    );
  }

  // timeout
  return (
    <div className="flex flex-col items-center justify-center py-12 space-y-4">
      <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center">
        <span className="text-3xl">⏱️</span>
      </div>
      <div className="text-center">
        <h3 className="text-lg font-semibold text-yellow-800">Device not yet activated</h3>
        <p className="text-sm text-gray-500 mt-2">
          The device has not connected within the expected time ({formatTime(elapsedSeconds)})
        </p>
        <p className="text-xs text-gray-600 mt-1">
          This may be normal if the device is still being configured or powered on.
        </p>
      </div>
      {onRefresh && (
        <button
          onClick={onRefresh}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Refresh Status
        </button>
      )}
    </div>
  );
}
