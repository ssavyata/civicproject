/* base.js — shared UI behaviour across all officer pages */

// Toggle notification panel
function toggleNotif() {
  const panel = document.getElementById('notifPanel');
  if (panel) {
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
  }
}

// Close notification panel when clicking outside
document.addEventListener('click', function (e) {
  const panel = document.getElementById('notifPanel');
  const btn   = document.getElementById('notifBtn');
  if (panel && btn && !btn.contains(e.target) && !panel.contains(e.target)) {
    panel.style.display = 'none';
  }
});

// Generic password visibility toggle
// Usage: <span … onclick="togglePassword(this)">visibility</span>
function togglePassword(iconEl) {
  const wrapper = iconEl.closest('.input-wrapper');
  const input   = wrapper ? wrapper.querySelector('input') : null;
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    iconEl.textContent = 'visibility_off';
  } else {
    input.type = 'password';
    iconEl.textContent = 'visibility';
  }
}
