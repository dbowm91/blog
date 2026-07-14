import '../css/public.css';

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
        './shared/mobile-menu.jsx',
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
        './shared/mobile-menu.jsx',
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
    ];
}

const loadModule = (path) => {
    const loader = moduleGlob[path];
    if (loader) {
        loader().then(module => {
            if (typeof module.default === 'function') { module.default(); }
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
