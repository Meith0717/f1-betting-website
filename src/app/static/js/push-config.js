/**
 * Web Push Notification Configuration for F1 Betting Platform
 * 
 * This module handles:
 * - Checking browser support for notifications
 * - Requesting notification permission (must be triggered by user gesture)
 * - Subscribing to push notifications
 * - Sending subscription data to the server
 * - Handling subscription errors
 */

// Application server public key from .env (will be set when page loads)
let applicationServerKey = null;
let keyLoaded = false;
let keyPromise = null;

/**
 * Wait for VAPID key to be loaded
 * @returns {Promise<void>}
 */
async function waitForKey() {
  if (keyLoaded) return;
  if (keyPromise) return keyPromise;
  
  keyPromise = new Promise((resolve) => {
    const check = () => {
      if (keyLoaded) {
        resolve();
      } else {
        setTimeout(check, 100);
      }
    };
    check();
  });
  return keyPromise;
}

/**
 * Convert a base64 string to a Uint8Array.
 * Used to convert VAPID public key for the browser.
 * 
 * @param {string} base64String - The base64-encoded string
 * @returns {Uint8Array} The decoded Uint8Array
 */
function urlBase64ToUint8Array(base64String) {
  // Remove padding characters
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  
  // Decode using atob
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  
  return outputArray;
}

/**
 * Check if the browser supports Web Push notifications.
 * 
 * @returns {Promise<boolean>} True if notifications are supported
 */
async function isNotificationsSupported() {
  // Check if service workers are supported
  if (!('serviceWorker' in navigator)) {
    console.log('[Push] Service Worker not supported');
    return false;
  }
  
  // Check if PushManager is available
  if (!('PushManager' in window)) {
    console.log('[Push] Push API not supported');
    return false;
  }
  
  // Check if notifications are supported
  if (!('Notification' in window)) {
    console.log('[Push] Notification API not supported');
    return false;
  }
  
  return true;
}

/**
 * Check current notification permission state.
 * 
 * @returns {string} One of: 'granted', 'denied', 'default'
 */
function getNotificationPermission() {
  return Notification.permission;
}

/**
 * Request notification permission from the user.
 * 
 * IMPORTANT: This MUST be called from a user gesture (click handler, etc.)
 * Browsers will block permission requests not triggered by user action.
 * 
 * @returns {Promise<string>} The permission state: 'granted', 'denied', or 'default'
 */
async function requestNotificationPermission() {
  try {
    const permission = await Notification.requestPermission();
    console.log('[Push] Notification permission:', permission);
    return permission;
  } catch (error) {
    console.error('[Push] Error requesting permission:', error);
    return 'denied';
  }
}

/**
 * Subscribe to push notifications.
 * 
 * IMPORTANT: Must be called after permission is granted.
 * This should also be triggered by a user gesture due to browser requirements.
 * 
 * @param {ServiceWorkerRegistration} registration - The service worker registration
 * @returns {Promise<PushSubscription>} The push subscription object, or null on failure
 */
async function subscribeToPush(registration) {
  // Wait for key to be loaded
  await waitForKey();
  
  if (!applicationServerKey) {
    console.error('[Push] Application server key not set');
    alert('Push notifications are not configured on the server. Please contact the administrator.');
    return null;
  }
  
  try {
    // Convert VAPID public key to Uint8Array
    const applicationServerKeyUint8 = urlBase64ToUint8Array(applicationServerKey);
    
    // Subscribe to push notifications
    console.log('[Push] Subscribing to push notifications...');
    
    // Subscribe to push notifications
    // Note: userVisibleOnly is required by Chrome, but Firefox doesn't support it
    // We detect Firefox and omit it for compatibility
    const isFirefox = navigator.userAgent.includes('Firefox');
    const subscribeOptions = {
      applicationServerKey: applicationServerKeyUint8
    };
    
    // Add userVisibleOnly for Chrome/Edge (required for these browsers)
    if (!isFirefox) {
      subscribeOptions.userVisibleOnly = true;
    }
    
    const subscription = await registration.pushManager.subscribe(subscribeOptions);
    
    console.log('[Push] Subscription successful:', subscription);
    return subscription;
  } catch (error) {
    console.error('[Push] Subscription failed:', error);
    
    // Handle specific errors with user-friendly messages
    let message = 'Failed to subscribe. Please try again.';
    if (error.name === 'NotAllowedError') {
      message = 'Notification permission was denied. Please allow notifications and try again.';
    } else if (error.name === 'InvalidStateError') {
      message = 'Service Worker not ready. Please refresh the page and try again.';
    } else if (error.message) {
      message = error.message;
    }
    console.error('[Push] Unknown error:', error.message);
    
    alert(message);
    return null;
  }
}

/**
 * Unsubscribe from push notifications.
 * 
 * @param {PushSubscription} subscription - The subscription to remove
 * @returns {Promise<boolean>} True if unsubscribed successfully
 */
async function unsubscribeFromPush(subscription) {
  try {
    const result = await subscription.unsubscribe();
    console.log('[Push] Unsubscribed', result ? 'successfully' : 'unsuccessfully');
    return result;
  } catch (error) {
    console.error('[Push] Error unsubscribing:', error);
    return false;
  }
}

/**
 * Send subscription data to the server for storage.
 * 
 * @param {PushSubscription} subscription - The push subscription object
 * @param {string} username - The current user's username
 * @returns {Promise<Response>} The fetch response
 */
async function saveSubscriptionToServer(subscription, username) {
  // Extract subscription details
  const subscriptionData = {
    endpoint: subscription.endpoint,
    keys: {
      p256dh: subscription.options.applicationServerKey 
        ? btoa(String.fromCharCode.apply(null, subscription.options.applicationServerKey))
        : subscription.toJSON().keys.p256dh,
      auth: subscription.toJSON().keys.auth
    }
  };
  
  // For some browsers, we need to get the keys differently
  const jsonSubscription = subscription.toJSON();
  const keys = jsonSubscription.keys || subscriptionData.keys;
  
  const payload = {
    username: username,
    subscription: jsonSubscription
  };
  
  try {
    const response = await fetch('/api/save-subscription', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': JSON.stringify(payload).length.toString()
      },
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('[Push] Server error:', response.status, errorText);
      throw new Error(`Server responded with ${response.status}: ${errorText}`);
    }
    
    const result = await response.json();
    console.log('[Push] Subscription saved to server:', result);
    return response;
  } catch (error) {
    console.error('[Push] Error saving subscription:', error);
    throw error;
  }
}

/**
 * Remove subscription from the server.
 * 
 * @param {string} username - The user's username
 * @param {string} endpoint - The subscription endpoint to remove
 * @returns {Promise<Response>} The fetch response
 */
async function removeSubscriptionFromServer(username, endpoint) {
  try {
    const response = await fetch('/api/remove-subscription', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: username,
        endpoint: endpoint
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('[Push] Server error removing subscription:', response.status, errorText);
    }
    
    return response;
  } catch (error) {
    console.error('[Push] Error removing subscription from server:', error);
    throw error;
  }
}

/**
 * Initialize push notifications.
 * Call this when the page loads to fetch the VAPID public key from the server.
 * 
 * @param {string} vapidPublicKey - Optional: The base64url-encoded VAPID public key
 *                                 If not provided, will be fetched from /api/vapid-public-key
 * @returns {Promise<void>}
 */
async function initPushNotifications(vapidPublicKey = null) {
  if (keyLoaded) return; // Already initialized
  
  try {
    if (vapidPublicKey) {
      applicationServerKey = vapidPublicKey;
      console.log('[Push] Initialized with provided VAPID public key');
    } else {
      // Fetch from server
      const response = await fetch('/api/vapid-public-key');
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      const data = await response.json();
      if (data.success && data.vapidPublicKey) {
        applicationServerKey = data.vapidPublicKey;
        console.log('[Push] Initialized with VAPID public key from server');
      } else {
        throw new Error(data.error || 'No VAPID public key in response');
      }
    }
    
    keyLoaded = true;
    keyPromise = null;
  } catch (error) {
    console.error('[Push] Failed to fetch VAPID public key:', error);
    // Continue without push notifications - user won't be able to subscribe
  }
}

/**
 * Initialize push notifications automatically on page load.
 * This is a convenience function that calls initPushNotifications() without arguments.
 */
function autoInitPushNotifications() {
  // Only run in browser environment
  if (typeof window !== 'undefined') {
    // Initialize on DOMContentLoaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => {
        initPushNotifications();
      });
    } else {
      // DOM already loaded
      initPushNotifications();
    }
  }
}

/**
 * Main function to enable push notifications.
 * 
 * IMPORTANT: This MUST be called from a user gesture (e.g., button click).
 * 
 * Usage:
 *   <button onclick="enablePushNotifications()">Enable Notifications</button>
 * 
 * @param {string} username - The current user's username
 * @returns {Promise<void>}
 */
async function enablePushNotifications(username) {
  // Check if supported
  const supported = await isNotificationsSupported();
  if (!supported) {
    alert('Your browser does not support Web Push notifications.');
    return;
  }
  
  // Check current permission
  const currentPermission = getNotificationPermission();
  
  if (currentPermission === 'granted') {
    // Already have permission, just subscribe
    console.log('[Push] Permission already granted, subscribing...');
    await subscribeAndSave(username);
    return;
  }
  
  if (currentPermission === 'denied') {
    alert('Notification permission was denied. Please enable it in your browser settings.');
    return;
  }
  
  // Request permission (must be in user gesture)
  const permission = await requestNotificationPermission();
  
  if (permission === 'granted') {
    // Permission granted, subscribe and save
    await subscribeAndSave(username);
  } else {
    console.log('[Push] Notification permission denied');
    alert('Notification permission denied. You can enable it later in your browser settings.');
  }
}

/**
 * Subscribe to push notifications and save to server.
 * 
 * @param {string} username - The current user's username
 * @returns {Promise<PushSubscription|null>}
 */
async function subscribeAndSave(username) {
  try {
    // Get the existing service worker registration
    const registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      // If not registered, use the default static path
      console.log('[Push] No existing registration, registering at /static/sw.js');
      // Note: We don't register here - it should already be registered by base.html
      // If it's not registered, something is wrong
      alert('Service Worker is not registered. Please refresh the page and try again.');
      return null;
    }
    
    console.log('[Push] Using existing Service Worker registration');
    
    // Wait for service worker to be active
    await navigator.serviceWorker.ready;
    console.log('[Push] Service Worker ready');
    
    // Subscribe to push
    const subscription = await subscribeToPush(registration);
    
    if (subscription) {
      // Save subscription to server
      await saveSubscriptionToServer(subscription, username);
      console.log('[Push] Notifications enabled successfully!');
      return subscription;
    } else {
      console.log('[Push] Subscription failed');
      return null;
    }
  } catch (error) {
    console.error('[Push] Error in subscribeAndSave:', error);
    alert('Failed to enable notifications. Please try again.');
    return null;
  }
}

/**
 * Disable push notifications for the current user.
 * 
 * @param {string} username - The current user's username
 * @returns {Promise<void>}
 */
async function disablePushNotifications(username) {
  try {
    // Get existing registration
    const registration = await navigator.serviceWorker.getRegistration();
    
    if (!registration) {
      console.error('[Push] No Service Worker registration found');
      return;
    }
    
    // Get current subscription
    const subscription = await registration.pushManager.getSubscription();
    
    if (subscription) {
      // Unsubscribe
      await unsubscribeFromPush(subscription);
      
      // Remove from server
      await removeSubscriptionFromServer(username, subscription.endpoint);
      
      console.log('[Push] Notifications disabled successfully');
      alert('🔔 Push notifications disabled');
    } else {
      console.log('[Push] No active subscription found');
      alert('No active notification subscription found.');
    }
  } catch (error) {
    console.error('[Push] Error disabling notifications:', error);
    alert('Failed to disable notifications.');
  }
}

/**
 * Check current notification status.
 * 
 * @returns {Promise<{supported: boolean, permission: string, subscribed: boolean}>}
 */
async function checkNotificationStatus() {
  const supported = await isNotificationsSupported();
  const permission = getNotificationPermission();
  
  let subscribed = false;
  
  if (supported && permission === 'granted') {
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration) {
        const subscription = await registration.pushManager.getSubscription();
        subscribed = !!subscription;
      }
    } catch (error) {
      console.error('[Push] Error checking subscription:', error);
    }
  }
  
  return {
    supported,
    permission,
    subscribed
  };
}

// Expose functions to global scope for HTML onclick handlers
window.enablePushNotifications = enablePushNotifications;
window.disablePushNotifications = disablePushNotifications;
window.checkNotificationStatus = checkNotificationStatus;
window.initPushNotifications = initPushNotifications;
window.autoInitPushNotifications = autoInitPushNotifications;

// Auto-initialize on page load
if (typeof window !== 'undefined') {
    autoInitPushNotifications();
}
