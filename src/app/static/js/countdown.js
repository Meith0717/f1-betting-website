// Session Countdown Timer
function initializeCountdown() {
  const countdownElement = document.getElementById("session-countdown-inline");
  if (!countdownElement) return;

  // Get the session ISO time from the template
  const sessionTime = countdownElement.dataset.sessionTime || "";

  if (sessionTime) {
    try {
      // Parse the ISO time and create countdown
      const sessionDate = new Date(sessionTime);
      const now = new Date();

      // Only show countdown if session is in the future
      if (sessionDate > now) {
        updateCountdown(sessionDate, countdownElement, true); // inline format
        const timer = setInterval(
          () => updateCountdown(sessionDate, countdownElement, true),
          1000,
        );
        countdownElement.dataset.timerId = timer;
      } else {
        countdownElement.innerHTML =
          '<span class="countdown-expired">Started</span>';
      }
    } catch (error) {
      console.error("Error initializing countdown:", error);
      countdownElement.innerHTML =
        '<span class="countdown-unavailable">--:--:--</span>';
    }
  }
}

function updateCountdown(targetDate, element, isInline = false) {
  const now = new Date();
  const diff = targetDate - now;

  if (diff <= 0) {
    // Check if this is a betting countdown timer
    if (element.id && element.id.startsWith('betting-countdown-')) {
      element.innerHTML = '⏰ <span class="countdown-expired">Betting closed</span>';
      console.log('Betting countdown expired, refreshing page...');
      // Refresh page to update bet status
      setTimeout(() => {
        console.log('Refreshing page now...');
        window.location.reload();
      }, 2000); // Refresh after 2 seconds to allow user to see the message
    } else {
      element.innerHTML = '<span class="countdown-expired">Started</span>';
    }
    return;
  }

  // Calculate time components
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  // Format the countdown
  let countdownText = "";
  if (isInline) {
    // Compact format for inline: HH:MM:SS or DDd HH:MM:SS
    if (days > 0) countdownText += `${days}d `;
    countdownText += `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  } else {
    // Detailed format for full display
    if (days > 0) countdownText += `${days}d `;
    if (hours > 0 || days > 0)
      countdownText += `${hours.toString().padStart(2, "0")}:`;
    countdownText += `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  }

  element.innerHTML = `⏰ <span class="countdown-active">${countdownText}</span>`;
}

function initializeBettingCountdowns() {
  // Handle both old format [id^="betting-closes-"] and new format [id^="betting-countdown-"]
  const bettingTimers = document.querySelectorAll('[id^="betting-closes-"], [id^="betting-countdown-"]');
  
  console.log(`Found ${bettingTimers.length} betting timer elements`);
  
  bettingTimers.forEach(timerElement => {
    console.log(`Initializing betting timer: ${timerElement.id}`);
    const raceTime = timerElement.dataset.raceTime || "";
    
    if (raceTime) {
      try {
        const raceDate = new Date(raceTime);
        const now = new Date();
        
        console.log(`Race date: ${raceDate}, Now: ${now}`);
        
        // Only show countdown if race is in the future
        if (raceDate > now) {
          updateCountdown(raceDate, timerElement, true); // inline format
          const timer = setInterval(
            () => updateCountdown(raceDate, timerElement, true),
            1000,
          );
          timerElement.dataset.timerId = timer;
        } else {
          timerElement.innerHTML =
            '⏰ <span class="countdown-expired">Betting closed</span>';
        }
      } catch (error) {
        console.error("Error initializing betting countdown:", error);
        timerElement.innerHTML =
          '⏰ <span class="countdown-unavailable">--:--:--</span>';
      }
    } else {
      console.warn(`No race time data for timer: ${timerElement.id}`);
    }
  });
}

// Initialize countdown when page loads
document.addEventListener("DOMContentLoaded", function() {
  initializeCountdown();
  initializeBettingCountdowns();
});
