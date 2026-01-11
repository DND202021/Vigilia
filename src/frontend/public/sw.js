/**
 * ERIOP Service Worker
 * Provides offline capability and caching
 */

const CACHE_NAME = 'eriop-cache-v1';
const API_CACHE_NAME = 'eriop-api-cache-v1';

// Static assets to cache
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
];

// API routes to cache
const API_ROUTES = [
  '/api/v1/incidents/active',
  '/api/v1/resources/available',
  '/api/v1/alerts/pending',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Install');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activate');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== API_CACHE_NAME)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request));
    return;
  }

  // Handle static assets
  event.respondWith(handleStaticRequest(request));
});

// Handle API requests with network-first strategy
async function handleApiRequest(request) {
  const cache = await caches.open(API_CACHE_NAME);

  try {
    // Try network first
    const networkResponse = await fetch(request);

    // Cache successful responses for certain routes
    if (networkResponse.ok && shouldCacheApiRoute(request.url)) {
      const responseClone = networkResponse.clone();
      cache.put(request, responseClone);
    }

    return networkResponse;
  } catch (error) {
    // Network failed, try cache
    console.log('[SW] Network failed, trying cache:', request.url);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      console.log('[SW] Serving from cache:', request.url);
      return cachedResponse;
    }

    // Return offline response for API
    return new Response(
      JSON.stringify({ error: 'offline', message: 'No cached data available' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

// Handle static requests with cache-first strategy
async function handleStaticRequest(request) {
  const cache = await caches.open(CACHE_NAME);

  // Check cache first
  const cachedResponse = await cache.match(request);
  if (cachedResponse) {
    // Refresh cache in background
    refreshCache(request, cache);
    return cachedResponse;
  }

  try {
    // Not in cache, fetch from network
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    // Network failed, return offline page for navigation requests
    if (request.mode === 'navigate') {
      return cache.match('/index.html');
    }

    return new Response('Offline', { status: 503 });
  }
}

// Refresh cache in background
async function refreshCache(request, cache) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse);
    }
  } catch (error) {
    // Ignore errors during background refresh
  }
}

// Check if API route should be cached
function shouldCacheApiRoute(url) {
  const path = new URL(url).pathname;
  return API_ROUTES.some((route) => path.includes(route));
}

// Listen for messages from main thread
self.addEventListener('message', (event) => {
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'CLEAR_CACHE') {
    caches.delete(CACHE_NAME);
    caches.delete(API_CACHE_NAME);
    event.ports[0].postMessage({ success: true });
  }
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-incidents') {
    event.waitUntil(syncIncidents());
  }

  if (event.tag === 'sync-resources') {
    event.waitUntil(syncResources());
  }
});

// Sync incidents with server
async function syncIncidents() {
  // This will be handled by the main app's sync service
  // Notify all clients to trigger sync
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_TRIGGERED', target: 'incidents' });
  });
}

// Sync resources with server
async function syncResources() {
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_TRIGGERED', target: 'resources' });
  });
}

// Push notification handling
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();

  const options = {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
    },
    actions: data.actions || [],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'ERIOP Alert', options)
  );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const url = event.notification.data?.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      // Check if there's already a window open
      for (const client of clients) {
        if (client.url.includes(self.location.origin)) {
          client.focus();
          client.navigate(url);
          return;
        }
      }
      // Open new window
      return self.clients.openWindow(url);
    })
  );
});

console.log('[SW] Service worker loaded');
