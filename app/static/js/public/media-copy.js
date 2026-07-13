export function initMediaCopy() {
    document.querySelectorAll('.media-copy-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const url = btn.dataset.url;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(() => {
                    btn.textContent = 'Copied!';
                    setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
                }).catch(() => {
                    btn.textContent = 'Failed';
                    setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
                });
            } else {
                btn.textContent = 'Failed';
                setTimeout(() => { btn.textContent = 'Copy URL'; }, 1500);
            }
        });
    });
}

export default initMediaCopy;
