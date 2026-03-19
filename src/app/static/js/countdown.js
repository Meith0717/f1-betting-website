/**
 * F1 Betting Platform - Countdown Timer
 * Handles real-time countdown for next F1 sessions
 */

/**
 * Initialize countdown timer for next session
 */
function initializeCountdown() {
    const countdownElement = document.getElementById('session-countdown-inline');
    if (!countdownElement) return;
    
    // Get the session ISO time from the template
    const sessionTime = countdownElement.getAttribute('data-session-time');
    
    if (sessionTime) {
        try {
            // Parse the ISO time and create countdown
            const sessionDate = new Date(sessionTime);
            const now = new Date();
            
            // Only show countdown if session is in the future
            if (sessionDate > now) {
                updateCountdown(sessionDate, countdownElement, true); // inline format
                const timer = setInterval(() => updateCountdown(sessionDate, countdownElement, true), 1000);
                countdownElement.dataset.timerId = timer;
            } else {
                countdownElement.innerHTML = '<span class="countdown-expired">Started</span>';
            }
        } catch (error) {
            console.error('Error initializing countdown:', error);
            countdownElement.innerHTML = '<span class="countdown-unavailable">--:--:--</span>';
        }
    }
}

/**
 * Update countdown display
 * @param {Date} targetDate - Target date/time
 * @param {HTMLElement} element - Element to update
 * @param {boolean} isInline - Whether to use inline format
 */
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
    let countdownText = '';
    if (isInline) {
        // Compact format for inline: HH:MM:SS or DDd HH:MM:SS
        if (days > 0) countdownText += `${days}d `;
        countdownText += `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    } else {
        // Detailed format for full display
        if (days > 0) countdownText += `${days}d `;
        if (hours > 0 || days > 0) countdownText += `${hours.toString().padStart(2, '0')}:`;
        countdownText += `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    element.innerHTML = `<span class="countdown-active">${countdownText}</span>`;
}

/**
 * Race card toggle functionality
 */
function toggleRaceCard(raceId) {
    const raceCard = document.querySelector(`.race-card[data-race-id="${raceId}"]`);
    if (raceCard) {
        raceCard.classList.toggle('expanded');
        
        const icon = raceCard.querySelector('.expand-icon');
        if (icon) {
            icon.textContent = raceCard.classList.contains('expanded') ? '▲' : '▼';
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize countdown timer
    initializeCountdown();
    
    // Set up race card toggle handlers
    document.querySelectorAll('.race-header, .expand-icon').forEach(element => {
        element.addEventListener('click', function() {
            const raceCard = this.closest('.race-card');
            if (raceCard) {
                const raceId = raceCard.getAttribute('data-race-id');
                toggleRaceCard(raceId);
            }
        });
    });
});