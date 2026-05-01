export function initLazyLoad() {
    // Native lazy loading support
    if ('loading' in HTMLImageElement.prototype) {
        return;
    }

    // IntersectionObserver polyfill for lazy loading
    if (!('IntersectionObserver' in window)) {
        // No IntersectionObserver support: load all images immediately
        document.querySelectorAll('img[loading="lazy"]').forEach(img => {
            img.src = img.dataset.src || img.src;
        });
        return;
    }

    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }
                img.removeAttribute('loading');
                observer.unobserve(img);
            }
        });
    }, { rootMargin: '200px 0px' });

    lazyImages.forEach(img => observer.observe(img));
}

export default initLazyLoad;
