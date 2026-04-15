document.documentElement.classList.add('js');
document.addEventListener("DOMContentLoaded", () => {
    import('./shared/utils.js').then(module => module.initSharedUtils());
    import('./shared/dark-mode.js').then(module => module.initDarkMode());
    import('./shared/modal.js').then(module => module.initModal());
    import('./admin/editor.js').then(module => module.initEditor());
    import('./admin/bulk.js').then(module => module.initBulk());
    import('./admin/shortcuts.js').then(module => module.initShortcuts());
    import('./public/share.js').then(module => module.initShare());
    import('./public/lightbox.js').then(module => module.initLightbox());
    import('./public/toc.js').then(module => module.initToc());
    import('./public/code-copy.js').then(module => module.initCodeCopy());
    import('./upload.js').then(module => module.initUpload());
    import('./image-preview.js').then(module => module.initImagePreview());

    // --- Mobile hamburger menu ---
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
    }

    // --- Anchor links for headings ---
    const usedIds = new Set();
    document.querySelectorAll('.prose h1, .prose h2, .prose h3, .prose h4').forEach((heading) => {
        if (!heading.id) {
            const text = heading.textContent;
            let id = text.toLowerCase()
                .replace(/[^\w\s-]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-')
                .trim();

            if (!id) {
                const headingType = heading.tagName.toLowerCase();
                let counter = 1;
                id = `${headingType}-${counter}`;
                while (usedIds.has(id)) {
                    counter++;
                    id = `${headingType}-${counter}`;
                }
            } else {
                let finalId = id;
                let counter = 1;
                while (usedIds.has(finalId)) {
                    finalId = `${id}-${counter}`;
                    counter++;
                }
                id = finalId;
            }
            usedIds.add(id);
            heading.id = id;
        } else {
            usedIds.add(heading.id);
        }

        const wrapper = document.createElement('span');
        wrapper.className = 'heading-anchor';

        const anchor = document.createElement('a');
        anchor.className = 'anchor-link';
        anchor.href = `#${heading.id}`;
        anchor.innerHTML = '#';
        anchor.setAttribute('aria-label', 'Link to this section');
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const fullUrl = window.location.origin + window.location.pathname + anchor.href;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(fullUrl).then(() => {
                    const toast = document.createElement('div');
                    toast.className = 'toast';
                    toast.textContent = 'Link copied!';
                    document.body.appendChild(toast);
                    requestAnimationFrame(() => toast.classList.add('visible'));
                    setTimeout(() => {
                        toast.classList.remove('visible');
                        setTimeout(() => toast.remove(), 300);
                    }, 2000);
                });
            }
        });

        while (heading.firstChild) {
            wrapper.appendChild(heading.firstChild);
        }

        heading.appendChild(wrapper);
        heading.appendChild(anchor);
    });

    // --- Lazy loading for images ---
    if (!('loading' in HTMLImageElement.prototype)) {
        document.querySelectorAll('img:not([loading])').forEach((img) => {
            const rect = img.getBoundingClientRect();
            if (rect.top > window.innerHeight * 3) {
                img.setAttribute('loading', 'lazy');
            }
        });
    }

    document.querySelectorAll('img[loading="lazy"]').forEach((img) => {
        if (img.complete) {
            img.classList.add('loaded');
        } else {
            img.addEventListener('load', () => img.classList.add('loaded'));
            img.addEventListener('error', () => img.classList.add('loaded'));
        }
    });

    // --- Media Copy URL ---
    document.querySelectorAll('.media-copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const url = btn.dataset.url;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
                }).catch(() => {
                    btn.textContent = 'Failed';
                    setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
                });
            } else {
                btn.textContent = 'Failed';
                setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
            }
        });
    });

    // --- Dashboard filter select auto-submit ---
    document.querySelectorAll('.filter-select').forEach(select => {
        select.addEventListener('change', () => {
            const form = select.form;
            form.classList.add('loading');
            form.submit();
        });
    });

    // --- Analytics select auto-submit ---
    document.querySelectorAll('[data-auto-submit]').forEach(select => {
        select.addEventListener('change', () => {
            const allowedDays = ['7', '14', '30', '90', '180', '365'];
            if (allowedDays.includes(select.value)) {
                select.closest('form').classList.add('loading');
                window.location.href = '/admin/analytics?days=' + select.value;
            }
        });
    });

    // --- Prefetch likely next pages ---
    const prefetchedUrls = new Set();
    let prefetchTimer = null;

    document.querySelectorAll('a[href]').forEach(link => {
        const url = link.href;
        if (!url || prefetchedUrls.has(url) || url.startsWith('mailto:') || url.startsWith('tel:')) return;

        if (link.classList.contains('page-link')) {
            link.addEventListener('mouseenter', () => {
                if (!prefetchedUrls.has(url)) {
                    prefetchedUrls.add(url);
                    const prefetch = document.createElement('link');
                    prefetch.rel = 'prefetch';
                    prefetch.href = url;
                    document.head.appendChild(prefetch);
                }
            }, { passive: true });
        } else {
            link.addEventListener('mouseenter', () => {
                clearTimeout(prefetchTimer);
                prefetchTimer = setTimeout(() => {
                    if (prefetchedUrls.has(url)) return;
                    prefetchedUrls.add(url);
                    const prefetch = document.createElement('link');
                    prefetch.rel = 'prefetch';
                    prefetch.href = url;
                    document.head.appendChild(prefetch);
                }, 100);
            }, { passive: true });
        }
    });

    window.addEventListener('beforeunload', () => {
        clearTimeout(prefetchTimer);
    });

    // --- Nav dropdown toggle ---
    document.querySelectorAll('.nav-dropdown-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = btn.closest('.nav-dropdown');
            const isOpen = dropdown.classList.contains('open');
            document.querySelectorAll('.nav-dropdown.open').forEach(d => d.classList.remove('open'));
            if (!isOpen) {
                dropdown.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
            } else {
                btn.setAttribute('aria-expanded', 'false');
            }
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.nav-dropdown.open').forEach(d => {
            d.classList.remove('open');
            d.querySelector('.nav-dropdown-toggle').setAttribute('aria-expanded', 'false');
        });
    });
});