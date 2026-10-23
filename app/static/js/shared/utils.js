export const focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

export function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

export function getCsrfHeaderName() {
    return document.documentElement?.dataset?.csrfHeader || 'X-CSRF-Token';
}

export function csrfHeaders() {
    const token = getCsrfToken();
    if (!token) return {};
    return { [getCsrfHeaderName()]: token };
}

export function initFormLoading() {
    document.querySelectorAll('form[data-loading]').forEach(form => {
        if (form.dataset.loadingBound === 'true') return;
        form.dataset.loadingBound = 'true';
        form.addEventListener('submit', () => {
            const submit = form.querySelector('button[type="submit"], input[type="submit"]');
            if (!submit || submit.disabled) return;
            const pendingText = form.dataset.loadingText;
            if (pendingText) submit.textContent = pendingText;
            form.setAttribute('aria-busy', 'true');
            setTimeout(() => { submit.disabled = true; }, 0);
        });
    });
}

const SCROLL_RESTORE_KEY = 'devlog-scroll-position';
const SCROLL_PRESERVE_SELECTOR = 'a.filter-link, a.page-link';

export function initScrollPreservation() {
    document.addEventListener('click', (e) => {
        const link = e.target.closest(SCROLL_PRESERVE_SELECTOR);
        if (!link) return;
        try {
            sessionStorage.setItem(SCROLL_RESTORE_KEY, String(Math.round(window.scrollY)));
        } catch {
            // storage unavailable — scroll position is simply not preserved
        }
    });

    let saved = null;
    try {
        saved = sessionStorage.getItem(SCROLL_RESTORE_KEY);
    } catch {
        return;
    }
    if (saved === null) return;
    try {
        sessionStorage.removeItem(SCROLL_RESTORE_KEY);
    } catch {
        // storage unavailable — nothing to restore
    }
    const y = Number(saved);
    if (!Number.isFinite(y) || y <= 0) return;

    const apply = () => window.scrollTo(0, y);
    if (document.readyState === 'complete') {
        requestAnimationFrame(apply);
    } else {
        window.addEventListener('load', () => requestAnimationFrame(apply), { once: true });
    }
}

export function announce(message) {
    const el = document.getElementById('sr-announce');
    if (el) {
        el.textContent = '';
        setTimeout(() => { el.textContent = message; }, 50);
    }
}

export function initSharedUtils() {
    // --- Pending-state submit buttons ---
    initFormLoading();

    // --- Keep the viewport in place across filter/pagination navigation ---
    initScrollPreservation();

    // --- History back button (CSP-safe replacement for inline onclick) ---
    document.querySelectorAll('[data-history-back]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (window.history.length > 1) {
                window.history.back();
            } else {
                window.location.href = '/';
            }
        });
    });

    // --- Password visibility toggle ---
    document.querySelectorAll('.pw-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const input = targetId ? document.getElementById(targetId) : btn.previousElementSibling;
            if (input && input.type === 'password') {
                input.type = 'text';
                btn.textContent = 'Hide';
                btn.setAttribute('aria-label', 'Hide password');
            } else if (input) {
                input.type = 'password';
                btn.textContent = 'Show';
                btn.setAttribute('aria-label', 'Show password');
            }
        });
    });

    // --- Search result announcement ---
    const searchResultCount = document.querySelector('[data-search-announce]');
    if (searchResultCount) {
        announce(searchResultCount.textContent.trim());
    }

    // --- Form confirmation via data-confirm attribute ---
    const confirmModal = document.getElementById('confirm-modal');
    const confirmModalTitle = document.getElementById('confirm-modal-title');
    const confirmModalMessage = document.getElementById('confirm-modal-message');
    const confirmModalConfirm = document.getElementById('confirm-modal-confirm');
    let pendingConfirmForm = null;

    if (confirmModal && confirmModalConfirm) {
        confirmModalConfirm.addEventListener('click', () => {
            if (pendingConfirmForm) {
                pendingConfirmForm.submit();
            }
            confirmModal.classList.add('hidden');
            pendingConfirmForm = null;
        });

        document.querySelectorAll('form[data-confirm]').forEach(form => {
            form.addEventListener('submit', e => {
                e.preventDefault();
                pendingConfirmForm = form;
                const isDanger = form.dataset.confirmType === 'danger';
                confirmModalMessage.textContent = form.dataset.confirm;
                confirmModalConfirm.className = isDanger ? 'btn btn-small btn-danger' : 'btn btn-small btn-primary';
                confirmModalTitle.textContent = isDanger ? 'Confirm Destructive Action' : 'Confirm';
                if (isDanger) {
                    confirmModal.classList.add('danger');
                } else {
                    confirmModal.classList.remove('danger');
                }
                confirmModal.classList.remove('hidden');
            });
        });
    }

    // --- Bulk action confirmation via data-confirm-bulk ---
    document.querySelectorAll('button[data-confirm-bulk]').forEach(btn => {
        let originalText = btn.textContent;
        let resetTimer = null;
        const resetButton = () => {
            btn.textContent = originalText;
            btn.dataset.primed = 'false';
            btn.classList.remove('btn-danger-primed');
            btn.removeEventListener('blur', resetButton);
            if (resetTimer) {
                clearTimeout(resetTimer);
                resetTimer = null;
            }
        };
        btn.addEventListener('click', e => {
            const checked = document.querySelectorAll('.bulk-checkbox:checked');
            if (checked.length === 0) {
                e.preventDefault();
                return;
            }
            const count = checked.length;
            const isDelete = btn.value === 'delete';
            if (isDelete) {
                if (btn.dataset.primed !== 'true') {
                    e.preventDefault();
                    originalText = btn.textContent;
                    btn.textContent = `Delete ${count} post${count > 1 ? 's' : ''}? Click again to confirm`;
                    btn.dataset.primed = 'true';
                    btn.classList.add('btn-danger-primed');
                    resetTimer = setTimeout(resetButton, 5000);
                    btn.addEventListener('blur', resetButton);
                    return;
                }
                resetButton();
            }
            if (!confirm(btn.dataset.confirmBulk)) e.preventDefault();
        });
    });

    // --- Element references ---
    const navbar = document.querySelector(".navbar");

    // --- Back to top button ---
    const backToTop = document.createElement("button");
    backToTop.className = "back-to-top";
    backToTop.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M7.41 15.41L12 10.83l4.59 4.58L18 14l-6-6-6 6z"/></svg>';
    backToTop.setAttribute("aria-label", "Back to top");
    document.body.appendChild(backToTop);

    // --- Combined scroll handler with throttling ---
    let scrollTimeout;
    const combinedScrollHandler = () => {
        if (scrollTimeout) return;

        scrollTimeout = setTimeout(() => {
            scrollTimeout = null;

            if (navbar) {
                navbar.classList.toggle('navbar-shrunk', window.scrollY > 60);
            }

            if (window.scrollY > 300) {
                backToTop.classList.add("visible");
            } else {
                backToTop.classList.remove("visible");
            }

            const readingProgress = document.querySelector('.reading-progress');
            if (readingProgress) {
                const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
                const progress = scrollHeight > 0 ? (window.scrollY / scrollHeight) * 100 : 0;
                readingProgress.style.width = `${Math.min(progress, 100)}%`;
            }
        }, 100);
    };

    window.addEventListener("scroll", combinedScrollHandler, { passive: true });

    backToTop.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    // --- Smooth flash dismissal ---
    document.querySelectorAll(".flash").forEach((flash) => {
        let dismissTimer;
        const dismiss = () => {
            flash.style.transition = "opacity 0.3s ease, transform 0.3s ease";
            flash.style.opacity = "0";
            flash.style.transform = "translateY(-8px)";
            setTimeout(() => flash.remove(), 300);
        };
        const startTimer = () => {
            clearTimeout(dismissTimer);
            dismissTimer = setTimeout(dismiss, 8000);
        };
        const closeBtn = flash.querySelector(".flash-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                dismiss();
            });
        }
        flash.addEventListener("mouseenter", () => clearTimeout(dismissTimer));
        flash.addEventListener("mouseleave", startTimer);
        flash.addEventListener("focusin", () => clearTimeout(dismissTimer));
        flash.addEventListener("focusout", startTimer);
        startTimer();
    });
}

export default initSharedUtils;