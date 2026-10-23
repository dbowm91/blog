document.documentElement.classList.add('js');

// Use Vite-compatible import.meta.glob() for static analysis
const moduleGlob = import.meta.glob([
    './shared/utils.js',
    './shared/modal.js',
    './shared/nav-dropdown.js',
    './shared/filter-select.js',
    './shared/toast.js',
    './admin/shortcuts.js',
    './admin/bulk.js',
    './admin/editor.js',
    './image-preview.js',
    './upload.js',
    './shared/color-scheme.js',
    './shared/mobile-menu.jsx',
    './shared/lazy-load.js',
    './shared/prefetch.js',
    './public/share.js',
    './public/lightbox.js',
    './public/toc.js',
    './public/code-copy.js',
    './public/anchor-links.js',
    './public/media-copy.js',
    './public/search.js',
]);

const ROUTE_MODULES = {
    '/admin/new': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './shared/color-scheme.js',
        './shared/mobile-menu.jsx',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
        './image-preview.js',
    ],
    '/admin/edit': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './shared/color-scheme.js',
        './shared/mobile-menu.jsx',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
        './image-preview.js',
    ],
    '/admin/pages/new': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './shared/color-scheme.js',
        './shared/mobile-menu.jsx',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
    ],
    '/admin/pages/edit': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './shared/color-scheme.js',
        './shared/mobile-menu.jsx',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './admin/editor.js',
    ],
    '/admin/media': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './shared/color-scheme.js',
        './shared/mobile-menu.jsx',
        './admin/shortcuts.js',
        './admin/bulk.js',
        './public/media-copy.js',
        './upload.js',
        './image-preview.js',
    ],
    '/admin/': [
        './shared/utils.js',
        './shared/modal.js',
        './shared/nav-dropdown.js',
        './shared/filter-select.js',
        './shared/toast.js',
        './shared/color-scheme.js',
        './shared/mobile-menu.jsx',
        './admin/shortcuts.js',
        './admin/bulk.js',
    ],
};

const PUBLIC_MODULES = [
    './shared/utils.js',
    './shared/toast.js',
    './shared/color-scheme.js',
    './shared/mobile-menu.jsx',
    './shared/lazy-load.js',
    './shared/prefetch.js',
    './public/share.js',
    './public/lightbox.js',
    './public/toc.js',
    './public/code-copy.js',
    './public/anchor-links.js',
    './public/search.js',
];

// Longest prefix wins, and a route only matches on a path-segment boundary,
// so '/admin/newsletter/preview' cannot be captured by '/admin/new'.
const SORTED_ROUTE_MODULES = Object.entries(ROUTE_MODULES)
    .sort((a, b) => b[0].length - a[0].length);

function matchesRoute(path, route) {
    if (route.endsWith('/')) return path.startsWith(route);
    return path === route || path.startsWith(`${route}/`);
}

export function getModulesForPath(path) {
    for (const [route, modules] of SORTED_ROUTE_MODULES) {
        if (matchesRoute(path, route)) return modules;
    }
    return PUBLIC_MODULES;
}

const MODULE_INIT_OPTIONS = {
    './shared/color-scheme.js': () => ({
        defaultScheme: document.documentElement.dataset.defaultScheme || 'system',
    }),
};

const loadModule = (path) => {
    const loader = moduleGlob[path];
    if (loader) {
        loader().then(module => {
            if (typeof module.default === 'function') {
                const options = MODULE_INIT_OPTIONS[path] ? MODULE_INIT_OPTIONS[path]() : undefined;
                if (options) {
                    module.default(options);
                } else {
                    module.default();
                }
            }
        }).catch(err => {
            console.error(`Failed to load module: ${path}`, err);
        });
    } else {
        console.warn(`Module not found in glob: ${path}`);
    }
};
function loadPrismIfNeeded() {
    if (window.Prism) return;
    const codeBlocks = document.querySelectorAll('pre[class*="language-"]');
    if (codeBlocks.length === 0) return;
    const prismCSS = document.createElement('link');
    prismCSS.rel = 'stylesheet';
    prismCSS.href = document.documentElement.dataset.prismCssUrl;
    document.head.appendChild(prismCSS);
    const prismJS = document.createElement('script');
    prismJS.src = document.documentElement.dataset.prismJsUrl;
    prismJS.onload = () => {
        const langJS = document.createElement('script');
        langJS.src = document.documentElement.dataset.prismLangsUrl;
        document.body.appendChild(langJS);
    };
    document.body.appendChild(prismJS);
}

document.addEventListener("DOMContentLoaded", () => {
    const modules = getModulesForPath(window.location.pathname);
    modules.forEach(m => loadModule(m));
    loadPrismIfNeeded();
});
