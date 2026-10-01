function faceattendApiBase() {
  if (typeof location === 'undefined') return 'https://faceattend.app';
  const host = location.hostname;
  if (host === 'faceattend.app' || host.endsWith('.faceattend.app')) {
    return `${location.protocol}//${location.host}`;
  }
  return 'https://faceattend.app';
}

const API_URL = faceattendApiBase();

// ── Signup form ──
function initSignupForm() {
  const form = document.getElementById('signup-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn    = document.getElementById('submit-btn');
    const status = document.getElementById('status-msg');

    const universityName = document.getElementById('university_name').value.trim();
    const adminFullName  = document.getElementById('admin_full_name').value.trim();
    const adminEmail     = document.getElementById('admin_email').value.trim();
    const phone          = document.getElementById('phone').value.trim();

    btn.disabled         = true;
    btn.textContent      = 'Creating account…';
    status.style.display = 'none';
    status.className     = 'status-msg';
    if (!universityName || !adminFullName || !adminEmail || !phone) {
      const firstInvalid = [...form.querySelectorAll('input[required]')].find(field => !field.value.trim());
      if (firstInvalid) { firstInvalid.setAttribute('aria-invalid', 'true'); firstInvalid.focus(); }
      status.className = 'status-msg error';
      status.textContent = 'Complete all required fields before submitting.';
      status.style.display = 'block';
      btn.disabled = false;
      btn.textContent = 'Create Institution Account';
      return;
    }

    const formData = new FormData();
    formData.append('university_name', universityName);
    formData.append('admin_full_name', adminFullName);
    formData.append('admin_email',     adminEmail);
    formData.append('phone',           phone);

    try {
      const resp = await fetch(`${API_URL}/register-institution`, {
        method: 'POST',
        body: formData,
      });
      const data = await resp.json();

      if (resp.ok && data.success) {
        status.className     = 'status-msg success';
        status.style.display = 'block';
        status.innerHTML     = `
          <strong>Welcome to FaceAttend!</strong><br><br>
          Your institution <strong>${data.institution_name || universityName}</strong> has been created.<br>
          Institution ID: <strong>${data.institution_id}</strong><br><br>
          Check <strong>${adminEmail}</strong> to set your password and start your ${data.trial_days || 30}-day free trial.<br><br>
          <span style="color:var(--cyan);font-size:0.82rem;">
            You are the <strong>Central Administrator</strong>. After logging in, create your departments and invite department admins to get started.
          </span>
        `;
        status.focus();
        form.reset();
        btn.textContent = 'Account Created ✓';

        // Clear POST from history after successful submission
        if (window.history.replaceState) {
          window.history.replaceState(null, null, window.location.href);
        }
      } else {
        throw new Error(data.detail || 'Registration failed. Please try again.');
      }
    } catch (err) {
      status.className     = 'status-msg error';
      status.style.display = 'block';
      status.textContent   = err.message;
      status.focus();
      btn.disabled         = false;
      btn.textContent      = 'Create Institution Account';
    }
  });
}

// ── Mobile nav toggle ──
function initMobileNav() {
  const toggle = document.getElementById('nav-toggle');
  const links  = document.querySelector('.nav-links');
  if (!toggle || !links) return;

  toggle.addEventListener('click', () => {
    links.classList.toggle('open');
    const isOpen = links.classList.contains('open');
    toggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  links.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open menu');
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && links.classList.contains('open')) {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open menu');
      toggle.focus();
    }
  });
}

// ── Scroll hint fade-out ──
function initScrollHint() {
  const hint = document.querySelector('.hero-scroll-hint');
  if (!hint) return;

  window.addEventListener('scroll', () => {
    const opacity = Math.max(0, 1 - window.scrollY / 120);
    hint.style.opacity = opacity;
  }, { passive: true });
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  // Prevent form resubmission dialog on refresh
  if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
  }

  FaceAttendTheme.initSwitcher();
  initSignupForm();
  initMobileNav();
  initScrollHint();
});