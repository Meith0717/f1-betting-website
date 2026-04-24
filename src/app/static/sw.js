// Web Push Notifications
// ============================================

// Application server public key - will be set from frontend
let applicationServerKey = null;

// Listen for push messages
self.addEventListener('push', event => {
  console.log('[Service Worker] Push received');
  
  // CRITICAL: iOS 2026 requires event.waitUntil with showNotification
  // otherwise permission will be revoked
  event.waitUntil(
    self.registration.showNotification(
      event.data?.json()?.title || 'F1 Betting Notification',
      {
        body: event.data?.json()?.body || 'You have a new notification',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-192x192.png',
        data: event.data?.json()?.data || {},
        actions: event.data?.json()?.actions || []
      }
    )
  );
});

// Listen for notification clicks
self.addEventListener('notificationclick', event => {
  console.log('[Service Worker] Notification clicked');
  
  event.notification.close();
  
  // Handle action button clicks
  if (event.action) {
    console.log('[Service Worker] Action clicked:', event.action);
    // Could open different URLs based on action
  }
  
  // Open the application URL
  // Default to the main page, or use data.url if provided
  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then((clientList) => {
      // Check if there's already a window/tab open with this URL
      for (const client of clientList) {
        if (client.url.includes(urlToOpen) && 'focus' in client) {
          return client.focus();
        }
      }
      
      // If no matching window, open a new one
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// Listen for push subscription change (when subscription expires)
self.addEventListener('pushsubscriptionchange', event => {
  console.log('[Service Worker] Push subscription expired');
  
  event.waitUntil(
    // The old subscription is no longer valid, unsubscribe it
    event.oldSubscription.unsubscribe().then(() => {
      // TODO: Subscribe again and send new subscription to server
      console.log('[Service Worker] Old subscription unsubscribed');
    })
  );
});
=======
// ============================================
// Web Push Notifications
// ============================================

// Listen for push messages
self.addEventListener('push', event => {
  console.log('[Service Worker] Push received');
  
  // Safely parse data - handle case where event.data is undefined or not JSON
  let title = 'F1 Betting Notification';
  let body = 'You have a new notification';
  let icon = '/static/icons/icon-192x192.png';
  let data = {};
  let url = '/';
  
  try {
    if (event.data) {
      const jsonData = event.data.json();
      if (jsonData) {
        title = jsonData.title || title;
        body = jsonData.body || body;
        data = jsonData.data || {};
        url = jsonData.url || url;
      }
    }
  } catch (e) {
    console.log('[Service Worker] Error parsing push data:', e);
  }
  
  // CRITICAL: iOS 2026 requires event.waitUntil with showNotification
  // otherwise permission will be revoked
  event.waitUntil(
    self.registration.showNotification(title, {
      body: body,
      icon: icon,
      data: data,
      requireInteraction: true
    }).then(() => {
      console.log('[Service Worker] Notification shown');
    }).catch(err => {
      console.error('[Service Worker] Error showing notification:', err);
    })
  );
});

// Listen for notification clicks
self.addEventListener('notificationclick', event => {
  console.log('[Service Worker] Notification clicked');
  
  // Close the notification
  if (event.notification) {
    event.notification.close();
  }
  
  // Open the application URL
  // Default to the main page, or use data.url if provided
  let urlToOpen = '/ ';
  try {
    urlToOpen = (event.notification && event.notification.data && event.notification.data.url) || '/';
  } catch (e) {
    urlToOpen = '/';
  }
  
  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then((clientList) => {
      // Check if there's already a window/tab open with this URL
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        try {
          if (client.url && client.url.includes(urlToOpen) && 'focus' in client) {
            return client.focus();
          }
        } catch (e) {
          // Skip this client
        }
      }
      
      // If no matching window, open a new one
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
      
      return Promise.resolve();
    })
  );
});

// Listen for push subscription change (when subscription expires)
self.addEventListener('pushsubscriptionchange', event => {
  console.log('[Service Worker] Push subscription expired');
  
  event.waitUntil(
    Promise.resolve().then(() => {
      // The old subscription is no longer valid
      if (event.oldSubscription) {
        return event.oldSubscription.unsubscribe().then(() => {
          console.log('[Service Worker] Old subscription unsubscribed');
        });
      }
    })
  );
});Basic Service Worker for F1 Betting Platform
const CACHE_NAME = 'f1-betting-v1';
const urlsToCache = [
  '/',
  '/static/css/mobile-styles.css',
  '/static/manifest.json',
  '/static/icons/apple-touch-icon.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

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
  );
});

// ============================================
// Web Push Notifications
// ============================================

// Application server public key - will be set from frontend
let applicationServerKey = null;

// Listen for push messages
self.addEventListener('push', event => {
  console.log('[Service Worker] Push received');
  
  // CRITICAL: iOS 2026 requires event.waitUntil with showNotification
  // otherwise permission will be revoked
  event.waitUntil(
    self.registration.showNotification(
      event.data?.json()?.title || 'F1 Betting Notification',
      {
        body: event.data?.json()?.body || 'You have a new notification',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-192x192.png',
        data: event.data?.json()?.data || {},
        actions: event.data?.json()?.actions || []
      }
    )
  );
});

// Listen for notification clicks
self.addEventListener('notificationclick', event => {
  console.log('[Service Worker] Notification clicked');
  
  event.notification.close();
  
  // Handle action button clicks
  if (event.action) {
    console.log('[Service Worker] Action clicked:', event.action);
    // Could open different URLs based on action
  }
  
  // Open the application URL
  // Default to the main page, or use data.url if provided
  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then((clientList) => {
      // Check if there's already a window/tab open with this URL
      for (const client of clientList) {
        if (client.url.includes(urlToOpen) && 'focus' in client) {
          return client.focus();
        }
      }
      
      // If no matching window, open a new one
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// Listen for push subscription change (when subscription expires)
self.addEventListener('pushsubscriptionchange', event => {
  console.log('[Service Worker] Push subscription expired');
  
  event.waitUntil(
    // The old subscription is no longer valid, unsubscribe it
    event.oldSubscription.unsubscribe().then(() => {
      // TODO: Subscribe again and send new subscription to server
      console.log('[Service Worker] Old subscription unsubscribed');
    })
  );
});