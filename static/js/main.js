// main.js — Client-side interactivity for the Courier Tracking System

// ── Sidebar toggle ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('sidebarToggle');

  if (toggleBtn && sidebar) {
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) sidebar.classList.add('collapsed');

    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
      updateToggleIcon();
    });
    updateToggleIcon();
  }

  function updateToggleIcon() {
    if (!toggleBtn || !sidebar) return;
    const collapsed = sidebar.classList.contains('collapsed');
    toggleBtn.innerHTML = collapsed
      ? `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>`
      : `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>`;
  }

  // ── Flash messages auto-dismiss ──────────────────────────
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      alert.style.transition = 'all .4s ease';
      setTimeout(() => alert.remove(), 400);
    }, 4000);
  });

  // ── Top-bar quick search ─────────────────────────────────
  const quickSearch = document.getElementById('quickSearchInput');
  if (quickSearch) {
    quickSearch.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const val = quickSearch.value.trim();
        if (val) window.location.href = `/track?tid=${encodeURIComponent(val)}`;
      }
    });
  }

  // ── Delete confirmation modal ────────────────────────────
  initDeleteModals();

  // ── Number counter animation for stat cards ──────────────
  animateStats();
});

// ── Delete modal ──────────────────────────────────────────
function initDeleteModals() {
  const overlay = document.getElementById('deleteModalOverlay');
  if (!overlay) return;

  const confirmBtn = document.getElementById('confirmDeleteBtn');
  const cancelBtn  = document.getElementById('cancelDeleteBtn');
  let   deleteForm = null;

  document.querySelectorAll('[data-delete-form]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const formId = btn.getAttribute('data-delete-form');
      deleteForm   = document.getElementById(formId);
      const name   = btn.getAttribute('data-parcel-name') || 'this parcel';
      const msgEl  = document.getElementById('deleteModalMsg');
      if (msgEl) msgEl.textContent = `Are you sure you want to delete parcel "${name}"? This action cannot be undone.`;
      overlay.classList.add('open');
    });
  });

  if (cancelBtn) cancelBtn.addEventListener('click', () => {
    overlay.classList.remove('open');
    deleteForm = null;
  });

  if (confirmBtn) confirmBtn.addEventListener('click', () => {
    if (deleteForm) deleteForm.submit();
  });

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.classList.remove('open');
      deleteForm = null;
    }
  });
}

// ── Stat counter animation ─────────────────────────────────
function animateStats() {
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    const target  = parseFloat(el.getAttribute('data-target'));
    const isFloat = el.getAttribute('data-float') === 'true';
    const prefix  = el.getAttribute('data-prefix') || '';
    const suffix  = el.getAttribute('data-suffix') || '';
    let   start   = 0;
    const duration = 1200;
    const startTime = performance.now();

    function update(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = start + (target - start) * ease;
      el.textContent = prefix + (isFloat
        ? current.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : Math.floor(current).toLocaleString('en-IN')
      ) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });
}

// ── Status badge helper ────────────────────────────────────
function getStatusBadgeClass(status) {
  const map = {
    'Booked':           'badge-booked',
    'Picked Up':        'badge-picked',
    'In Transit':       'badge-transit',
    'Out for Delivery': 'badge-out',
    'Delivered':        'badge-delivered',
    'Failed Delivery':  'badge-failed',
    'Returned':         'badge-returned',
  };
  return map[status] || 'badge-booked';
}

// ── Timeline dot colour ─────────────────────────────────────
function getTimelineDotClass(status) {
  const map = {
    'Booked':           'blue',
    'Picked Up':        'amber',
    'In Transit':       'purple',
    'Out for Delivery': 'teal',
    'Delivered':        'green',
    'Failed Delivery':  'red',
    'Returned':         'grey',
  };
  return map[status] || 'blue';
}

// ── Format ISO date string nicely ─────────────────────────
function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
