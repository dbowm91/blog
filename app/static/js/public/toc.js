export function initToc() {
    const tocContainer = document.querySelector('.post-toc-container');
    if (tocContainer) {
        const headings = document.querySelectorAll('.prose h2, .prose h3');
        if (headings.length >= 3) {
            const toc = document.createElement('nav');
            toc.className = 'post-toc';
            toc.setAttribute('aria-label', 'Table of contents');

            const title = document.createElement('div');
            title.className = 'post-toc-title';
            title.textContent = 'On This Page';
            toc.appendChild(title);

            const ul = document.createElement('ul');
            headings.forEach((heading, index) => {
                if (!heading.id) {
                    heading.id = `heading-${index}`;
                }
                const li = document.createElement('li');
                li.className = heading.tagName === 'H3' ? 'toc-h3' : '';
                const a = document.createElement('a');
                a.href = `#${heading.id}`;
                a.textContent = heading.textContent;
                a.dataset.section = heading.id;
                li.appendChild(a);
                ul.appendChild(li);
            });
            toc.appendChild(ul);
            tocContainer.appendChild(toc);
            tocContainer.style.display = 'block';

            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    const id = entry.target.id;
                    const link = toc.querySelector(`a[data-section="${id}"]`);
                    if (link) {
                        link.classList.toggle('active', entry.isIntersecting);
                    }
                });
            }, {
                rootMargin: '-80px 0px -70% 0px',
                threshold: 0
            });

            headings.forEach(h => observer.observe(h));
        }
    }
}