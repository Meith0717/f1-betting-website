/**
 * PWA Install Prompt for iOS Safari and other browsers
 * 
 * Features:
 * - Detects iOS Safari and shows "Add to Home Screen" nudge
 * - Detects Chrome/Android and shows install prompt
 * - Remembers if user has already been prompted
 * - Tracks if user has already installed the PWA
 */

// Check if running in a browser
if (typeof window === 'undefined') {
  module.exports = {}; // Node.js environment
} else {
  (function() {
    'use strict';

    // Storage key for tracking if user has been prompted
    const PROMPTED_KEY = 'f1Betting_pwaPrompted';
    const INSTALLED_KEY = 'f1Betting_pwaInstalled';
    const DISMISSED_KEY = 'f1Betting_pwaDismissed';

    // iOS Safari detection
    const isIOSSafari = () => {
      const userAgent = window.navigator.userAgent;
      const isIOS = /iPhone|iPad|iPod/i.test(userAgent);
      const isSafari = /Safari/i.test(userAgent);
      const isChrome = /CriOS|FxiOS|EdgiOS|OPiOS/i.test(userAgent);
      return isIOS && isSafari && !isChrome;
    };

    // Android Chrome detection
    const isAndroidChrome = () => {
      const userAgent = window.navigator.userAgent;
      const isAndroid = /Android/i.test(userAgent);
      const isChrome = /Chrome/i.test(userAgent);
      return isAndroid && isChrome;
    };

    // Check if PWA is already installed (running in standalone mode)
    const isPWAInstalled = () => {
      return window.matchMedia('(display-mode: standalone)').matches ||
             window.matchMedia('(display-mode: fullscreen)').matches ||
             window.navigator.standalone ||
             localStorage.getItem(INSTALLED_KEY) === 'true';
    };

    // Check if deferred prompt is available (Chrome conditional install)
    let deferredPrompt = null;

    // Track if we've shown the prompt
    let promptShown = false;

    // iOS install instructions
    const IOS_INSTRUCTIONS = {
      title: 'Install F1 Betting App',
      message: 'Tap <strong>Share</strong> below, then <strong>Add to Home Screen</strong> to install.',
      buttonText: 'Got it!',
      icon: '📱'
    };

    // Android install instructions
    const ANDROID_INSTRUCTIONS = {
      title: 'Install F1 Betting App',
      message: 'Tap <strong>Install</strong> in the browser menu to add this app to your home screen.',
      buttonText: 'Install',
      icon: '📱'
    };

    /**
     * Create and show the iOS/Android install banner
     */
    function showInstallBanner(instructions) {
      // Check if already prompted
      if (localStorage.getItem(PROMPTED_KEY) === 'true' ||
          localStorage.getItem(DISMISSED_KEY) === 'true') {
        return;
      }

      // Don't show if already installed
      if (isPWAInstalled()) {
        localStorage.setItem(INSTALLED_KEY, 'true');
        return;
      }

      // Create banner element
      const banner = document.createElement('div');
      banner.id = 'pwa-install-banner';
      banner.className = 'pwa-install-banner';
      banner.style.cssText = `
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #e10600, #c40404);
        color: white;
        padding: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 10000;
        box-sizing: border-box;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
      `;

      // Banner content
      banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px; overflow: hidden;">
          <span style="font-size: 24px;">${instructions.icon}</span>
          <div style="min-width: 0; flex: 1;">
            <div style="font-weight: 600; font-size: 16px; margin-bottom: 4px;">${instructions.title}</div>
            <div style="font-size: 14px; opacity: 0.9;">${instructions.message}</div>
          </div>
        </div>
        <button id="pwa-install-confirm" 
                style="background: white; color: #e10600; border: none; 
                       padding: 10px 20px; border-radius: 6px; 
                       font-weight: 600; font-size: 14px; cursor: pointer;
                       min-width: 100px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
          ${instructions.buttonText}
        </button>
        <button id="pwa-install-close" 
                style="background: transparent; border: none; color: white; 
                       font-size: 20px; cursor: pointer; padding: 8px;
                       opacity: 0.8;">
          ×
        </button>
      `;

      // Add banner to body
      document.body.appendChild(banner);
      promptShown = true;
      localStorage.setItem(PROMPTED_KEY, 'true');

      // Close button
      banner.querySelector('#pwa-install-close').addEventListener('click', () => {
        banner.style.transform = 'translateY(100%)';
        banner.style.transition = 'transform 0.3s ease-out';
        setTimeout(() => banner.remove(), 300);
        localStorage.setItem(DISMISSED_KEY, 'true');
      });

      // Confirm button - trigger install
      banner.querySelector('#pwa-install-confirm').addEventListener('click', () => {
        triggerInstall();
        banner.style.transform = 'translateY(100%)';
        banner.style.transition = 'transform 0.3s ease-out';
        setTimeout(() => banner.remove(), 300);
      });

      // Auto-hide after 10 seconds
      setTimeout(() => {
        if (banner.parentNode) {
          banner.style.transform = 'translateY(100%)';
          banner.style.transition = 'transform 0.3s ease-out';
          setTimeout(() => banner.remove(), 300);
        }
      }, 10000);
    }

    /**
     * Trigger PWA install based on platform
     */
    function triggerInstall() {
      if (deferredPrompt) {
        // Chrome/Edge on Android/Desktop
        deferredPrompt.prompt();
        
        deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('[PWA] User accepted install prompt');
            localStorage.setItem(INSTALLED_KEY, 'true');
          } else {
            console.log('[PWA] User dismissed install prompt');
          }
          deferredPrompt = null;
        });
      } else if (isIOSSafari()) {
        // iOS - just show instructions again
        showIOSShareInstructions();
      }
    }

    /**
     * Show iOS share instructions
     */
    function showIOSShareInstructions() {
      // Show a more persistent instruction
      const existing = document.getElementById('pwa-ios-instructions');
      if (existing) existing.remove();

      const iosGuide = document.createElement('div');
      iosGuide.id = 'pwa-ios-instructions';
      iosGuide.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: white;
        border-radius: 12px;
        padding: 16px;
        max-width: 280px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        z-index: 10000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      `;

      iosGuide.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px;">
          <span style="font-size: 20px;">📱</span>
          <div>
            <div style="font-weight: 600; font-size: 14px; color: #333;">Install F1 Betting</div>
            <div style="font-size: 12px; color: #666; line-height: 1.4;">
              Tap <strong>Share → Add to Home Screen</strong>
            </div>
          </div>
        </div>
        <button onclick="this.parentElement.remove()" 
                style="background: #e10600; color: white; border: none; 
                       padding: 8px 12px; border-radius: 6px; 
                       font-size: 12px; cursor: pointer; font-weight: 500;">
          Close
        </button>
      `;

      document.body.appendChild(iosGuide);

      // Auto-remove after 15 seconds
      setTimeout(() => {
        if (iosGuide.parentNode) {
          iosGuide.remove();
        }
      }, 15000);
    }

    /**
     * Show the install button in the UI
     * Can be called from template to add a persistent install button
     */
    function showInstallButton() {
      const btn = document.createElement('button');
      btn.id = 'pwa-install-button';
      btn.className = 'pwa-install-button';
      btn.textContent = 'Install App';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #e10600, #c40404);
        color: white;
        border: none;
        border-radius: 50%;
        width: 56px;
        height: 56px;
        font-size: 12px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(225, 6, 0, 0.4);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s, box-shadow 0.2s;
      `;

      btn.addEventListener('click', triggerInstall);
      
      // Hover effect
      btn.addEventListener('mouseenter', () => {
        btn.style.transform = 'scale(1.05)';
        btn.style.boxShadow = '0 6px 16px rgba(225, 6, 0, 0.6)';
      });
      
      btn.addEventListener('mouseleave', () => {
        btn.style.transform = 'scale(1)';
        btn.style.boxShadow = '0 4px 12px rgba(225, 6, 0, 0.4)';
      });

      document.body.appendChild(btn);
      return btn;
    }

    /**
     * Initialize PWA install prompt logic
     */
    function initPWAInstall() {
      // Don't run if already installed
      if (isPWAInstalled()) {
        console.log('[PWA] Already installed as PWA');
        return;
      }

      // Listen for beforeinstallprompt event (Chrome/Edge)
      window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        console.log('[PWA] beforeinstallprompt event received');

        // For Chrome on desktop/Android, show the banner
        if (isAndroidChrome() || !isIOSSafari()) {
          showInstallBanner(ANDROID_INSTRUCTIONS);
        }
      });

      // For iOS Safari, check on page load
      if (isIOSSafari()) {
        // Delay slightly to let page load
        setTimeout(() => {
          showInstallBanner(IOS_INSTRUCTIONS);
        }, 2000);
      }

      // Listen for appinstalled event
      window.addEventListener('appinstalled', () => {
        console.log('[PWA] App installed');
        localStorage.setItem(INSTALLED_KEY, 'true');
        
        // Remove any visible banners
        const banner = document.getElementById('pwa-install-banner');
        if (banner) banner.remove();
        
        const iosGuide = document.getElementById('pwa-ios-instructions');
        if (iosGuide) iosGuide.remove();
        
        const btn = document.getElementById('pwa-install-button');
        if (btn) btn.remove();
      });

      // Check periodically if user installed via iOS method
      setInterval(() => {
        if (isPWAInstalled() && localStorage.getItem(INSTALLED_KEY) !== 'true') {
          localStorage.setItem(INSTALLED_KEY, 'true');
          const banner = document.getElementById('pwa-install-banner');
          if (banner) banner.remove();
          const iosGuide = document.getElementById('pwa-ios-instructions');
          if (iosGuide) iosGuide.remove();
        }
      }, 5000);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initPWAInstall);
    } else {
      initPWAInstall();
    }

    // Expose to global scope for manual control
    window.showPWAInstallBanner = showInstallBanner;
    window.showPWAInstallButton = showInstallButton;
    window.triggerPWAInstall = triggerInstall;
    window.isPWAInstalled = isPWAInstalled;

  })();
}
