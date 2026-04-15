import { focusableSelectors } from '../shared/utils.js';

export function initLightbox() {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = lightbox?.querySelector('.lightbox-img');
    const lightboxClose = lightbox?.querySelector('.lightbox-close');

    if (lightbox && lightboxImg) {
        let lightboxTrigger = null;

        const openLightbox = (img) => {
            lightboxTrigger = img;
            lightboxImg.src = img.src;
            lightboxImg.alt = img.alt;
            lightbox.classList.add('open');
            lightbox.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
            lightboxClose?.focus();
        };

        const closeLightbox = () => {
            lightbox.classList.remove('open');
            lightbox.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            if (lightboxTrigger) {
                lightboxTrigger.focus();
                lightboxTrigger = null;
            }
        };

        document.querySelectorAll('.prose img').forEach(img => {
            img.style.cursor = 'zoom-in';
            img.addEventListener('click', () => openLightbox(img));
        });

        lightboxClose?.addEventListener('click', closeLightbox);
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) closeLightbox();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && lightbox.classList.contains('open')) {
                closeLightbox();
            }
            if (e.key === 'Tab' && lightbox.classList.contains('open')) {
                const focusable = lightbox.querySelectorAll(focusableSelectors);
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
    }
}