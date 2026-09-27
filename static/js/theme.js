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
  }

  function persistPreference(preference) {
    try {
      localStorage.setItem(STORAGE_KEY, preference);
    } catch (error) {
      // Ignore persistence failures.
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
      queueMicrotask(() => persistPreference(preference));
      return;
    }

    window.setTimeout(() => persistPreference(preference), 0);
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
    if (!select || select.dataset.themeBound === 'true') return;

    select.dataset.themeBound = 'true';
    const handleThemeChange = () => {
      setPreference(select.value);
    };

    select.addEventListener('input', handleThemeChange);
    select.addEventListener('change', handleThemeChange);
  }

  return {
    initEarly,
    initSwitcher,
    resolvePreference,
    resolveEffectiveTheme,
  };
})();

FaceAttendTheme.initEarly();
