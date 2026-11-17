// Render session times in the browser's local timezone.
// Elements with class "local-time" carry a UTC ISO string in data-utc-iso;
// the server-rendered content is kept as a no-JS fallback and overwritten here.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".local-time[data-utc-iso]").forEach(function (el) {
    const iso = el.dataset.utcIso;
    if (!iso) return;
    const date = new Date(iso);
    if (isNaN(date.getTime())) return;
    const hh = String(date.getHours()).padStart(2, "0");
    const mm = String(date.getMinutes()).padStart(2, "0");
    el.textContent = hh + ":" + mm;
  });

  // Same for the session date — a session late in the UTC day can fall on
  // the next calendar day in the browser's timezone.
  document.querySelectorAll(".local-date[data-utc-iso]").forEach(function (el) {
    const iso = el.dataset.utcIso;
    if (!iso) return;
    const date = new Date(iso);
    if (isNaN(date.getTime())) return;
    const dd = String(date.getDate()).padStart(2, "0");
    const mm = String(date.getMonth() + 1).padStart(2, "0");
    el.textContent = dd + "." + mm;
  });
});
