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
]);

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
    const codeBlocks = document.querySelectorAll('pre[class*="language-"]');
    if (codeBlocks.length === 0) return;
    const prismCSS = document.createElement('link');
    prismCSS.rel = 'stylesheet';
    prismCSS.href = `/static/css/${document.documentElement.dataset.syntaxTheme || 'okaidia'}.css`;
    document.head.appendChild(prismCSS);
    const prismJS = document.createElement('script');
    prismJS.src = '/static/js/prism.min.js';
    prismJS.onload = () => {
        const langJS = document.createElement('script');
        langJS.src = '/static/js/prism-languages.js';
        document.body.appendChild(langJS);
    };
    document.body.appendChild(prismJS);
}

document.addEventListener("DOMContentLoaded", () => {
    const modules = getModulesForPath(window.location.pathname);
    modules.forEach(m => loadModule(m));
    loadPrismIfNeeded();
});
