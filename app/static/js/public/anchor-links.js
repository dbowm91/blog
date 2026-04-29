export function initAnchorLinks() {
    const usedIds = new Set();
    document.querySelectorAll('.prose h1, .prose h2, .prose h3, .prose h4').forEach((heading) => {
        if (!heading.id) {
            const text = heading.textContent;
            let id = text.toLowerCase()
                .replace(/[^\w\s-]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-')
                .trim();

            if (!id) {
                const headingType = heading.tagName.toLowerCase();
                let counter = 1;
                id = `${headingType}-${counter}`;
                while (usedIds.has(id)) {
                    counter++;
                    id = `${headingType}-${counter}`;
                }
            } else {
                let finalId = id;
                let counter = 1;
                while (usedIds.has(finalId)) {
                    finalId = `${id}-${counter}`;
                    counter++;
                }
                id = finalId;
            }
            usedIds.add(id);
            heading.id = id;
        } else {
            usedIds.add(heading.id);
        }

        const wrapper = document.createElement('span');
        wrapper.className = 'heading-anchor';

        const anchor = document.createElement('a');
        anchor.className = 'anchor-link';
        anchor.href = `#${heading.id}`;
        anchor.innerHTML = '#';
        anchor.setAttribute('aria-label', 'Link to this section');
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const fullUrl = window.location.origin + window.location.pathname + anchor.href;
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
