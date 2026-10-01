const FaceAttendTheme = (() => {
  const STORAGE_KEY = 'faceattend-theme';
  const VALID_PREFERENCES = ['system', 'light', 'dark'];

  let systemListenerAttached = false;

  function resolvePreference() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        return stored;
      }
    } catch (error) {
      // Ignore storage access failures and fall back to system preference.
    }

    return 'system';
  }

  function resolveEffectiveTheme(preference) {
    if (preference === 'light') return 'light';
    if (preference === 'dark') return 'dark';

    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }

    return 'dark';
  }

  function applyEffectiveTheme(effectiveTheme) {
    const root = document.documentElement;
    root.dataset.theme = effectiveTheme;
    root.style.colorScheme = effectiveTheme;
    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.content = effectiveTheme === 'dark' ? '#0e1416' : '#f4f7f7';
  }

  function persistPreference(preference) {
    try {
      localStorage.setItem(STORAGE_KEY, preference);
      return true;
    } catch (error) {
      return false;
    }
  }

  function syncThemeUi(preference) {
    const effectiveTheme = resolveEffectiveTheme(preference);
    const root = document.documentElement;

    root.dataset.themePreference = preference;
    applyEffectiveTheme(effectiveTheme);

    const select = document.getElementById('theme-select');
    const badge = document.getElementById('launch-badge');

    if (select && select.value !== preference) {
      select.value = preference;
    }
    document.querySelectorAll('[data-theme-choice]').forEach((toggle) => {
      const active = toggle.dataset.themeChoice === preference;
      toggle.setAttribute('aria-pressed', String(active));
      toggle.classList.toggle('active', active);
    });

    if (badge) {
      const badgeUrl = new URL(badge.src);
      badgeUrl.searchParams.set('theme', effectiveTheme);
      badge.src = badgeUrl.toString();
    }
  }

  function setPreference(preference) {
    if (!VALID_PREFERENCES.includes(preference)) return;

    syncThemeUi(preference);

    if (window.queueMicrotask) {
      queueMicrotask(() => { if (!persistPreference(preference)) syncThemeUi('system'); });
      return;
    }

    window.setTimeout(() => { if (!persistPreference(preference)) syncThemeUi('system'); }, 0);
  }

  function watchSystemTheme() {
    if (systemListenerAttached || !window.matchMedia) return;

    systemListenerAttached = true;

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (resolvePreference() === 'system') {
        syncThemeUi('system');
      }
    });
  }

  function initEarly() {
    const preference = resolvePreference();
    document.documentElement.dataset.themePreference = preference;
    applyEffectiveTheme(resolveEffectiveTheme(preference));
  }

  function initSwitcher() {
    watchSystemTheme();
    syncThemeUi(resolvePreference());

    const select = document.getElementById('theme-select');
    if (select && select.dataset.themeBound !== 'true') {
      select.dataset.themeBound = 'true';
      const handleThemeChange = () => setPreference(select.value);
      select.addEventListener('input', handleThemeChange);
      select.addEventListener('change', handleThemeChange);
    }

    document.querySelectorAll('[data-theme-choice]').forEach((toggle) => {
      if (toggle.dataset.themeBound === 'true') return;
      toggle.dataset.themeBound = 'true';
      toggle.addEventListener('click', () => setPreference(toggle.dataset.themeChoice));
    });
  }

  return {
    initEarly,
    initSwitcher,
    resolvePreference,
    resolveEffectiveTheme,
  };
})();

FaceAttendTheme.initEarly();
