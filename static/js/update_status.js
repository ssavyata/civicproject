/* update_status.js — photo lightbox and rejection guard for update status page */

// Open an evidence photo in a lightbox overlay
function openPhoto(url) {
  const overlay = document.createElement('div');
  overlay.style.cssText = [
    'position:fixed',
    'inset:0',
    'background:rgba(0,0,0,0.85)',
    'z-index:9999',
    'display:flex',
    'align-items:center',
    'justify-content:center',
    'cursor:zoom-out',
  ].join(';');

  const img = document.createElement('img');
  img.src = url;
  img.style.cssText = [
    'max-width:90vw',
    'max-height:90vh',
    'border-radius:8px',
    'box-shadow:0 25px 50px rgba(0,0,0,0.5)',
  ].join(';');

  overlay.appendChild(img);
  overlay.addEventListener('click', function () {
    document.body.removeChild(overlay);
  });
  document.body.appendChild(overlay);
}

// Require remarks and confirm before submitting a Rejected status
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form[data-status-form]');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    const status  = form.querySelector('[name="status"]').value;
    const remarks = form.querySelector('[name="remarks"]').value.trim();

    if (status === 'rejected') {
      if (!remarks) {
        e.preventDefault();
        alert('Please provide a reason in the Remarks field when rejecting an issue.');
        return;
      }
      if (!confirm('Are you sure you want to reject this issue?')) {
        e.preventDefault();
      }
    }
  });
});
