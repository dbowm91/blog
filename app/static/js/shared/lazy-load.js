export function initLazyLoad() {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');

    // The `.loaded` class is the contract with the CSS fade-in rule, so it must be
    // applied on every browser (including ones with native lazy loading).
    lazyImages.forEach(img => {
        const markLoaded = () => img.classList.add('loaded');
        if (img.complete) {
            markLoaded();
        } else {
            img.addEventListener('load', markLoaded, { once: true });
            img.addEventListener('error', markLoaded, { once: true });
        }
    });

    // Native lazy loading support
    if ('loading' in HTMLImageElement.prototype) {
        return;
    }

    // IntersectionObserver polyfill for lazy loading
    if (!('IntersectionObserver' in window)) {
        // No IntersectionObserver support: load all images immediately
        lazyImages.forEach(img => {
            img.src = img.dataset.src || img.src;
        });
        return;
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }
                img.removeAttribute('loading');
                img.addEventListener('load', () => img.classList.add('loaded'), { once: true });
                observer.unobserve(img);
            }
        });
    }, { rootMargin: '200px 0px' });

    lazyImages.forEach(img => observer.observe(img));
}

export default initLazyLoad;
