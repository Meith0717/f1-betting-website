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

  // Race weekend date range, rendered in the browser's timezone
  // (same formatting as the server-side date_range filter)
  document.querySelectorAll(".local-date-range").forEach(function (el) {
    const start = new Date(el.dataset.startIso);
    const end = new Date(el.dataset.endIso);
    if (isNaN(start.getTime()) || isNaN(end.getTime())) return;
    const day = (d) => String(d.getDate()).padStart(2, "0") + "." + String(d.getMonth() + 1).padStart(2, "0");
    const full = (d) => day(d) + "." + d.getFullYear();
    if (start.getFullYear() === end.getFullYear() && start.getMonth() === end.getMonth()) {
      el.textContent = day(start) + " - " + full(end);
    } else {
      el.textContent = full(start) + " - " + full(end);
    }
  });
});
