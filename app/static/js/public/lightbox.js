import { focusableSelectors } from '../shared/utils.js';

export function initLightbox() {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = lightbox?.querySelector('.lightbox-img');
    const lightboxClose = lightbox?.querySelector('.lightbox-close');
    const lightboxPrev = lightbox?.querySelector('.lightbox-prev');
    const lightboxNext = lightbox?.querySelector('.lightbox-next');
    const lightboxCaption = lightbox?.querySelector('.lightbox-caption');

    if (lightbox && lightboxImg) {
        let lightboxTrigger = null;
        let images = [];
        let currentIndex = 0;
        let isZoomed = false;
        let touchStartX = 0;
        let touchEndX = 0;

        const updateNav = () => {
            if (lightboxPrev) {
                lightboxPrev.disabled = images.length <= 1 || currentIndex === 0;
            }
            if (lightboxNext) {
                lightboxNext.disabled = images.length <= 1 || currentIndex === images.length - 1;
            }
        };

        const showImage = (index) => {
            if (index < 0 || index >= images.length) return;
            currentIndex = index;
            const img = images[index];
            lightboxImg.src = img.src;
            lightboxImg.alt = img.alt;
            isZoomed = false;
            lightboxImg.classList.remove('zoomed');
            updateNav();

            if (lightboxCaption) {
                if (img.alt) {
                    lightboxCaption.textContent = img.alt;
                    lightboxCaption.classList.add('visible');
                } else {
                    lightboxCaption.textContent = '';
                    lightboxCaption.classList.remove('visible');
                }
            }
        };

        const openLightbox = (img, index) => {
            lightboxTrigger = img;
            isZoomed = false;
            lightboxImg.classList.remove('zoomed');
            lightbox.classList.add('open');
            lightbox.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
            showImage(index);
            lightboxClose?.focus();
        };

        const closeLightbox = () => {
            lightbox.classList.remove('open');
            lightbox.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            isZoomed = false;
            lightboxImg.classList.remove('zoomed');
            if (lightboxTrigger) {
                lightboxTrigger.focus();
                lightboxTrigger = null;
            }
        };

        const prevImage = () => {
            if (currentIndex > 0) {
                showImage(currentIndex - 1);
            }
        };

        const nextImage = () => {
            if (currentIndex < images.length - 1) {
                showImage(currentIndex + 1);
            }
        };

        const toggleZoom = () => {
            if (isZoomed) {
                isZoomed = false;
                lightboxImg.classList.remove('zoomed');
            } else {
                isZoomed = true;
                lightboxImg.classList.add('zoomed');
            }
        };

        images = Array.from(document.querySelectorAll('.prose img'));
        images.forEach((img, index) => {
            img.style.cursor = 'zoom-in';
            img.addEventListener('click', (e) => {
                e.preventDefault();
                openLightbox(img, index);
            });
        });

        lightboxClose?.addEventListener('click', closeLightbox);
        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) closeLightbox();
        });

        lightboxPrev?.addEventListener('click', (e) => {
            e.stopPropagation();
            prevImage();
        });

        lightboxNext?.addEventListener('click', (e) => {
            e.stopPropagation();
            nextImage();
        });

        lightboxImg?.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            toggleZoom();
        });

        lightboxImg?.addEventListener('click', (e) => {
            if (!isZoomed) {
                e.stopPropagation();
                closeLightbox();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (!lightbox.classList.contains('open')) return;

            switch (e.key) {
                case 'Escape':
                    closeLightbox();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    prevImage();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    nextImage();
                    break;
                case 'Tab':
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
                    break;
            }
        });

        lightbox.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });

        lightbox.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            const diff = touchStartX - touchEndX;
            if (Math.abs(diff) > 50) {
                if (diff > 0) {
                    nextImage();
                } else {
                    prevImage();
                }
            }
        }, { passive: true });
    }
}
