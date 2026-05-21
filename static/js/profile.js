/* profile.js — password strength meter and toggle for the profile page */

// Toggle password field visibility (delegates to base.js togglePassword)
function togglePw(iconEl) {
  togglePassword(iconEl);
}

// Password strength meter
function checkStrength(val) {
  const bar  = document.getElementById('pwBar');
  const hint = document.getElementById('pwHint');
  if (!bar || !hint) return;

  let score = 0;
  if (val.length >= 8)          score++;
  if (/[A-Z]/.test(val))        score++;
  if (/[0-9]/.test(val))        score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;

  const levels = [
    { pct: '0%',   color: '',        label: 'Enter a new password' },
    { pct: '25%',  color: '#ef4444', label: 'Weak' },
    { pct: '50%',  color: '#f59e0b', label: 'Fair' },
    { pct: '75%',  color: '#3b82f6', label: 'Good' },
    { pct: '100%', color: '#10b981', label: 'Strong' },
  ];
  const lvl = levels[score];
  bar.style.width      = lvl.pct;
  bar.style.background = lvl.color;
  hint.textContent     = lvl.label;
  hint.style.color     = lvl.color || '#64748b';
}
