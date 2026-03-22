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
    element.innerHTML = '<span class="countdown-expired">Started</span>';
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

  element.innerHTML = `<span class="countdown-active">${countdownText}</span>`;
}

// Initialize countdown when page loads
document.addEventListener("DOMContentLoaded", initializeCountdown);
