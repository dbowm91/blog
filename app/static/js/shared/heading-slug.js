export const HEADING_SELECTOR = '.prose h1, .prose h2, .prose h3, .prose h4';

const usedIds = new Set();

export function slugifyHeading(text) {
    return String(text || '')
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-+|-+$/g, '')
        .trim();
}

export function uniqueHeadingSlug(base, taken = usedIds) {
    const seed = base || 'section';
    let slug = seed;
    let counter = 1;
    while (taken.has(slug)) {
        slug = `${seed}-${counter}`;
        counter += 1;
    }
    return slug;
}

export function getHeadingText(heading) {
    const clone = heading.cloneNode(true);
    clone.querySelectorAll('.anchor-link').forEach((el) => el.remove());
    return (clone.textContent || '').trim();
}

export function assignHeadingId(heading, taken = usedIds) {
    if (heading.id) {
        taken.add(heading.id);
        return heading.id;
    }
    const seed = slugifyHeading(getHeadingText(heading)) || heading.tagName.toLowerCase();
    const slug = uniqueHeadingSlug(seed, taken);
    taken.add(slug);
    heading.id = slug;
    return slug;
}

export function getProseHeadings() {
    return Array.from(document.querySelectorAll(HEADING_SELECTOR));
}

export function ensureHeadingIds() {
    const headings = getProseHeadings();
    headings.forEach((heading) => {
        if (heading.id) usedIds.add(heading.id);
    });
    headings.forEach((heading) => assignHeadingId(heading));
    return headings;
}
