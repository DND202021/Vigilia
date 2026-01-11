/**
 * IndexedDB Offline Storage Service
 * Provides offline data persistence for ERIOP
 */

const DB_NAME = 'eriop_offline';
const DB_VERSION = 1;

// Store names
const STORES = {
  incidents: 'incidents',
  resources: 'resources',
  alerts: 'alerts',
  syncQueue: 'sync_queue',
  cache: 'cache',
} as const;

type StoreName = typeof STORES[keyof typeof STORES];

interface SyncQueueItem {
  id: string;
  operation: 'create' | 'update' | 'delete';
  store: StoreName;
  data: unknown;
  timestamp: number;
  retries: number;
}

class OfflineDatabase {
  private db: IDBDatabase | null = null;
  private initPromise: Promise<void> | null = null;

  async init(): Promise<void> {
    if (this.db) return;
    if (this.initPromise) return this.initPromise;

    this.initPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error('[OfflineDB] Failed to open database:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        console.log('[OfflineDB] Database opened successfully');
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        // Incidents store
        if (!db.objectStoreNames.contains(STORES.incidents)) {
          const incidentStore = db.createObjectStore(STORES.incidents, { keyPath: 'id' });
          incidentStore.createIndex('status', 'status', { unique: false });
          incidentStore.createIndex('priority', 'priority', { unique: false });
          incidentStore.createIndex('updated_at', 'updated_at', { unique: false });
        }

        // Resources store
        if (!db.objectStoreNames.contains(STORES.resources)) {
          const resourceStore = db.createObjectStore(STORES.resources, { keyPath: 'id' });
          resourceStore.createIndex('status', 'status', { unique: false });
          resourceStore.createIndex('resource_type', 'resource_type', { unique: false });
        }

        // Alerts store
        if (!db.objectStoreNames.contains(STORES.alerts)) {
          const alertStore = db.createObjectStore(STORES.alerts, { keyPath: 'id' });
          alertStore.createIndex('status', 'status', { unique: false });
          alertStore.createIndex('severity', 'severity', { unique: false });
        }

        // Sync queue for offline operations
        if (!db.objectStoreNames.contains(STORES.syncQueue)) {
          const syncStore = db.createObjectStore(STORES.syncQueue, { keyPath: 'id' });
          syncStore.createIndex('timestamp', 'timestamp', { unique: false });
          syncStore.createIndex('store', 'store', { unique: false });
        }

        // Generic cache store
        if (!db.objectStoreNames.contains(STORES.cache)) {
          const cacheStore = db.createObjectStore(STORES.cache, { keyPath: 'key' });
          cacheStore.createIndex('expires_at', 'expires_at', { unique: false });
        }

        console.log('[OfflineDB] Database schema upgraded');
      };
    });

    return this.initPromise;
  }

  private async ensureInit(): Promise<IDBDatabase> {
    await this.init();
    if (!this.db) {
      throw new Error('Database not initialized');
    }
    return this.db;
  }

  // Generic CRUD operations
  async put<T extends { id: string }>(store: StoreName, item: T): Promise<void> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(store, 'readwrite');
      const objectStore = transaction.objectStore(store);
      const request = objectStore.put({ ...item, _offline_updated: Date.now() });

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async putMany<T extends { id: string }>(store: StoreName, items: T[]): Promise<void> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(store, 'readwrite');
      const objectStore = transaction.objectStore(store);

      items.forEach((item) => {
        objectStore.put({ ...item, _offline_updated: Date.now() });
      });

      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error);
    });
  }

  async get<T>(store: StoreName, id: string): Promise<T | undefined> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(store, 'readonly');
      const objectStore = transaction.objectStore(store);
      const request = objectStore.get(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async getAll<T>(store: StoreName): Promise<T[]> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(store, 'readonly');
      const objectStore = transaction.objectStore(store);
      const request = objectStore.getAll();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async getByIndex<T>(
    store: StoreName,
    indexName: string,
    value: IDBValidKey
  ): Promise<T[]> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(store, 'readonly');
      const objectStore = transaction.objectStore(store);
      const index = objectStore.index(indexName);
      const request = index.getAll(value);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async delete(store: StoreName, id: string): Promise<void> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(store, 'readwrite');
      const objectStore = transaction.objectStore(store);
      const request = objectStore.delete(id);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async clear(store: StoreName): Promise<void> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(store, 'readwrite');
      const objectStore = transaction.objectStore(store);
      const request = objectStore.clear();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  // Sync queue operations
  async addToSyncQueue(item: Omit<SyncQueueItem, 'id' | 'timestamp' | 'retries'>): Promise<void> {
    const queueItem: SyncQueueItem = {
      ...item,
      id: crypto.randomUUID(),
      timestamp: Date.now(),
      retries: 0,
    };

    await this.put(STORES.syncQueue, queueItem);
  }

  async getSyncQueue(): Promise<SyncQueueItem[]> {
    return this.getAll<SyncQueueItem>(STORES.syncQueue);
  }

  async removeSyncQueueItem(id: string): Promise<void> {
    await this.delete(STORES.syncQueue, id);
  }

  async incrementSyncRetry(id: string): Promise<void> {
    const item = await this.get<SyncQueueItem>(STORES.syncQueue, id);
    if (item) {
      item.retries++;
      await this.put(STORES.syncQueue, item);
    }
  }

  // Cache operations
  async setCache(key: string, value: unknown, ttlSeconds: number = 300): Promise<void> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.cache, 'readwrite');
      const objectStore = transaction.objectStore(STORES.cache);
      const request = objectStore.put({
        key,
        value,
        expires_at: Date.now() + ttlSeconds * 1000,
      });

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async getCache<T>(key: string): Promise<T | undefined> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.cache, 'readonly');
      const objectStore = transaction.objectStore(STORES.cache);
      const request = objectStore.get(key);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const result = request.result;
        if (!result) {
          resolve(undefined);
        } else if (result.expires_at < Date.now()) {
          // Expired - clean up and return undefined
          this.delete(STORES.cache, key);
          resolve(undefined);
        } else {
          resolve(result.value);
        }
      };
    });
  }

  async cleanExpiredCache(): Promise<void> {
    const db = await this.ensureInit();

    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORES.cache, 'readwrite');
      const objectStore = transaction.objectStore(STORES.cache);
      const index = objectStore.index('expires_at');
      const range = IDBKeyRange.upperBound(Date.now());
      const request = index.openCursor(range);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const cursor = request.result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          resolve();
        }
      };
    });
  }

  // Store-specific helpers
  get incidents() {
    return {
      put: <T extends { id: string }>(item: T) => this.put(STORES.incidents, item),
      putMany: <T extends { id: string }>(items: T[]) => this.putMany(STORES.incidents, items),
      get: <T>(id: string) => this.get<T>(STORES.incidents, id),
      getAll: <T>() => this.getAll<T>(STORES.incidents),
      getByStatus: <T>(status: string) => this.getByIndex<T>(STORES.incidents, 'status', status),
      delete: (id: string) => this.delete(STORES.incidents, id),
      clear: () => this.clear(STORES.incidents),
    };
  }

  get resources() {
    return {
      put: <T extends { id: string }>(item: T) => this.put(STORES.resources, item),
      putMany: <T extends { id: string }>(items: T[]) => this.putMany(STORES.resources, items),
      get: <T>(id: string) => this.get<T>(STORES.resources, id),
      getAll: <T>() => this.getAll<T>(STORES.resources),
      getByStatus: <T>(status: string) => this.getByIndex<T>(STORES.resources, 'status', status),
      delete: (id: string) => this.delete(STORES.resources, id),
      clear: () => this.clear(STORES.resources),
    };
  }

  get alerts() {
    return {
      put: <T extends { id: string }>(item: T) => this.put(STORES.alerts, item),
      putMany: <T extends { id: string }>(items: T[]) => this.putMany(STORES.alerts, items),
      get: <T>(id: string) => this.get<T>(STORES.alerts, id),
      getAll: <T>() => this.getAll<T>(STORES.alerts),
      getBySeverity: <T>(severity: string) => this.getByIndex<T>(STORES.alerts, 'severity', severity),
      delete: (id: string) => this.delete(STORES.alerts, id),
      clear: () => this.clear(STORES.alerts),
    };
  }
}

// Singleton instance
export const offlineDb = new OfflineDatabase();
