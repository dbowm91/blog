const STORAGE_KEY = 'blog-color-scheme';
const VALID_SCHEMES = ['system', 'dark', 'light'];
const SCHEME_ATTR = 'data-color-scheme';

function getConfiguredDefault() {
    const configured = document.documentElement?.dataset?.defaultScheme;
    return VALID_SCHEMES.includes(configured) ? configured : 'system';
}

function getStoredScheme(defaultScheme) {
    const fallback = VALID_SCHEMES.includes(defaultScheme) ? defaultScheme : getConfiguredDefault();
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return VALID_SCHEMES.includes(stored) ? stored : fallback;
    } catch {
        return fallback;
    }
}

function resolveEffectiveScheme(stored) {
    if (stored === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return stored;
}

function applyScheme(scheme) {
    document.documentElement.setAttribute(SCHEME_ATTR, scheme);
}

function getSchemeLabel(scheme) {
    const labels = {
        system: 'System (follows OS)',
        dark: 'Dark',
        light: 'Light'
    };
    return labels[scheme] || 'System';
}

function getSchemeIcon(scheme) {
    if (scheme === 'system') {
        return '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>';
    }
    if (scheme === 'dark') {
        return '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/></svg>';
}

function cycleScheme(current) {
    const idx = VALID_SCHEMES.indexOf(current);
    return VALID_SCHEMES[(idx + 1) % VALID_SCHEMES.length];
}

export function initColorScheme(options) {
    const defaultScheme = (options && options.defaultScheme) || getConfiguredDefault();
    const stored = getStoredScheme(defaultScheme);
    const effective = resolveEffectiveScheme(stored);

    applyScheme(effective);

    const toggle = document.createElement('button');
    toggle.className = 'theme-toggle';
    toggle.type = 'button';

    // The accessible name describes the scheme in effect; the icon shows the
    // stored preference (so "system" stays distinguishable from a fixed mode).
    // The control is tri-state, so aria-pressed carries the binary part of the
    // state: pressed means an explicit choice is in effect rather than "system".
    const describe = (preference) => {
        const current = resolveEffectiveScheme(preference);
        const label = `Color scheme: ${getSchemeLabel(current)}`;
        toggle.setAttribute('aria-label', label);
        toggle.setAttribute('aria-pressed', preference === 'system' ? 'false' : 'true');
        toggle.title = label;
        toggle.innerHTML = getSchemeIcon(preference);
    };

    describe(stored);

    toggle.addEventListener('click', () => {
        const current = getStoredScheme(defaultScheme);
        const next = cycleScheme(current);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch {
            // storage unavailable — apply without persisting
        }
        applyScheme(resolveEffectiveScheme(next));
        describe(next);
    });

    // The toggle must stay reachable on small viewports, where .nav-links is hidden.
    const host = document.querySelector('.nav-actions') || document.querySelector('.nav-container');
    if (host) {
        host.appendChild(toggle);
    }

    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (getStoredScheme(defaultScheme) === 'system') {
            applyScheme(resolveEffectiveScheme('system'));
            describe('system');
        }
    });
}

export function getInitialColorScheme(defaultScheme) {
    return resolveEffectiveScheme(getStoredScheme(defaultScheme));
}

export function setColorScheme(scheme) {
    if (VALID_SCHEMES.includes(scheme)) {
        try {
            localStorage.setItem(STORAGE_KEY, scheme);
        } catch {
            // storage unavailable — apply without persisting
        }
        applyScheme(resolveEffectiveScheme(scheme));
    }
}

export default initColorScheme;
