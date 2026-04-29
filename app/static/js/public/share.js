import { getCsrfToken } from '../shared/utils.js';

export function initShare() {
    const shareBar = document.querySelector(".share-bar");
    if (shareBar) {
        const postId = shareBar.dataset.postId;

        // Keyboard shortcut: 'c' to copy link (only on post pages, not in inputs)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'c' || e.key === 'C') {
                const target = e.target;
                const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;
                if (!isInput) {
                    const copyBtn = shareBar.querySelector('.share-btn[data-platform="copy"]');
                    if (copyBtn) {
                        e.preventDefault();
                        copyBtn.click();
                    }
                }
            }
        });

        shareBar.querySelectorAll(".share-btn[data-platform]").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                const platform = btn.dataset.platform;

                if (platform === "copy") {
                    e.preventDefault();
                    const shareUrl = shareBar.dataset.shareUrl;
                    const copyToClipboard = (text) => {
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            return navigator.clipboard.writeText(text);
                        }
                        throw new Error('Clipboard API not available');
                    };

                    copyToClipboard(shareUrl).then(() => {
                        const original = btn.innerHTML;
                        btn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>';
                        const announcer = document.getElementById('sr-announce');
                        if (announcer) announcer.textContent = 'Link copied!';
                        setTimeout(() => { btn.innerHTML = original; }, 1500);
                    }).catch(() => {
                        btn.textContent = 'Failed';
                        setTimeout(() => { btn.innerHTML = original; }, 1500);
                    });
                    return;
                }

                const trackShare = () => {
                    const csrfToken = getCsrfToken();
                    const formData = new FormData();
                    formData.append('post_id', postId);
                    formData.append('platform', platform);
                    formData.append('csrf_token', csrfToken);

                    if (navigator.sendBeacon) {
                        navigator.sendBeacon('/api/track-share', formData);
                    } else {
                        const data = JSON.stringify({ post_id: parseInt(postId), platform: platform });
                        fetch("/api/track-share", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                "X-CSRF-Token": csrfToken,
                            },
                            body: data,
                            keepalive: true,
                        }).catch(err => {
                            console.warn('Share tracking failed:', err);
                        });
                    }
                };
                trackShare();
            });
        });
    }

    // --- Share button color flash ---
    document.querySelectorAll('.share-btn[data-platform]:not([data-platform="copy"])').forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.add('share-flash');
            this.addEventListener('animationend', () => {
                this.classList.remove('share-flash');
            }, { once: true });
        });
    });
}

export default initShare;