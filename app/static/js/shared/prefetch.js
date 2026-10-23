export function initPrefetch() {
    const MAX_CONCURRENT = 3;
    const MAX_QUEUE = 10;
    const prefetchedUrls = new Set();
    let activePrefetches = 0;
    const prefetchQueue = [];
    const abortControllers = new Set();

    const processQueue = () => {
        while (activePrefetches < MAX_CONCURRENT && prefetchQueue.length > 0) {
            const { url } = prefetchQueue.shift();
            activePrefetches++;
            const controller = new AbortController();
            abortControllers.add(controller);

            fetch(url, { signal: controller.signal, priority: 'low' })
                .then(() => {
                    activePrefetches--;
                    abortControllers.delete(controller);
                    processQueue();
                })
                .catch(() => {
                    activePrefetches--;
                    abortControllers.delete(controller);
                    processQueue();
                });
        }
    };

    const ALLOWED_PROTOCOLS = ['http:', 'https:'];
    const ALLOWED_SPECIAL = ['mailto:', 'tel:'];
    const DANGEROUS_PROTOCOLS = ['javascript:', 'data:', 'vbscript:', 'file:'];

    const isAllowedUrl = (url) => {
        if (ALLOWED_SPECIAL.some(p => url.startsWith(p))) return true;
        if (DANGEROUS_PROTOCOLS.some(p => url.startsWith(p))) return false;
        return ALLOWED_PROTOCOLS.some(p => url.startsWith(p));
    };

    const isSameOrigin = (url) => {
        try {
            return new URL(url, window.location.href).origin === window.location.origin;
        } catch {
            return false;
        }
    };

    const queuePrefetch = (url) => {
        if (prefetchedUrls.has(url) || !isAllowedUrl(url)) return;
        if (!isSameOrigin(url)) return;
        if (prefetchQueue.length >= MAX_QUEUE) return;

        prefetchedUrls.add(url);
        prefetchQueue.push({ url });
        processQueue();
    };

    const links = Array.from(document.querySelectorAll('a[href]')).filter((link) => {
        const url = link.href;
        return url && isAllowedUrl(url) && isSameOrigin(url);
    });

    if (links.length === 0) return;

    links.forEach(link => {
        const url = link.href;

        if (link.classList.contains('page-link')) {
            link.addEventListener('mouseenter', () => queuePrefetch(url), { passive: true });
        } else {
            link.addEventListener('mouseenter', () => {
                clearTimeout(link._prefetchTimer);
                link._prefetchTimer = setTimeout(() => queuePrefetch(url), 100);
            }, { passive: true });
        }
    });

    window.addEventListener('beforeunload', () => {
        abortControllers.forEach(controller => controller.abort());
        abortControllers.clear();
    });
}

export default initPrefetch;
