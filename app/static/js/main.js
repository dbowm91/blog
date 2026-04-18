document.documentElement.classList.add('js');

const loadModule = (path, initFn) => {
    import(path).then(module => {
        if (initFn) initFn(module);
    }).catch(err => {
        console.error(`Failed to load module: ${path}`, err);
    });
};

document.addEventListener("DOMContentLoaded", () => {
    loadModule('./shared/utils.js', module => module.initSharedUtils());
    loadModule('./shared/dark-mode.js', module => module.initDarkMode());
    loadModule('./shared/modal.js', module => module.initModal());
    loadModule('./shared/mobile-menu.js', module => module.initMobileMenu());
    loadModule('./shared/lazy-load.js', module => module.initLazyLoad());
    loadModule('./shared/filter-select.js', module => module.initFilterSelect());
    loadModule('./shared/prefetch.js', module => module.initPrefetch());
    loadModule('./shared/nav-dropdown.js', module => module.initNavDropdown());
    loadModule('./admin/editor.js', module => module.initEditor());
    loadModule('./admin/bulk.js', module => module.initBulk());
    loadModule('./admin/shortcuts.js', module => module.initShortcuts());
    loadModule('./public/share.js', module => module.initShare());
    loadModule('./public/lightbox.js', module => module.initLightbox());
    loadModule('./public/toc.js', module => module.initToc());
    loadModule('./public/code-copy.js', module => module.initCodeCopy());
    loadModule('./public/anchor-links.js', module => module.initAnchorLinks());
    loadModule('./public/media-copy.js', module => module.initMediaCopy());
    loadModule('./upload.js', module => module.initUpload());
    loadModule('./image-preview.js', module => module.initImagePreview());
});