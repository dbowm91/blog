import { ensureHeadingIds, getProseHeadings } from '../shared/heading-slug.js';

export function initAnchorLinks() {
    ensureHeadingIds();

    getProseHeadings().forEach((heading) => {
        const wrapper = document.createElement('span');
        wrapper.className = 'heading-anchor';

        const anchor = document.createElement('a');
        anchor.className = 'anchor-link';
        anchor.href = `#${heading.id}`;
        anchor.innerHTML = '#';
        anchor.setAttribute('aria-label', 'Link to this section');
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const fullUrl = anchor.href;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(fullUrl).then(() => {
                    const toast = document.createElement('div');
                    toast.className = 'toast';
                    toast.textContent = 'Link copied!';
                    document.body.appendChild(toast);
                    requestAnimationFrame(() => toast.classList.add('visible'));
                    setTimeout(() => {
                        toast.classList.remove('visible');
                        setTimeout(() => toast.remove(), 300);
                    }, 2000);
                });
            }
        });

        while (heading.firstChild) {
            wrapper.appendChild(heading.firstChild);
        }

        heading.appendChild(wrapper);
        heading.appendChild(anchor);
    });
}

export default initAnchorLinks;
