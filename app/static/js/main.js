document.documentElement.classList.add('js');

const loadModule = (path) => {
    import(path).then(module => {
        if (typeof module.default === 'function') { module.default(); }
    }).catch(err => {
        console.error(`Failed to load module: ${path}`, err);
    });
};

const ROUTE_MODULES = {
    '/admin/posts': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
        './image-preview.js',
    ],
    '/admin/media': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './upload.js',
        './image-preview.js',
    ],
    '/admin/': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './admin/shortcuts.js',
        './admin/bulk.js',
    ],
};

function getModulesForPath(path) {
    for (const [route, modules] of Object.entries(ROUTE_MODULES)) {
        if (path.startsWith(route)) return modules;
    }
    return [
        './shared/utils.js',
        './shared/toast.js',
        './shared/dark-mode.js',
        './shared/mobile-menu.js',
        './shared/lazy-load.js',
        './shared/prefetch.js',
        './public/share.js',
        './public/lightbox.js',
        './public/toc.js',
        './public/code-copy.js',
        './public/anchor-links.js',
        './public/media-copy.js',
        './public/search.js',
    ];
}

document.addEventListener("DOMContentLoaded", () => {
    const modules = getModulesForPath(window.location.pathname);
    modules.forEach(m => loadModule(m));
});
