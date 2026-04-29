export function initMobileMenu() {
    const mobileMenuToggle = document.createElement('button');
    mobileMenuToggle.className = 'mobile-menu-toggle';
    mobileMenuToggle.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>';
    mobileMenuToggle.setAttribute('aria-label', 'Toggle navigation menu');
    mobileMenuToggle.setAttribute('aria-expanded', 'false');

    const navContainer = document.querySelector('.nav-container');
    const navLinks = document.querySelector('.nav-links');

    if (navContainer && navLinks) {
        navContainer.appendChild(mobileMenuToggle);

        mobileMenuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
            const isOpen = navLinks.classList.contains('open');
            mobileMenuToggle.setAttribute('aria-expanded', isOpen.toString());
            mobileMenuToggle.innerHTML = isOpen
                ? '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>'
                : '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>';
        });

        document.addEventListener('click', (e) => {
            const hamburger = document.querySelector('.mobile-menu-toggle');
            const nav = document.querySelector('.nav-links');
            if (hamburger && nav && !hamburger.contains(e.target) && !nav.contains(e.target)) {
                hamburger.setAttribute('aria-expanded', 'false');
                nav.classList.remove('open');
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const hamburger = document.querySelector('.mobile-menu-toggle');
                const nav = document.querySelector('.nav-links');
                if (hamburger && nav) {
                    hamburger.setAttribute('aria-expanded', 'false');
                    nav.classList.remove('open');
                }
            }
});
    });
}

export default initMobileMenu;
