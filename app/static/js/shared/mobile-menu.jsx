export function initMobileMenu() {
    const mobileMenuToggle = document.createElement('button');
    const menuIcon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>';
    const closeIcon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>';
    mobileMenuToggle.className = 'mobile-menu-toggle';
    mobileMenuToggle.type = 'button';
    mobileMenuToggle.innerHTML = `<span class="mobile-menu-icon-open">${menuIcon}</span><span class="mobile-menu-icon-close">${closeIcon}</span>`;
    mobileMenuToggle.setAttribute('aria-label', 'Open navigation menu');
    mobileMenuToggle.setAttribute('aria-expanded', 'false');

    const navContainer = document.querySelector('.nav-container');
    const navLinks = document.querySelector('.nav-links');

    if (navContainer && navLinks) {
        if (!navLinks.id) navLinks.id = 'nav-links';
        mobileMenuToggle.setAttribute('aria-controls', navLinks.id);
        navContainer.appendChild(mobileMenuToggle);

        // The scrim that dims the page behind the open menu. It is a
        // body-level element rather than a pseudo-element of the menu: the
        // panel sits inside the navbar stacking context, so a scrim declared
        // on the panel would paint over the menu links, and a tap on it
        // would count as a click inside the menu.
        const backdrop = document.createElement('div');
        backdrop.className = 'mobile-menu-backdrop';
        document.body.appendChild(backdrop);

        const setMenuOpen = (isOpen) => {
            navLinks.classList.toggle('open', isOpen);
            backdrop.classList.toggle('open', isOpen);
            mobileMenuToggle.setAttribute('aria-expanded', isOpen.toString());
            mobileMenuToggle.setAttribute('aria-label', isOpen ? 'Close navigation menu' : 'Open navigation menu');
        };

        mobileMenuToggle.addEventListener('click', () => {
            setMenuOpen(!navLinks.classList.contains('open'));
        });

        backdrop.addEventListener('click', () => {
            setMenuOpen(false);
        });

        document.addEventListener('click', (e) => {
            if (!mobileMenuToggle.contains(e.target) && !navLinks.contains(e.target)) {
                setMenuOpen(false);
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                setMenuOpen(false);
            }
        });
    }
}

export default initMobileMenu;
