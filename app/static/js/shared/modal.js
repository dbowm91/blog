import { focusableSelectors } from './utils.js';

export function initModal() {
    const previousFocus = new WeakMap();

    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.setAttribute('tabindex', '-1');

        const focusModal = () => {
            const firstFocusable = modal.querySelector(focusableSelectors);
            (firstFocusable || modal).focus();
        };

        const closeModal = () => {
            modal.classList.add('hidden');
        };

        new MutationObserver(() => {
            if (!modal.classList.contains('hidden')) {
                if (!previousFocus.has(modal)) {
                    previousFocus.set(modal, document.activeElement);
                }
                focusModal();
            } else {
                const trigger = previousFocus.get(modal);
                previousFocus.delete(modal);
                trigger?.focus?.();
            }
        }).observe(modal, { attributes: true, attributeFilter: ['class'] });

        modal.querySelectorAll('.modal-close-btn, .close-btn').forEach(btn => {
            btn.addEventListener('click', closeModal);
        });

        modal.addEventListener('click', (event) => {
            if (event.target === modal) closeModal();
        });

        modal.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                event.stopPropagation();
                closeModal();
                return;
            }

            if (event.key !== 'Tab') return;
            const focusable = modal.querySelectorAll(focusableSelectors);
            if (focusable.length === 0) return;

            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        });
    });
}

export default initModal;
