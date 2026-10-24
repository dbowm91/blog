const ACTIONS = {
    bold: { type: 'wrap', before: '**', after: '**', placeholder: 'bold text' },
    italic: { type: 'wrap', before: '*', after: '*', placeholder: 'italic text' },
    underline: { type: 'wrap', before: '<u>', after: '</u>', placeholder: 'underlined text' },
    strikethrough: { type: 'wrap', before: '~~', after: '~~', placeholder: 'struck text' },
    code: { type: 'wrap', before: '`', after: '`', placeholder: 'code' },
    link: { type: 'link', placeholder: 'link text' },
    codeblock: { type: 'block', placeholder: 'code' },
    heading: { type: 'line', prefix: '## ', placeholder: 'Heading', strip: /^(\s*)#{1,6}\s+/ },
    quote: { type: 'line', prefix: '> ', placeholder: 'Quote', strip: /^(\s*)>\s?/ },
    bulletlist: { type: 'line', prefix: '- ', placeholder: 'List item', strip: /^(\s*)[-*+]\s+/ },
    numberedlist: { type: 'line', prefix: null, placeholder: 'List item', strip: /^(\s*)\d+\.\s+/ },
};

function replaceSpan(textarea, from, to, text, selectStart, selectEnd) {
    const value = textarea.value;

    textarea.dispatchEvent(new CustomEvent('editor:structural', { bubbles: true }));
    textarea.value = value.slice(0, from) + text + value.slice(to);
    textarea.focus();
    textarea.setSelectionRange(selectStart, selectEnd);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
}

function replaceRange(textarea, text, selectStart, selectEnd) {
    replaceSpan(
        textarea,
        textarea.selectionStart,
        textarea.selectionEnd,
        text,
        selectStart,
        selectEnd
    );
}

function applyWrap(textarea, action) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    const selected = value.slice(start, end) || action.placeholder;
    const text = action.before + selected + action.after;

    replaceRange(textarea, text, start + action.before.length, start + action.before.length + selected.length);
}

function applyLink(textarea, action) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    const selected = value.slice(start, end) || action.placeholder;
    const text = '[' + selected + '](url)';
    const urlStart = start + selected.length + 3;

    replaceRange(textarea, text, urlStart, urlStart + 3);
}

function applyBlock(textarea, action) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    const selected = value.slice(start, end) || action.placeholder;
    const before = value.slice(0, start);
    const after = value.slice(end);

    const leading = before && !before.endsWith('\n') ? '\n' : '';
    const trailing = after && !after.startsWith('\n') ? '\n' : '';
    const text = leading + '```\n' + selected + '\n```' + trailing;
    const contentStart = start + leading.length + 4;

    replaceRange(textarea, text, contentStart, contentStart + selected.length);
}

function applyLinePrefix(textarea, action) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;

    const lineStart = value.lastIndexOf('\n', start - 1) + 1;
    let lineEnd = value.indexOf('\n', end);
    if (lineEnd === -1) lineEnd = value.length;

    const block = value.slice(lineStart, lineEnd);
    const lines = block.split('\n');
    const prefixFor = (index) => (action.prefix ? action.prefix : `${index + 1}. `);

    let newBlock;
    let selectStart;
    let selectEnd;

    if (lines.length === 1 && lines[0].trim() === '') {
        newBlock = prefixFor(0) + action.placeholder;
        selectStart = lineStart + prefixFor(0).length;
        selectEnd = selectStart + action.placeholder.length;
    } else {
        newBlock = lines
            .map((line, index) => {
                const match = action.strip.exec(line);
                const indent = match ? match[1] : '';
                const rest = match ? line.slice(match[0].length) : line;
                return indent + prefixFor(index) + rest;
            })
            .join('\n');
        selectStart = lineStart + newBlock.length;
        selectEnd = selectStart;
    }

    replaceSpan(textarea, lineStart, lineEnd, newBlock, selectStart, selectEnd);
}

function applyAction(textarea, action) {
    if (!action) return;

    switch (action.type) {
        case 'wrap':
            applyWrap(textarea, action);
            break;
        case 'link':
            applyLink(textarea, action);
            break;
        case 'block':
            applyBlock(textarea, action);
            break;
        case 'line':
            applyLinePrefix(textarea, action);
            break;
    }
}

export function initMarkdownToolbar() {
    const toolbar = document.querySelector('.editor-toolbar');
    const textarea = document.getElementById('body');

    if (!toolbar || !textarea) return;

    toolbar.addEventListener('mousedown', (event) => {
        if (event.target.closest('.md-tool')) {
            event.preventDefault();
        }
    });

    toolbar.addEventListener('click', (event) => {
        const button = event.target.closest('.md-tool');
        if (!button) return;

        event.preventDefault();
        applyAction(textarea, ACTIONS[button.dataset.mdAction]);
    });
}

export default initMarkdownToolbar;
