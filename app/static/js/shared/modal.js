import { focusableSelectors } from './utils.js';

export function initModal() {
    // Modal close button handler
    document.querySelectorAll('.modal-overlay .close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal-overlay').classList.add('hidden');
        });
    });

    // Click outside modal content to close
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.add('hidden');
            }
        });
    });

    // --- Modal Focus Trapping ---
    let previousActiveElement = null;

    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('transitionend', () => {
            if (!modal.classList.contains('hidden')) {
                previousActiveElement = document.activeElement;
                const focusable = modal.querySelector(focusableSelectors);
                if (focusable) focusable.focus();
            } else if (previousActiveElement) {
                previousActiveElement.focus();
                previousActiveElement = null;
            }
        });

        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                const focusable = modal.querySelectorAll(focusableSelectors);
                if (focusable.length === 0) return;
                const first = focusable[0];
                const last = focusable[focusable.length - 1];
                if (e.shiftKey) {
                    if (document.activeElement === first) {
                        e.preventDefault();
                        last.focus();
                    }
                } else {
                    if (document.activeElement === last) {
                        e.preventDefault();
                        first.focus();
                    }
                }
            }
        });
    });
}