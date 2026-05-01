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

    const queuePrefetch = (url) => {
        if (prefetchedUrls.has(url) || url.startsWith('mailto:') || url.startsWith('tel:')) return;
        if (prefetchQueue.length >= MAX_QUEUE) return;

        prefetchedUrls.add(url);
        prefetchQueue.push({ url });
        processQueue();
    };

    document.querySelectorAll('a[href]').forEach(link => {
        const url = link.href;
        if (!url) return;

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
