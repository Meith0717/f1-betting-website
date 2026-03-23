// Admin Dashboard Log Management Functions

function toggleLogWrap() {
  const logContainer = document.getElementById("logContainer");
  const logContent = logContainer.querySelector(".log-content");

  if (logContainer.classList.contains("wrap")) {
    logContainer.classList.remove("wrap");
    logContent.classList.remove("wrap");
  } else {
    logContainer.classList.add("wrap");
    logContent.classList.add("wrap");
  }
}

function clearLogs() {
  if (
    confirm(
      "Are you sure you want to clear the log file? This cannot be undone.",
    )
  ) {
    // This function is now handled by the form submission
    return true;
  }
  return false;
}