export function initLazyLoad() {
    if (!('loading' in HTMLImageElement.prototype)) {
        document.querySelectorAll('img:not([loading])').forEach((img) => {
            const rect = img.getBoundingClientRect();
            if (rect.top > window.innerHeight) {
                img.setAttribute('loading', 'lazy');
            }
});
    });
}

export default initLazyLoad;
