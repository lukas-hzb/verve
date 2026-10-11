/* Apply the preference before styles load to avoid a light flash on dark pages. */
(() => {
    const storageKey = 'verve-theme';
    const choices = new Set(['light', 'dark', 'system']);
    const nextPreference = { system: 'light', light: 'dark', dark: 'system' };
    const labels = { light: 'Light Mode', dark: 'Dark Mode', system: 'System' };
    const system = window.matchMedia('(prefers-color-scheme: dark)');
    const readPreference = (fallback = 'system') => {
        try {
            const saved = localStorage.getItem(storageKey);
            return choices.has(saved) ? saved : 'system';
        } catch {
            return fallback;
        }
    };
    let preference = readPreference();

    function apply() {
        const dark = preference === 'dark' || (preference === 'system' && system.matches);
        document.documentElement.dataset.theme = dark ? 'dark' : 'light';
        document.documentElement.dataset.themePreference = preference;
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            const current = preference === 'system' ? 'System (follows device setting)' : labels[preference];
            const label = `${current}. Switch to ${labels[nextPreference[preference]]}`;
            button.setAttribute('aria-label', label);
            button.title = label;
            const text = button.querySelector('[data-theme-label]');
            if (text) text.textContent = labels[preference];
        });
    }

    function setPreference(value) {
        if (!choices.has(value)) return;
        preference = value;
        try { localStorage.setItem(storageKey, value); } catch { /* Works without storage. */ }
        apply();
    }

    apply();
    system.addEventListener('change', apply);
    window.addEventListener('storage', event => {
        if (event.key === storageKey || event.key === null) {
            preference = readPreference();
            apply();
        }
    });
    window.addEventListener('pageshow', () => { preference = readPreference(preference); apply(); });
    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            button.addEventListener('click', () => {
                setPreference(nextPreference[preference]);
            });
        });
        apply();
    });
})();
