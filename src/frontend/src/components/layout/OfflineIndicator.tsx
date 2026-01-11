/**
 * Offline Status Indicator Component
 */

import { useOffline, useServiceWorker } from '../../hooks/useOffline';
import { Button } from '../ui';
import { cn, formatRelativeTime } from '../../utils';

export function OfflineIndicator() {
  const { isOnline, isSyncing, pendingChanges, lastSyncTime, error, triggerSync } = useOffline();
  const { updateAvailable, updateServiceWorker } = useServiceWorker();

  // Update available banner
  if (updateAvailable) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <div className="bg-blue-600 text-white rounded-lg shadow-lg p-4 max-w-sm">
          <p className="font-medium">Update Available</p>
          <p className="text-sm text-blue-100 mt-1">
            A new version of ERIOP is available.
          </p>
          <Button
            size="sm"
            variant="secondary"
            className="mt-3"
            onClick={updateServiceWorker}
          >
            Update Now
          </Button>
        </div>
      </div>
    );
  }

  // Offline banner
  if (!isOnline) {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-50">
        <div className="bg-yellow-500 text-yellow-900 px-4 py-2">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
                />
              </svg>
              <span className="font-medium">You are offline</span>
              {pendingChanges > 0 && (
                <span className="text-sm">
                  ({pendingChanges} change{pendingChanges > 1 ? 's' : ''} pending)
                </span>
              )}
            </div>
            <span className="text-sm">
              Working with cached data
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Syncing indicator
  if (isSyncing) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <div className="bg-blue-600 text-white rounded-lg shadow-lg px-4 py-2 flex items-center gap-2">
          <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span className="text-sm">Syncing...</span>
        </div>
      </div>
    );
  }

  // Error indicator
  if (error) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <div className="bg-red-600 text-white rounded-lg shadow-lg p-4 max-w-sm">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <p className="font-medium">Sync Error</p>
              <p className="text-sm text-red-100 mt-1">{error}</p>
            </div>
          </div>
          <Button
            size="sm"
            variant="secondary"
            className="mt-3"
            onClick={triggerSync}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  // Pending changes indicator
  if (pendingChanges > 0) {
    return (
      <div className="fixed bottom-4 right-4 z-50">
        <div className="bg-yellow-500 text-yellow-900 rounded-lg shadow-lg px-4 py-2 flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span className="text-sm">
            {pendingChanges} pending change{pendingChanges > 1 ? 's' : ''}
          </span>
          <button
            onClick={triggerSync}
            className="ml-2 text-sm underline hover:no-underline"
          >
            Sync now
          </button>
        </div>
      </div>
    );
  }

  return null;
}
