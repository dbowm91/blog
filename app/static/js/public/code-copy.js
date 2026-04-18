export function initCodeCopy() {
    document.querySelectorAll('pre[class*="language-"]').forEach((pre) => {
        const code = pre.querySelector('code');
        if (code) {
            const langMatch = pre.className.match(/language-(\S+)/);
            if (langMatch) {
                code.lang = langMatch[1];
            }
        }
        const button = document.createElement('button');
        button.className = 'copy-code-btn';
        button.textContent = 'Copy';
        button.addEventListener('click', () => {
            if (code) {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(code.textContent).then(() => {
                        button.textContent = 'Copied!';
                        setTimeout(() => { button.textContent = 'Copy'; }, 2000);
                    }).catch(() => {
                        button.textContent = 'Failed';
                        setTimeout(() => { button.textContent = 'Copy'; }, 2000);
                    });
                } else {
                    button.textContent = 'Failed';
                    setTimeout(() => { button.textContent = 'Copy'; }, 2000);
                }
            }
        });
        pre.appendChild(button);
    });
}