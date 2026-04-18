import { focusableSelectors } from '../shared/utils.js';

export function initShortcuts() {
    if (!document.body.classList.contains('admin-body')) return;

    // --- Vim-style keyboard navigation ---
    let vimKey = null;
    let vimTimer = null;

    document.addEventListener('keydown', (e) => {
        // Clear vim state on any non-g key (unless modifier is held)
        if (vimKey && !e.ctrlKey && !e.metaKey && !e.altKey && e.key.length === 1) {
            if (vimKey === 'g' && e.key !== 'd' && e.key !== 'p' && e.key !== 's' && e.key !== 't') {
                vimKey = null;
                clearTimeout(vimTimer);
            }
        }

        // g key: prime for vim-style nav
        if (!vimKey && e.key === 'g' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            const tag = e.target.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA' && !e.target.isContentEditable) {
                vimKey = 'g';
                clearTimeout(vimTimer);
                vimTimer = setTimeout(() => { vimKey = null; }, 500);
            }
        }

        // gd = Dashboard, gp = Posts, gs = Subscribers, gt = Tags
        if (vimKey === 'g') {
            const routes = { d: '/admin/', p: '/admin/posts', s: '/admin/subscribers', t: '/admin/tags' };
            if (routes[e.key]) {
                window.location.href = routes[e.key];
                vimKey = null;
                clearTimeout(vimTimer);
            }
        }
    });

    // --- Keyboard shortcuts for admin ---
    document.addEventListener('keydown', (e) => {
        // Ignore if user is typing in an input/textarea
        const tag = e.target.tagName;
        const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable;
        const mod = e.ctrlKey || e.metaKey;

        // Ctrl/Cmd+S: Save draft
        if (mod && e.key === 's' && !isInput) {
            const saveBtn = document.querySelector('button[name="action"][value="save"]');
            if (saveBtn) {
                e.preventDefault();
                saveBtn.click();
            }
        }

        // Ctrl/Cmd+Enter: Publish
        if (mod && e.key === 'Enter' && !isInput) {
            const publishBtn = document.querySelector('button[name="action"][value="publish"]');
            if (publishBtn) {
                e.preventDefault();
                publishBtn.click();
            }
        }

        // Escape: Close modals
        if (e.key === 'Escape') {
            const modal = document.querySelector('.modal-overlay:not(.hidden)');
            if (modal) {
                modal.classList.add('hidden');
            }
        }

        // Ctrl/Cmd+Shift+P: Toggle preview pane
        if (mod && e.shiftKey && e.key === 'P' && !isInput) {
            const split = document.querySelector('.editor-split');
            if (split) {
                e.preventDefault();
                split.classList.toggle('preview-hidden');
            }
        }

        // ?: Show help
        if (e.key === '?' && !isInput) {
            e.preventDefault();
            const helpModal = document.getElementById('keyboard-help');
            if (helpModal) {
                helpModal.classList.remove('hidden');
            }
        }
    });

    // --- Keyboard shortcuts trigger button ---
    document.getElementById('shortcut-trigger')?.addEventListener('click', () => {
        const helpModal = document.getElementById('keyboard-help');
        if (helpModal) {
            helpModal.classList.remove('hidden');
        }
    });
}