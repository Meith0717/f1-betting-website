// Admin Dashboard JavaScript
function toggleLogWrap() {
  const logContainer = document.getElementById('logContainer');
  if (logContainer) {
    logContainer.classList.toggle('log-wrap');
  }
}

function toggleEventLogWrap() {
  const logContainer = document.getElementById('eventLogContainer');
  if (logContainer) {
    logContainer.classList.toggle('log-wrap');
  }
}

// Mobile menu toggle for admin dashboard
document.addEventListener('DOMContentLoaded', function() {
  // Add any admin-specific mobile enhancements here
});