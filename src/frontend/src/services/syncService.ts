/**
 * Sync Service
 * Handles synchronization between offline storage and backend
 */

import { offlineDb } from './offlineDb';
import { incidentsApi, resourcesApi, alertsApi } from './api';
import type { Incident, Resource, Alert } from '../types';

const MAX_RETRIES = 3;
const SYNC_INTERVAL = 30000; // 30 seconds

type SyncStatus = 'idle' | 'syncing' | 'error';

interface SyncState {
  status: SyncStatus;
  lastSyncTime: number | null;
  pendingChanges: number;
  error: string | null;
}

class SyncService {
  private syncInterval: ReturnType<typeof setInterval> | null = null;
  private state: SyncState = {
    status: 'idle',
    lastSyncTime: null,
    pendingChanges: 0,
    error: null,
  };
  private listeners: Set<(state: SyncState) => void> = new Set();

  // Subscribe to state changes
  subscribe(listener: (state: SyncState) => void): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  private updateState(updates: Partial<SyncState>): void {
    this.state = { ...this.state, ...updates };
    this.listeners.forEach((listener) => listener(this.state));
  }

  // Check if online
  isOnline(): boolean {
    return navigator.onLine;
  }

  // Start periodic sync
  startPeriodicSync(): void {
    if (this.syncInterval) return;

    // Initial sync
    this.sync();

    // Set up periodic sync
    this.syncInterval = setInterval(() => {
      if (this.isOnline() && this.state.status !== 'syncing') {
        this.sync();
      }
    }, SYNC_INTERVAL);

    // Listen for online event
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);

    console.log('[SyncService] Periodic sync started');
  }

  // Stop periodic sync
  stopPeriodicSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }

    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);

    console.log('[SyncService] Periodic sync stopped');
  }

  private handleOnline = (): void => {
    console.log('[SyncService] Back online - triggering sync');
    this.sync();
  };

  private handleOffline = (): void => {
    console.log('[SyncService] Gone offline');
    this.updateState({ status: 'idle' });
  };

  // Main sync function
  async sync(): Promise<void> {
    if (!this.isOnline()) {
      console.log('[SyncService] Offline - skipping sync');
      return;
    }

    if (this.state.status === 'syncing') {
      console.log('[SyncService] Sync already in progress');
      return;
    }

    this.updateState({ status: 'syncing', error: null });

    try {
      // Process pending changes first
      await this.processSyncQueue();

      // Then fetch fresh data from server
      await this.syncFromServer();

      this.updateState({
        status: 'idle',
        lastSyncTime: Date.now(),
        error: null,
      });

      console.log('[SyncService] Sync completed successfully');
    } catch (error) {
      console.error('[SyncService] Sync failed:', error);
      this.updateState({
        status: 'error',
        error: error instanceof Error ? error.message : 'Sync failed',
      });
    }

    // Update pending changes count
    const queue = await offlineDb.getSyncQueue();
    this.updateState({ pendingChanges: queue.length });
  }

  // Process queued offline changes
  private async processSyncQueue(): Promise<void> {
    const queue = await offlineDb.getSyncQueue();

    for (const item of queue) {
      if (item.retries >= MAX_RETRIES) {
        console.warn('[SyncService] Max retries reached for:', item);
        await offlineDb.removeSyncQueueItem(item.id);
        continue;
      }

      try {
        await this.processSyncItem(item);
        await offlineDb.removeSyncQueueItem(item.id);
      } catch (error) {
        console.error('[SyncService] Failed to sync item:', item, error);
        await offlineDb.incrementSyncRetry(item.id);
      }
    }
  }

  private async processSyncItem(item: {
    operation: string;
    store: string;
    data: unknown;
  }): Promise<void> {
    const { operation, store, data } = item;

    switch (store) {
      case 'incidents':
        await this.syncIncidentItem(operation, data as Partial<Incident>);
        break;
      case 'resources':
        await this.syncResourceItem(operation, data as Partial<Resource>);
        break;
      case 'alerts':
        await this.syncAlertItem(operation, data as Partial<Alert>);
        break;
    }
  }

  private async syncIncidentItem(operation: string, data: Partial<Incident>): Promise<void> {
    switch (operation) {
      case 'create':
        await incidentsApi.create(data as Parameters<typeof incidentsApi.create>[0]);
        break;
      case 'update':
        if (data.id) {
          await incidentsApi.update(data.id, data);
        }
        break;
    }
  }

  private async syncResourceItem(operation: string, data: Partial<Resource>): Promise<void> {
    switch (operation) {
      case 'create':
        await resourcesApi.create(data as Parameters<typeof resourcesApi.create>[0]);
        break;
      case 'update':
        if (data.id && data.status) {
          await resourcesApi.updateStatus(data.id, { status: data.status });
        }
        break;
    }
  }

  private async syncAlertItem(operation: string, data: Partial<Alert>): Promise<void> {
    switch (operation) {
      case 'update':
        if (data.id) {
          if (data.status === 'acknowledged') {
            await alertsApi.acknowledge(data.id);
          } else if (data.status === 'resolved') {
            await alertsApi.resolve(data.id);
          }
        }
        break;
    }
  }

  // Fetch data from server and store locally
  private async syncFromServer(): Promise<void> {
    const [incidentsResult, resourcesResult, alertsResult] = await Promise.allSettled([
      incidentsApi.getActive(),
      resourcesApi.getAvailable(),
      alertsApi.getPending(),
    ]);

    if (incidentsResult.status === 'fulfilled') {
      await offlineDb.incidents.putMany(incidentsResult.value);
    }

    if (resourcesResult.status === 'fulfilled') {
      await offlineDb.resources.putMany(resourcesResult.value);
    }

    if (alertsResult.status === 'fulfilled') {
      await offlineDb.alerts.putMany(alertsResult.value);
    }
  }

  // Queue an operation for sync when back online
  async queueForSync(
    operation: 'create' | 'update' | 'delete',
    store: 'incidents' | 'resources' | 'alerts',
    data: unknown
  ): Promise<void> {
    await offlineDb.addToSyncQueue({ operation, store, data });
    const queue = await offlineDb.getSyncQueue();
    this.updateState({ pendingChanges: queue.length });

    // Try to sync immediately if online
    if (this.isOnline()) {
      this.sync();
    }
  }

  // Get data with offline fallback
  async getIncidents(): Promise<Incident[]> {
    if (this.isOnline()) {
      try {
        const incidents = await incidentsApi.getActive();
        await offlineDb.incidents.putMany(incidents);
        return incidents;
      } catch (error) {
        console.warn('[SyncService] Failed to fetch incidents, using cache');
      }
    }

    return offlineDb.incidents.getAll<Incident>();
  }

  async getResources(): Promise<Resource[]> {
    if (this.isOnline()) {
      try {
        const resources = await resourcesApi.getAvailable();
        await offlineDb.resources.putMany(resources);
        return resources;
      } catch (error) {
        console.warn('[SyncService] Failed to fetch resources, using cache');
      }
    }

    return offlineDb.resources.getAll<Resource>();
  }

  async getAlerts(): Promise<Alert[]> {
    if (this.isOnline()) {
      try {
        const alerts = await alertsApi.getPending();
        await offlineDb.alerts.putMany(alerts);
        return alerts;
      } catch (error) {
        console.warn('[SyncService] Failed to fetch alerts, using cache');
      }
    }

    return offlineDb.alerts.getAll<Alert>();
  }

  getState(): SyncState {
    return this.state;
  }
}

// Singleton instance
export const syncService = new SyncService();
