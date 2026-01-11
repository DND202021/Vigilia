/**
 * Offline Status Hook
 */

import { useState, useEffect, useCallback } from 'react';
import { syncService } from '../services/syncService';

interface OfflineState {
  isOnline: boolean;
  isSyncing: boolean;
  lastSyncTime: number | null;
  pendingChanges: number;
  error: string | null;
}

export function useOffline() {
  const [state, setState] = useState<OfflineState>({
    isOnline: navigator.onLine,
    isSyncing: false,
    lastSyncTime: null,
    pendingChanges: 0,
    error: null,
  });

  useEffect(() => {
    // Subscribe to sync service state changes
    const unsubscribe = syncService.subscribe((syncState) => {
      setState((prev) => ({
        ...prev,
        isSyncing: syncState.status === 'syncing',
        lastSyncTime: syncState.lastSyncTime,
        pendingChanges: syncState.pendingChanges,
        error: syncState.error,
      }));
    });

    // Listen for online/offline events
    const handleOnline = () => setState((prev) => ({ ...prev, isOnline: true }));
    const handleOffline = () => setState((prev) => ({ ...prev, isOnline: false }));

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Start sync service
    syncService.startPeriodicSync();

    return () => {
      unsubscribe();
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const triggerSync = useCallback(() => {
    syncService.sync();
  }, []);

  return {
    ...state,
    triggerSync,
  };
}

/**
 * Service Worker Registration Hook
 */
export function useServiceWorker() {
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js')
        .then((reg) => {
          console.log('[SW] Registered:', reg.scope);
          setRegistration(reg);

          // Check for updates
          reg.addEventListener('updatefound', () => {
            const newWorker = reg.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  setUpdateAvailable(true);
                }
              });
            }
          });
        })
        .catch((error) => {
          console.error('[SW] Registration failed:', error);
        });

      // Listen for messages from service worker
      navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data.type === 'SYNC_TRIGGERED') {
          syncService.sync();
        }
      });
    }
  }, []);

  const updateServiceWorker = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  }, [registration]);

  const clearCache = useCallback(async () => {
    if (registration?.active) {
      return new Promise<boolean>((resolve) => {
        const messageChannel = new MessageChannel();
        messageChannel.port1.onmessage = (event) => {
          resolve(event.data.success);
        };
        registration.active?.postMessage({ type: 'CLEAR_CACHE' }, [messageChannel.port2]);
      });
    }
    return false;
  }, [registration]);

  return {
    registration,
    updateAvailable,
    updateServiceWorker,
    clearCache,
  };
}
