function faceattendApiBase() {
  if (typeof location === 'undefined') return 'https://faceattend.app';
  const host = location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host === '[::1]') {
    return `${location.protocol}//${location.host}`;
  }
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

  const clearFieldErrors = () => {
    form.querySelectorAll('[aria-invalid="true"]').forEach((field) => field.removeAttribute('aria-invalid'));
    const consentWrap = document.querySelector('.privacy-consent');
    if (consentWrap) consentWrap.classList.remove('invalid');
  };

  form.querySelectorAll('input').forEach((field) => {
    field.addEventListener('input', () => {
      if (field.getAttribute('aria-invalid') === 'true') {
        field.removeAttribute('aria-invalid');
      }
      const consentWrap = document.querySelector('.privacy-consent');
      if (consentWrap && field.type !== 'checkbox') {
        const areAnyInvalid = form.querySelectorAll('[aria-invalid="true"]').length > 0;
        if (!areAnyInvalid && consentWrap.classList.contains('invalid')) {
          consentWrap.classList.remove('invalid');
        }
      }
    });
    field.addEventListener('change', () => {
      clearFieldErrors();
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn    = document.getElementById('submit-btn');
    const status = document.getElementById('status-msg');

    const universityName = document.getElementById('university_name').value.trim();
    const adminFullName  = document.getElementById('admin_full_name').value.trim();
    const adminEmail     = document.getElementById('admin_email').value.trim();
    const phone          = document.getElementById('phone').value.trim();
    const privacyConsent = document.getElementById('privacy-consent');

    btn.disabled         = true;
    btn.textContent      = 'Creating account…';
    status.style.display = 'none';
    status.className     = 'status-msg';
    const consentBox = document.querySelector('.privacy-consent');
    if (consentBox) consentBox.classList.remove('invalid');

    const requiredFields = [...form.querySelectorAll('input[required]')];
    const missingField = requiredFields.find(field => {
      if (field.type === 'checkbox') return !field.checked;
      return !field.value.trim();
    });

    if (!universityName || !adminFullName || !adminEmail || !phone || !privacyConsent.checked) {
      clearFieldErrors();
      if (missingField) {
        missingField.setAttribute('aria-invalid', 'true');
        if (missingField.type === 'checkbox') {
          const consentWrap = missingField.closest('.privacy-consent');
          if (consentWrap) consentWrap.classList.add('invalid');
          missingField.focus();
        } else {
          missingField.focus();
        }
      }
      status.className = 'status-msg error';
      status.textContent = !privacyConsent.checked
        ? 'Please confirm the privacy and consent notice before creating your institution account.'
        : 'Complete all required fields before submitting.';
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

  const setOpenState = (isOpen) => {
    links.classList.toggle('open', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
    toggle.setAttribute('aria-label', isOpen ? 'Close menu' : 'Open menu');
  };

  const closeMenu = (returnFocus = false) => {
    setOpenState(false);
    if (returnFocus) toggle.focus();
  };

  const getFocusable = () => {
    return [...links.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])')]
      .filter((el) => !el.hasAttribute('hidden'));
  };

  toggle.addEventListener('click', () => {
    const isOpen = links.classList.contains('open');
    setOpenState(!isOpen);
  });

  links.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      closeMenu(false);
    });
  });

  document.addEventListener('click', (event) => {
    const clickedInsideToggle = toggle.contains(event.target);
    const clickedInsideLinks = links.contains(event.target);
    if (!clickedInsideToggle && !clickedInsideLinks && links.classList.contains('open')) {
      closeMenu(false);
    }
  });

  document.addEventListener('keydown', (event) => {
    if (!links.classList.contains('open')) return;

    if (event.key === 'Escape') {
      closeMenu(true);
      return;
    }

    if (event.key !== 'Tab') return;

    const focusable = getFocusable();
    if (!focusable.length) {
      event.preventDefault();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
      return;
    }

    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
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