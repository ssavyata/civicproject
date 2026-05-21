/* issue_queue.js — client-side filtering for the issue queue page */

// Client-side keyword filter (supplements server-side filtering)
function filterTable(query) {
  const rows = document.querySelectorAll('#issueTable tbody tr');
  const q = query.toLowerCase();
  rows.forEach(function (row) {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

// Status filter — updates URL and reloads so Django can filter server-side
function filterByStatus(val) {
  const url = new URL(window.location.href);
  if (val) url.searchParams.set('status', val);
  else url.searchParams.delete('status');
  url.searchParams.delete('page');
  window.location.href = url.toString();
}

// Category filter — same pattern
function filterByCategory(val) {
  const url = new URL(window.location.href);
  if (val) url.searchParams.set('category', val);
  else url.searchParams.delete('category');
  url.searchParams.delete('page');
  window.location.href = url.toString();
}
