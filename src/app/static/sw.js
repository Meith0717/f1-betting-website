// Service Worker for F1 Betting Platform
// Handles caching and push notifications

const CACHE_NAME = 'f1-betting-v3';
const urlsToCache = [
  // Don't cache '/' as it's user-specific (logged in vs welcome page)
  '/static/css/mobile-styles.css',
  '/static/manifest.json',
  '/static/icons/apple-touch-icon.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Install - cache core assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
      .then(() => console.log('[SW] Installed'))
      .then(() => self.skipWaiting()) // Force the waiting service worker to become active immediately
      .catch(err => console.error('[SW] Install failed:', err))
  );
});

// Activate - clean old caches
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(() => self.clients.claim()) // Take control of all clients immediately
  );
});

// Fetch - Network-first strategy for HTML, cache-first for static assets
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // For HTML pages (including /), always go to network first
  // This ensures logged-in users see their dashboard, not cached welcome page
  if (url.pathname === '/' || url.pathname.endsWith('.html')) {
    event.respondWith(
      fetch(event.request).then(response => {
        // Clone and cache the response
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, responseClone);
        });
        return response;
      }).catch(() => {
        // If network fails, try cache
        return caches.match(event.request);
      })
    );
    return;
  }
  
  // For static assets, use cache-first strategy
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});

// Push notifications
self.addEventListener('push', event => {
  console.log('[SW] Push received');

  let title = 'F1 Betting Notification';
  let body = 'You have a new notification';
  let icon = '/static/icons/icon-192x192.png';
  let data = {};

  try {
    if (event.data) {
      const jsonData = event.data.json();
      if (jsonData) {
        title = jsonData.title || title;
        body = jsonData.body || body;
        data = jsonData.data || {};
      }
    }
  } catch (e) {
    console.log('[SW] Error parsing push data:', e);
  }

  event.waitUntil(
    self.registration.showNotification(title, {
      body: body,
      icon: icon,
      data: data,
      requireInteraction: true
    }).catch(err => {
      console.error('[SW] Error showing notification:', err);
    })
  );
});

// Notification click handler
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked');

  if (event.notification) {
    event.notification.close();
  }

  const urlToOpen = (event.notification && event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then(clientList => {
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        try {
          if (client.url && client.url.includes(urlToOpen) && 'focus' in client) {
            return client.focus();
          }
        } catch (e) { /* skip */ }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
      return Promise.resolve();
    })
  );
});

// Push subscription expired
self.addEventListener('pushsubscriptionchange', event => {
  console.log('[SW] Push subscription expired');
  event.waitUntil(
    Promise.resolve().then(() => {
      if (event.oldSubscription) {
        return event.oldSubscription.unsubscribe().then(() => {
          console.log('[SW] Old subscription unsubscribed');
        });
      }
    })
  );
});
