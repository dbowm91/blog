const OPEN_CLASS = 'open';
const READY_ATTRIBUTE = 'data-nav-dropdown-ready';
const NAV_CLOSED_EVENT = 'devlog:nav-closed';

function closeDropdown(dropdown) {
    dropdown.classList.remove(OPEN_CLASS);
    const toggle = dropdown.querySelector('.nav-dropdown-toggle');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
}

function openDropdown(dropdown) {
    dropdown.classList.add(OPEN_CLASS);
    const toggle = dropdown.querySelector('.nav-dropdown-toggle');
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
}

function menuItems(dropdown) {
    const menu = dropdown.querySelector('.nav-dropdown-menu');
    return menu ? Array.from(menu.querySelectorAll('a')) : [];
}

export function initNavDropdown() {
    const root = document.documentElement;
    if (root.getAttribute(READY_ATTRIBUTE) === 'true') return;

    const toggles = Array.from(document.querySelectorAll('.nav-dropdown-toggle'));
    if (!toggles.length) return;

    root.setAttribute(READY_ATTRIBUTE, 'true');

    const dropdowns = toggles
        .map((btn) => btn.closest('.nav-dropdown'))
        .filter((dropdown) => Boolean(dropdown));

    const closeAll = (except) => {
        dropdowns.forEach((dropdown) => {
            if (dropdown !== except) closeDropdown(dropdown);
        });
    };

    toggles.forEach((btn) => {
        const dropdown = btn.closest('.nav-dropdown');
        if (!dropdown) return;

        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = dropdown.classList.contains(OPEN_CLASS);
            closeAll(null);
            if (isOpen) {
                closeDropdown(dropdown);
            } else {
                openDropdown(dropdown);
            }
        });

        btn.addEventListener('keydown', (e) => {
            if (e.key !== 'ArrowDown') return;
            e.preventDefault();
            closeAll(null);
            openDropdown(dropdown);
            const items = menuItems(dropdown);
            if (items.length) items[0].focus();
        });
    });

    document.addEventListener('click', () => closeAll(null));

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        const open = dropdowns.find((dropdown) => dropdown.classList.contains(OPEN_CLASS));
        if (!open) return;
        closeDropdown(open);
        const toggle = open.querySelector('.nav-dropdown-toggle');
        if (toggle) toggle.focus();
    });

    // The mobile menu owns the panel, so closing it must not leave a
    // dropdown hanging open behind it.
    document.addEventListener(NAV_CLOSED_EVENT, () => closeAll(null));
}

export default initNavDropdown;
