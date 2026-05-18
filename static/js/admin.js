function openModal(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.add('open');
}

function closeModal(id) {
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('open');
}

/* Close modal when clicking the backdrop (outside .modal-box) */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) {
        overlay.classList.remove('open');
      }
    });
  });
});

/* ---------------------------------------------------------
   All-Issues page — Assign modal
   --------------------------------------------------------- */
function openAssignModal(issueId, issueTitle) {
  var titleEl = document.getElementById('modal-issue-id');
  var form    = document.getElementById('assign-form');
  if (titleEl) titleEl.textContent = issueTitle;
  if (form)    form.action = '/issues/admin-panel/assign/' + issueId + '/';
  openModal('assign-modal');
}

function closeAssignModal() {
  closeModal('assign-modal');
}

/* ---------------------------------------------------------
   Departments page — Edit modal
   --------------------------------------------------------- */
function openEditModal(id, name, email, description) {
  var idEl   = document.getElementById('edit-dept-id');
  var nameEl = document.getElementById('edit-dept-name');
  var emailEl= document.getElementById('edit-dept-email');
  var descEl = document.getElementById('edit-dept-desc');
  if (idEl)    idEl.value    = id;
  if (nameEl)  nameEl.value  = name;
  if (emailEl) emailEl.value = email;
  if (descEl)  descEl.value  = description;
  openModal('edit-dept-modal');
}

function closeEditModal() {
  closeModal('edit-dept-modal');
}

/* ---------------------------------------------------------
   Users page — Tab switching
   --------------------------------------------------------- */
function showTab(tab) {
  /* Hide all panels */
  document.querySelectorAll('.tab-panel').forEach(function (p) {
    p.classList.remove('active');
  });

  /* Reset all tab buttons */
  document.querySelectorAll('.tab-btn').forEach(function (b) {
    b.classList.remove('active');
  });

  /* Activate the selected panel and button */
  var panel = document.getElementById('panel-' + tab);
  var btn   = document.getElementById('btn-' + tab);
  if (panel) panel.classList.add('active');
  if (btn)   btn.classList.add('active');
}

/* Initialise first tab on users page */
document.addEventListener('DOMContentLoaded', function () {
  var firstBtn = document.querySelector('.tab-btn');
  if (firstBtn) {
    var firstTab = firstBtn.id.replace('btn-', '');
    showTab(firstTab);
  }
});