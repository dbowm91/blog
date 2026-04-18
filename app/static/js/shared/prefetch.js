export function initPrefetch() {
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
}
