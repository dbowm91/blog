const TAG_PATTERN = /<(\/)?([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^<>])*?)(\/)?>/g;

function rebalance(line, carry) {
    const endOpen = carry.slice();
    const stack = carry.map((tag) => tag.name);

    TAG_PATTERN.lastIndex = 0;
    let match;
    while ((match = TAG_PATTERN.exec(line)) !== null) {
        const closing = match[1] === '/';
        const name = match[2];
        const attrs = match[3] || '';
        if (match[4] === '/') continue;
        if (closing) {
            const index = stack.lastIndexOf(name);
            if (index === -1) continue;
            stack.splice(index);
            endOpen.splice(index);
        } else {
            stack.push(name);
            endOpen.push({ name, attrs });
        }
    }

    const prefix = carry.map((tag) => `<${tag.name}${tag.attrs}>`).join('');
    const suffix = endOpen.slice().reverse().map((tag) => `</${tag.name}>`).join('');

    return { html: `${prefix}${line}${suffix}`, carry: endOpen };
}

export function splitHighlightedLines(html, expected) {
    // Split the highlighted markup into one fragment per rendered line.
    //
    // A token may span lines, so a fragment is rebalanced: the tags that are
    // open when the line ends are closed, and the ones that were open when it
    // began are reopened. A token that spans lines therefore keeps its colour
    // on every line it covers.
    const parts = html.split('\n');
    if (parts.length === expected + 1 && parts[parts.length - 1] === '') {
        parts.pop();
    }
    if (parts.length !== expected) {
        return null;
    }

    const fragments = [];
    let carry = [];
    for (const part of parts) {
        const balanced = rebalance(part, carry);
        fragments.push(balanced.html);
        carry = balanced.carry;
    }
    return fragments;
}

export function highlightCodeBlocks(Prism) {
    const blocks = document.querySelectorAll('code[class*="language-"]');
    blocks.forEach((code) => {
        const language = Prism.util.getLanguage(code);
        if (!language || language === 'none') return;
        const grammar = Prism.languages[language];
        if (!grammar) return;
        const text = code.textContent;
        if (!text) return;

        const highlighted = Prism.highlight(text, grammar, language);

        const lines = [...code.children].filter((child) => child.tagName === 'SPAN');
        if (lines.length === 0) {
            code.innerHTML = highlighted;
            return;
        }

        const fragments = splitHighlightedLines(highlighted, lines.length);
        if (!fragments) {
            code.innerHTML = highlighted;
            return;
        }
        lines.forEach((line, index) => {
            line.innerHTML = fragments[index];
        });
    });
}

export default highlightCodeBlocks;
