let toastContainer = null;
let toastStack = [];
const TOAST_DURATION = 5000;
const MAX_TOASTS = 5;

function createToastContainer() {
    if (toastContainer) return toastContainer;
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.setAttribute('aria-live', 'polite');
    toastContainer.setAttribute('aria-atomic', 'false');
    document.body.appendChild(toastContainer);
    return toastContainer;
}

function removeToast(toast) {
    toast.classList.remove('toast-enter');
    toast.classList.add('toast-exit');
    toast.addEventListener('animationend', () => {
        toast.remove();
        toastStack = toastStack.filter(t => t !== toast);
    }, { once: true });
}

function dismissToast(toast) {
    if (toast.dataset.dismissed) return;
    toast.dataset.dismissed = 'true';
    clearTimeout(parseInt(toast.dataset.timeout, 10));
    removeToast(toast);
}

function showToast(message, type = 'info') {
    const container = createToastContainer();
    const toast = document.createElement('div');
    const toastType = ['success', 'error', 'warning', 'info'].includes(type) ? type : 'info';
    toast.className = `toast toast-${toastType}`;
    toast.setAttribute('role', 'alert');

    const icons = {
        success: '<svg class="toast-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"/></svg>',
        error: '<svg class="toast-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z"/></svg>',
        warning: '<svg class="toast-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1Zm.75 4.25a.75.75 0 0 0-1.5 0v4a.75.75 0 0 0 1.5 0v-4Zm-.75 8.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"/></svg>',
        info: '<svg class="toast-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 0 1.5h-1a.75.75 0 0 1-.75-.75ZM6.5 12a.75.75 0 0 0 0 1.5 6.5 6.5 0 1 0 0-13 .75.75 0 0 0 0 1.5Z"/></svg>',
    };

    toast.innerHTML = `
        ${icons[toastType]}
        <span class="toast-message"></span>
        <button type="button" class="toast-close" aria-label="Dismiss">&times;</button>
    `;
    toast.querySelector('.toast-message').textContent = message;
    toast.querySelector('.toast-close').addEventListener('click', () => dismissToast(toast));

    let cumulativeOffset = 0;
    toastStack.forEach(t => {
        t.style.transform = `translateY(-${cumulativeOffset}px)`;
        cumulativeOffset += t.offsetHeight + 12;
    });

    if (toastStack.length >= MAX_TOASTS) {
        const oldest = toastStack.shift();
        dismissToast(oldest);
    }

    toastStack.push(toast);
    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add('toast-enter');
    });

    const timeout = setTimeout(() => {
        dismissToast(toast);
    }, TOAST_DURATION);
    toast.dataset.timeout = timeout;

    return toast;
}

function convertFlashesToToasts() {
    const flashContainer = document.querySelector('.flash-container');
    if (!flashContainer) return;

    const flashes = flashContainer.querySelectorAll('.flash');
    flashes.forEach(flash => {
        const message = flash.querySelector('.flash-message')?.textContent;
        const category = Array.from(flash.classList)
            .find(c => c.startsWith('flash-') && c !== 'flash-')
            ?.replace('flash-', '') || 'info';
        if (message) {
            showToast(message.trim(), category);
        }
    });

    flashContainer.remove();
}

export function initToast() {
    convertFlashesToToasts();
}

export { showToast, initToast as default };
